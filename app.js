const API_BASE = window.NUTRIMENTE_API_URL
  || (window.location.protocol.startsWith("http") ? `${window.location.origin}/api` : "http://127.0.0.1:8000/api");
const SESSION_KEY = "nutrimente_session_token";

const state = {
  user: null,
  professionals: [],
  services: {},
  modes: {},
  selectedSlot: "",
  appointments: [],
};

const elements = {
  menuToggle: document.getElementById("menuToggle"),
  menuNav: document.getElementById("menuNav"),
  authModal: document.getElementById("authModal"),
  openAuthModal: document.getElementById("openAuthModal"),
  closeAuthModal: document.getElementById("closeAuthModal"),
  tabLogin: document.getElementById("tabLogin"),
  tabRegister: document.getElementById("tabRegister"),
  loginForm: document.getElementById("loginForm"),
  registerForm: document.getElementById("registerForm"),
  registerRole: document.getElementById("registerRole"),
  roleButtons: Array.from(document.querySelectorAll(".segment-btn")),
  professionalFields: document.getElementById("professionalFields"),
  dashboardSection: document.getElementById("dashboardSection"),
  dashboardShortcut: document.getElementById("dashboardShortcut"),
  appointmentsList: document.getElementById("appointmentsList"),
  professionalsGrid: document.getElementById("professionalsGrid"),
  professionalId: document.getElementById("professionalId"),
  serviceSelect: document.getElementById("serviceSelect"),
  modeSelect: document.getElementById("modeSelect"),
  appointmentDate: document.getElementById("appointmentDate"),
  slotsGrid: document.getElementById("slotsGrid"),
  bookingForm: document.getElementById("bookingForm"),
  bookingSummary: document.getElementById("bookingSummary"),
  patientName: document.getElementById("patientName"),
  patientEmail: document.getElementById("patientEmail"),
  patientPhone: document.getElementById("patientPhone"),
  appointmentNotes: document.getElementById("appointmentNotes"),
  videoModal: document.getElementById("videoModal"),
  closeVideoModal: document.getElementById("closeVideoModal"),
  videoShell: document.getElementById("videoShell"),
  toastStack: document.getElementById("toastStack"),
};

function getSessionToken() {
  return sessionStorage.getItem(SESSION_KEY);
}

function setSessionToken(token) {
  if (token) {
    sessionStorage.setItem(SESSION_KEY, token);
    return;
  }
  sessionStorage.removeItem(SESSION_KEY);
}

async function apiRequest(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getSessionToken();

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch (error) {
    throw new Error("Não foi possível comunicar com o servidor.");
  }

  let payload = {};
  try {
    payload = await response.json();
  } catch (error) {
    payload = {};
  }

  if (!response.ok) {
    throw new Error(payload.error || payload.message || "Falha inesperada.");
  }

  return payload;
}

function showToast(type, message) {
  const item = document.createElement("div");
  item.className = `toast ${type}`;
  item.textContent = message;
  elements.toastStack.appendChild(item);
  window.setTimeout(() => item.remove(), 4200);
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function isValidName(name) {
  return name.trim().length >= 3;
}

function isValidPhone(phone) {
  return phone.replace(/\D/g, "").length >= 10;
}

function isStrongPassword(password) {
  return password.length >= 8;
}

function isValidProfessionalDocument(council, documentId) {
  const value = documentId.trim().toUpperCase();
  const patterns = {
    CFP: /^\d{2}\/\d{4,6}$/,
    CFN: /^\d{4,6}(?:\/[A-Z]{2})?$/,
  };
  return Boolean(patterns[council] && patterns[council].test(value));
}

function setAuthTab(tab) {
  const isLogin = tab === "login";
  elements.tabLogin.classList.toggle("active", isLogin);
  elements.tabRegister.classList.toggle("active", !isLogin);
  elements.loginForm.classList.toggle("hidden", !isLogin);
  elements.registerForm.classList.toggle("hidden", isLogin);
  document.getElementById("authTitle").textContent = isLogin ? "Entrar" : "Criar conta";
}

function openModal(modal) {
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
}

function closeModal(modal) {
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
}

function updateHeader() {
  if (state.user) {
    elements.openAuthModal.textContent = `${state.user.nome.split(" ")[0]} | Sair`;
    elements.dashboardShortcut.classList.remove("hidden");
    elements.dashboardSection.classList.remove("hidden");
  } else {
    elements.openAuthModal.textContent = "Entrar";
    elements.dashboardShortcut.classList.add("hidden");
    elements.dashboardSection.classList.add("hidden");
  }
}

function renderProfessionals() {
  if (!state.professionals.length) {
    elements.professionalsGrid.innerHTML = '<article class="empty-card">Nenhum profissional disponível.</article>';
    return;
  }

  const pageMap = {
    "mariana-souza": "mariana.html",
    "lucas-fernandes": "lucas.html",
    "fernanda-lima": "fernandaa.html",
  };

  elements.professionalsGrid.innerHTML = state.professionals
    .map(
      (item) => `
        <article class="professional-card">
          <div class="card-top">
            <div>
              <p class="eyebrow">${item.conselho}</p>
              <h3>${item.nome}</h3>
            </div>
            <span class="chip">${item.registroProfissional}</span>
          </div>
          <p>${item.bio}</p>
          <div class="professional-meta">
            <span class="chip">${item.titulo}</span>
            <span class="chip">${item.especialidades[0]}</span>
          </div>
          <a class="card-link" href="${pageMap[item.slug] || "#agenda"}">Ver perfil completo</a>
        </article>
      `,
    )
    .join("");
}

function renderSelectOptions() {
  elements.professionalId.innerHTML = state.professionals
    .map((item) => `<option value="${item.id}">${item.nome} | ${item.titulo}</option>`)
    .join("");

  elements.serviceSelect.innerHTML = Object.entries(state.services)
    .map(([value, label]) => `<option value="${value}">${label}</option>`)
    .join("");
}

function updateSummary() {
  const professional = state.professionals.find(
    (item) => String(item.id) === elements.professionalId.value,
  );
  const date = elements.appointmentDate.value;
  const slot = state.selectedSlot;
  const service = state.services[elements.serviceSelect.value];
  const mode = state.modes[elements.modeSelect.value] || elements.modeSelect.value;

  if (!professional || !date || !slot) {
    elements.bookingSummary.innerHTML = `
      <p class="summary-label">Resumo da escolha</p>
      <h3>Nenhum horário selecionado</h3>
      <p>Escolha um profissional, uma data e um horário para visualizar o resumo.</p>
      <ul class="summary-list">
        <li>Login necessário para concluir o agendamento.</li>
        <li>Horários bloqueados automaticamente quando já reservados.</li>
        <li>Consultas online abrem em sala privada da plataforma.</li>
      </ul>
    `;
    return;
  }

  elements.bookingSummary.innerHTML = `
    <p class="summary-label">Resumo da escolha</p>
    <h3>${professional.nome}</h3>
    <p>${professional.titulo}</p>
    <ul class="summary-list">
      <li>Serviço: ${service}</li>
      <li>Modalidade: ${mode}</li>
      <li>Data: ${new Date(`${date}T00:00:00`).toLocaleDateString("pt-BR")}</li>
      <li>Horário: ${slot}</li>
    </ul>
  `;
}

function renderSlots(slots) {
  elements.slotsGrid.innerHTML = slots
    .map(
      (item) => `
        <button
          class="slot-btn ${item.hora === state.selectedSlot ? "selected" : ""}"
          data-slot="${item.hora}"
          type="button"
          ${item.disponivel ? "" : "disabled"}
        >
          ${item.hora}
        </button>
      `,
    )
    .join("");

  elements.slotsGrid.querySelectorAll("[data-slot]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedSlot = button.dataset.slot;
      renderSlots(slots);
      updateSummary();
    });
  });
}

async function refreshAvailability() {
  const professionalId = elements.professionalId.value;
  const date = elements.appointmentDate.value;

  if (!professionalId || !date) {
    state.selectedSlot = "";
    renderSlots([]);
    updateSummary();
    return;
  }

  try {
    const payload = await apiRequest(
      `/availability?professionalId=${encodeURIComponent(professionalId)}&date=${encodeURIComponent(date)}`,
      { method: "GET" },
    );
    state.selectedSlot = "";
    renderSlots(payload.slots || []);
    updateSummary();
  } catch (error) {
    state.selectedSlot = "";
    renderSlots([]);
    updateSummary();
    showToast("error", error.message);
  }
}

function fillBookingFormFromUser() {
  if (!state.user) {
    return;
  }
  elements.patientName.value = state.user.nome || "";
  elements.patientEmail.value = state.user.email || "";
}

function renderAppointments() {
  if (!state.user) {
    elements.appointmentsList.innerHTML = '<article class="empty-card">Faça login para visualizar seus agendamentos.</article>';
    return;
  }

  if (!state.appointments.length) {
    elements.appointmentsList.innerHTML = '<article class="empty-card">Ainda não há consultas agendadas para esta conta.</article>';
    return;
  }

  elements.appointmentsList.innerHTML = state.appointments
    .map(
      (item) => `
        <article class="appointment-card">
          <div>
            <p class="eyebrow">Consulta agendada</p>
            <h3>${item.professionalName}</h3>
            <p>${item.professionalTitle}</p>
          </div>
          <div class="appointment-tags">
            <span class="chip">${state.services[item.servico] || item.servico}</span>
            <span class="chip">${state.modes[item.modalidade] || item.modalidade}</span>
            <span class="chip">${item.data} às ${item.hora}</span>
          </div>
          <p>${item.observacoes || "Sem observações adicionais registradas."}</p>
          <div class="appointment-actions">
            <button class="action-btn primary" data-room="${item.roomName}" type="button">Entrar na sala</button>
            <button class="action-btn danger" data-delete="${item.id}" type="button">Cancelar</button>
          </div>
        </article>
      `,
    )
    .join("");

  elements.appointmentsList.querySelectorAll("[data-room]").forEach((button) => {
    button.addEventListener("click", () => openVideoRoom(button.dataset.room));
  });

  elements.appointmentsList.querySelectorAll("[data-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      const confirmed = window.confirm("Deseja realmente cancelar este agendamento?");
      if (!confirmed) {
        return;
      }

      try {
        await apiRequest(`/appointments/${button.dataset.delete}`, { method: "DELETE" });
        showToast("success", "Agendamento cancelado com sucesso.");
        await loadAppointments();
        await refreshAvailability();
      } catch (error) {
        showToast("error", error.message);
      }
    });
  });
}

function openVideoRoom(roomName) {
  elements.videoShell.innerHTML = `
    <iframe
      src="https://meet.jit.si/${roomName}#config.prejoinPageEnabled=false"
      title="Sala de consulta online"
      allow="camera; microphone; fullscreen; display-capture"
    ></iframe>
  `;
  openModal(elements.videoModal);
}

async function loadProfessionals() {
  const payload = await apiRequest("/professionals", { method: "GET" });
  state.professionals = payload.professionals || [];
  state.services = payload.services || {};
  state.modes = payload.modes || {};
  renderProfessionals();
  renderSelectOptions();
  updateSummary();
}

async function loadSession() {
  const token = getSessionToken();
  if (!token) {
    state.user = null;
    updateHeader();
    fillBookingFormFromUser();
    renderAppointments();
    return;
  }

  try {
    const payload = await apiRequest("/me", { method: "GET" });
    state.user = payload.user;
    updateHeader();
    fillBookingFormFromUser();
    await loadAppointments();
  } catch (error) {
    setSessionToken(null);
    state.user = null;
    updateHeader();
    renderAppointments();
  }
}

async function loadAppointments() {
  if (!state.user) {
    state.appointments = [];
    renderAppointments();
    return;
  }

  const payload = await apiRequest("/appointments", { method: "GET" });
  state.appointments = payload.appointments || [];
  renderAppointments();
}

async function handleLogin(event) {
  event.preventDefault();
  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;

  if (!isValidEmail(email)) {
    showToast("error", "Digite um email válido.");
    return;
  }
  if (!password) {
    showToast("error", "Digite a sua senha.");
    return;
  }

  try {
    const payload = await apiRequest("/login", {
      method: "POST",
      body: JSON.stringify({ email, senha: password }),
    });
    setSessionToken(payload.token);
    state.user = payload.user;
    updateHeader();
    fillBookingFormFromUser();
    await loadAppointments();
    closeModal(elements.authModal);
    showToast("success", "Login realizado com sucesso.");
  } catch (error) {
    showToast("error", error.message);
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const role = elements.registerRole.value;
  const name = document.getElementById("registerName").value.trim();
  const email = document.getElementById("registerEmail").value.trim();
  const password = document.getElementById("registerPassword").value;
  const council = document.getElementById("registerCouncil").value;
  const documentId = document.getElementById("registerDocument").value.trim().toUpperCase();

  if (!isValidName(name)) {
    showToast("error", "Informe um nome com pelo menos 3 caracteres.");
    return;
  }
  if (!isValidEmail(email)) {
    showToast("error", "Informe um email válido.");
    return;
  }
  if (!isStrongPassword(password)) {
    showToast("error", "A senha deve ter pelo menos 8 caracteres.");
    return;
  }
  if (role === "profissional" && (!council || !isValidProfessionalDocument(council, documentId))) {
    showToast("error", "Informe conselho e registro profissional válidos.");
    return;
  }

  try {
    await apiRequest("/register", {
      method: "POST",
      body: JSON.stringify({
        nome: name,
        email,
        senha: password,
        tipo: role,
        conselho: role === "profissional" ? council : null,
        registroProfissional: role === "profissional" ? documentId : null,
      }),
    });
    setAuthTab("login");
    elements.registerForm.reset();
    setRole("cliente");
    showToast("success", "Cadastro criado. Faça login para continuar.");
  } catch (error) {
    showToast("error", error.message);
  }
}

async function handleBooking(event) {
  event.preventDefault();

  if (!state.user) {
    openModal(elements.authModal);
    setAuthTab("login");
    showToast("error", "Faça login para concluir o agendamento.");
    return;
  }

  const payload = {
    professionalId: elements.professionalId.value,
    servico: elements.serviceSelect.value,
    modalidade: elements.modeSelect.value,
    data: elements.appointmentDate.value,
    hora: state.selectedSlot,
    nome: elements.patientName.value.trim(),
    email: elements.patientEmail.value.trim(),
    telefone: elements.patientPhone.value.trim(),
    observacoes: elements.appointmentNotes.value.trim(),
  };

  if (!payload.data || !payload.hora) {
    showToast("error", "Selecione uma data e um horário disponível.");
    return;
  }
  if (!isValidName(payload.nome)) {
    showToast("error", "Informe um nome válido.");
    return;
  }
  if (!isValidEmail(payload.email)) {
    showToast("error", "Informe um email válido.");
    return;
  }
  if (!isValidPhone(payload.telefone)) {
    showToast("error", "Informe um telefone válido.");
    return;
  }

  try {
    await apiRequest("/appointments", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showToast("success", "Agendamento confirmado com sucesso.");
    elements.bookingForm.reset();
    fillBookingFormFromUser();
    state.selectedSlot = "";
    updateSummary();
    await loadAppointments();
    await refreshAvailability();
  } catch (error) {
    showToast("error", error.message);
  }
}

async function handleAuthButton() {
  if (!state.user) {
    openModal(elements.authModal);
    setAuthTab("login");
    return;
  }

  try {
    await apiRequest("/logout", { method: "POST" });
  } catch (error) {
  }

  setSessionToken(null);
  state.user = null;
  state.appointments = [];
  updateHeader();
  renderAppointments();
  showToast("success", "Sessão encerrada.");
}

function setRole(role) {
  elements.registerRole.value = role;
  elements.roleButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.role === role);
  });
  elements.professionalFields.classList.toggle("hidden", role !== "profissional");
}

function registerEvents() {
  elements.menuToggle.addEventListener("click", () => {
    const isOpen = elements.menuNav.classList.toggle("open");
    elements.menuToggle.setAttribute("aria-expanded", String(isOpen));
  });

  document.querySelectorAll(".site-nav a").forEach((link) => {
    link.addEventListener("click", () => {
      elements.menuNav.classList.remove("open");
      elements.menuToggle.setAttribute("aria-expanded", "false");
    });
  });

  elements.openAuthModal.addEventListener("click", handleAuthButton);
  elements.closeAuthModal.addEventListener("click", () => closeModal(elements.authModal));
  elements.closeVideoModal.addEventListener("click", () => {
    elements.videoShell.innerHTML = "";
    closeModal(elements.videoModal);
  });
  elements.tabLogin.addEventListener("click", () => setAuthTab("login"));
  elements.tabRegister.addEventListener("click", () => setAuthTab("register"));
  elements.loginForm.addEventListener("submit", handleLogin);
  elements.registerForm.addEventListener("submit", handleRegister);
  elements.bookingForm.addEventListener("submit", handleBooking);
  elements.dashboardShortcut.addEventListener("click", () => {
    document.getElementById("dashboardSection").scrollIntoView({ behavior: "smooth" });
  });
  elements.roleButtons.forEach((button) => {
    button.addEventListener("click", () => setRole(button.dataset.role));
  });
  elements.professionalId.addEventListener("change", refreshAvailability);
  elements.appointmentDate.addEventListener("change", refreshAvailability);
  elements.serviceSelect.addEventListener("change", updateSummary);
  elements.modeSelect.addEventListener("change", updateSummary);

  [elements.authModal, elements.videoModal].forEach((modal) => {
    modal.addEventListener("click", (event) => {
      if (event.target === modal) {
        if (modal === elements.videoModal) {
          elements.videoShell.innerHTML = "";
        }
        closeModal(modal);
      }
    });
  });
}

async function init() {
  registerEvents();
  elements.appointmentDate.min = new Date().toISOString().split("T")[0];

  try {
    await loadProfessionals();
    await loadSession();
    await refreshAvailability();
  } catch (error) {
    showToast("error", error.message);
  }
}

init();
