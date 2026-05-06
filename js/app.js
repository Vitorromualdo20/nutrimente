const API_BASE = window.NUTRIMENTE_API_URL
  || (window.location.protocol.startsWith("http") ? `${window.location.origin}/api` : "http://127.0.0.1:8000/api");
const SESSION_KEY = "nutrimente_session_token";

const state = {
  user: null,
  professionals: [],
  activeProfileSlug: "",
  services: {},
  servicePrices: {},
  modes: {},
  modePriceAdjustments: {},
  weekdays: {},
  selectedSlot: "",
  appointments: [],
  notifications: [],
  professionalDashboard: null,
  adminDashboard: null,
  wallet: {
    balanceCents: 0,
    balanceFormatted: "R$ 0,00",
    transactions: [],
    pendingTopUps: [],
    topUpOptions: [],
    paymentMethods: {},
  },
  deferredPrompt: null,
  shownBrowserNotifications: new Set(),
};

const elements = {
  menuToggle: document.getElementById("menuToggle"),
  menuNav: document.getElementById("menuNav"),
  navNotifications: document.getElementById("navNotifications"),
  navProfessional: document.getElementById("navProfessional"),
  navAdmin: document.getElementById("navAdmin"),
  authModal: document.getElementById("authModal"),
  openAuthModal: document.getElementById("openAuthModal"),
  closeAuthModal: document.getElementById("closeAuthModal"),
  tabLogin: document.getElementById("tabLogin"),
  tabRegister: document.getElementById("tabRegister"),
  loginForm: document.getElementById("loginForm"),
  forgotPasswordForm: document.getElementById("forgotPasswordForm"),
  registerForm: document.getElementById("registerForm"),
  showForgotPassword: document.getElementById("showForgotPassword"),
  backToLogin: document.getElementById("backToLogin"),
  confirmResetPassword: document.getElementById("confirmResetPassword"),
  registerRole: document.getElementById("registerRole"),
  roleButtons: Array.from(document.querySelectorAll(".segment-btn")),
  professionalFields: document.getElementById("professionalFields"),
  walletSection: document.getElementById("walletSection"),
  walletForm: document.getElementById("walletForm"),
  walletAmount: document.getElementById("walletAmount"),
  walletPresetAmounts: document.getElementById("walletPresetAmounts"),
  walletPaymentMethod: document.getElementById("walletPaymentMethod"),
  walletBalance: document.getElementById("walletBalance"),
  walletBalanceHint: document.getElementById("walletBalanceHint"),
  walletPendingTopups: document.getElementById("walletPendingTopups"),
  walletTransactions: document.getElementById("walletTransactions"),
  walletPriceGuide: document.getElementById("walletPriceGuide"),
  dashboardSection: document.getElementById("dashboardSection"),
  dashboardShortcut: document.getElementById("dashboardShortcut"),
  installAppButton: document.getElementById("installAppButton"),
  notificationsSection: document.getElementById("notificationsSection"),
  notificationsList: document.getElementById("notificationsList"),
  enableBrowserNotifications: document.getElementById("enableBrowserNotifications"),
  markNotificationsRead: document.getElementById("markNotificationsRead"),
  professionalSection: document.getElementById("professionalSection"),
  adminSection: document.getElementById("adminSection"),
  professionalProfileForm: document.getElementById("professionalProfileForm"),
  professionalAvailabilityForm: document.getElementById("professionalAvailabilityForm"),
  professionalAppointmentsList: document.getElementById("professionalAppointmentsList"),
  adminStats: document.getElementById("adminStats"),
  adminUsersList: document.getElementById("adminUsersList"),
  adminSecurityNotes: document.getElementById("adminSecurityNotes"),
  adminTransactionsList: document.getElementById("adminTransactionsList"),
  profileSection: document.getElementById("profileSection"),
  profileBackButton: document.getElementById("profileBackButton"),
  profileSectionCouncil: document.getElementById("profileSectionCouncil"),
  profileSectionName: document.getElementById("profileSectionName"),
  profileSectionTitle: document.getElementById("profileSectionTitle"),
  profileSectionQuote: document.getElementById("profileSectionQuote"),
  profileSectionChips: document.getElementById("profileSectionChips"),
  profileSectionBio: document.getElementById("profileSectionBio"),
  profileSectionSpecialties: document.getElementById("profileSectionSpecialties"),
  profileSectionApproach: document.getElementById("profileSectionApproach"),
  profileSectionExperience: document.getElementById("profileSectionExperience"),
  profileTitle: document.getElementById("profileTitle"),
  profileBio: document.getElementById("profileBio"),
  profileQuote: document.getElementById("profileQuote"),
  profileSpecialties: document.getElementById("profileSpecialties"),
  profileApproach: document.getElementById("profileApproach"),
  profileExperience: document.getElementById("profileExperience"),
  availabilityGrid: document.getElementById("availabilityGrid"),
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
    const error = new Error(payload.error || payload.message || "Falha inesperada.");
    error.payload = payload;
    throw error;
  }
  return payload;
}

function resetWalletState() {
  state.wallet = {
    balanceCents: 0,
    balanceFormatted: "R$ 0,00",
    transactions: [],
    pendingTopUps: [],
    topUpOptions: [],
    paymentMethods: {},
  };
}

function formatCurrency(cents = 0) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format((Number(cents) || 0) / 100);
}

function parseCurrencyToCents(rawValue) {
  const value = String(rawValue || "").trim().replace(/^R\$\s*/i, "").replace(/\s+/g, "");
  if (!value) {
    return null;
  }

  let normalized = value;
  if (value.includes(",") && value.includes(".")) {
    normalized = value.lastIndexOf(",") > value.lastIndexOf(".")
      ? value.replace(/\./g, "").replace(",", ".")
      : value.replace(/,/g, "");
  } else if (value.includes(",")) {
    normalized = value.replace(/\./g, "").replace(",", ".");
  }

  const amount = Number(normalized);
  if (!Number.isFinite(amount) || amount <= 0) {
    return null;
  }
  return Math.round(amount * 100);
}

function getSelectedPriceCents() {
  const service = elements.serviceSelect?.value;
  const mode = elements.modeSelect?.value;
  return (state.servicePrices[service] || 0) + (state.modePriceAdjustments[mode] || 0);
}

function showToast(type, message) {
  const item = document.createElement("div");
  item.className = `toast ${type}`;
  item.textContent = message;
  elements.toastStack.appendChild(item);
  window.setTimeout(() => item.remove(), 4200);
}

async function withButtonLoading(button, label, task) {
  if (!button) {
    return task();
  }
  const previousText = button.textContent;
  button.disabled = true;
  button.textContent = label;
  try {
    return await task();
  } finally {
    button.disabled = false;
    button.textContent = previousText;
  }
}

function setAuthTab(tab) {
  const isLogin = tab === "login";
  elements.tabLogin.classList.toggle("active", isLogin);
  elements.tabRegister.classList.toggle("active", !isLogin);
  elements.loginForm.classList.toggle("hidden", !isLogin);
  elements.forgotPasswordForm.classList.add("hidden");
  elements.registerForm.classList.toggle("hidden", isLogin);
  document.getElementById("authTitle").textContent = isLogin ? "Entrar" : "Criar conta";
}

function openForgotPasswordForm() {
  elements.tabLogin.classList.add("active");
  elements.tabRegister.classList.remove("active");
  elements.loginForm.classList.add("hidden");
  elements.registerForm.classList.add("hidden");
  elements.forgotPasswordForm.classList.remove("hidden");
  document.getElementById("authTitle").textContent = "Recuperar senha";
}

function openModal(modal) {
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
}

function closeModal(modal) {
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
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

function normalizeProfessionalDocument(documentId) {
  return documentId.trim().toUpperCase().replace(/\s+/g, "");
}

function isValidProfessionalDocument(council, documentId) {
  const value = normalizeProfessionalDocument(documentId);
  const patterns = {
    CFP: /^\d{2}\/\d{4,6}(?:-\d)?$/,
    CFN: /^\d{4,6}(?:\/[A-Z]{2})?$/,
  };
  return Boolean(patterns[council] && patterns[council].test(value));
}

function splitTextarea(value) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function updateHeader() {
  const loggedIn = Boolean(state.user);
  const professional = loggedIn && state.user.tipo === "profissional";
  const admin = loggedIn && state.user.tipo === "admin";
  elements.openAuthModal.textContent = loggedIn ? `${state.user.nome.split(" ")[0]} | Sair` : "Entrar";
  elements.dashboardShortcut.classList.toggle("hidden", !loggedIn);
  elements.walletSection.classList.toggle("hidden", !loggedIn);
  elements.dashboardSection.classList.toggle("hidden", !loggedIn);
  elements.notificationsSection.classList.toggle("hidden", !loggedIn);
  elements.navNotifications.classList.toggle("hidden", !loggedIn);
  elements.professionalSection.classList.toggle("hidden", !professional);
  elements.navProfessional.classList.toggle("hidden", !professional);
  elements.adminSection.classList.toggle("hidden", !admin);
  elements.navAdmin.classList.toggle("hidden", !admin);
}

function fillBookingFormFromUser() {
  if (!state.user) {
    return;
  }
  elements.patientName.value = state.user.nome || "";
  elements.patientEmail.value = state.user.email || "";
}

function renderWalletPriceGuide() {
  if (!elements.walletPriceGuide) {
    return;
  }
  const entries = Object.entries(state.services)
    .filter(([service]) => state.servicePrices[service])
    .map(([service, label]) => `
      <span class="chip">${label}: ${formatCurrency(state.servicePrices[service])}</span>
    `);
  elements.walletPriceGuide.innerHTML = entries.join("");
}

function renderWalletTopUpOptions() {
  if (!elements.walletPresetAmounts) {
    return;
  }
  const options = state.wallet.topUpOptions || [];
  if (!options.length) {
    elements.walletPresetAmounts.innerHTML = "";
    return;
  }

  elements.walletPresetAmounts.innerHTML = options.map((item) => `
    <button class="ghost-btn wallet-preset-btn" data-wallet-preset="${item.amountCents}" type="button">${item.amountFormatted}</button>
  `).join("");

  elements.walletPresetAmounts.querySelectorAll("[data-wallet-preset]").forEach((button) => {
    button.addEventListener("click", () => {
      elements.walletAmount.value = formatCurrency(Number(button.dataset.walletPreset));
    });
  });
}

function renderWalletPaymentMethods() {
  if (!elements.walletPaymentMethod) {
    return;
  }
  const methods = Object.entries(state.wallet.paymentMethods || {});
  if (!methods.length) {
    return;
  }

  const currentValue = elements.walletPaymentMethod.value;
  elements.walletPaymentMethod.innerHTML = methods.map(([value, label]) => `
    <option value="${value}">${label}</option>
  `).join("");
  if (methods.some(([value]) => value === currentValue)) {
    elements.walletPaymentMethod.value = currentValue;
  }
}

function renderPendingTopUps() {
  if (!elements.walletPendingTopups) {
    return;
  }
  if (!state.user) {
    elements.walletPendingTopups.innerHTML = '<article class="empty-card">Faça login para gerir pagamentos pendentes.</article>';
    return;
  }
  if (!state.wallet.pendingTopUps.length) {
    elements.walletPendingTopups.innerHTML = '<article class="empty-card">Nenhum pagamento pendente no momento.</article>';
    return;
  }

  elements.walletPendingTopups.innerHTML = state.wallet.pendingTopUps.map((item) => `
    <article class="wallet-transaction credit">
      <div class="notification-meta">
        <strong>Recarga pendente</strong>
        <span>${new Date(item.createdAt).toLocaleString("pt-BR")}</span>
      </div>
      <p>${item.amountFormatted} via ${item.paymentMethodLabel}. Referência: ${item.externalReference}.</p>
      <div class="panel-toolbar">
        <button class="primary-btn" data-confirm-topup="${item.id}" type="button">Confirmar pagamento</button>
      </div>
    </article>
  `).join("");

  elements.walletPendingTopups.querySelectorAll("[data-confirm-topup]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        const payload = await apiRequest(`/wallet/topups/${button.dataset.confirmTopup}/confirm`, { method: "POST" });
        state.wallet = payload.wallet || state.wallet;
        renderWallet();
        updateSummary();
        showToast("success", payload.message);
      } catch (error) {
        showToast("error", error.message);
      }
    });
  });
}

function renderWallet() {
  if (!elements.walletBalance || !elements.walletTransactions) {
    return;
  }

  if (!state.user) {
    elements.walletBalance.textContent = "R$ 0,00";
    elements.walletBalanceHint.textContent = "Adicione fundos para pagar consultas diretamente pela plataforma.";
    elements.walletPendingTopups.innerHTML = '<article class="empty-card">Faça login para gerir pagamentos pendentes.</article>';
    elements.walletTransactions.innerHTML = '<article class="empty-card">Faça login para visualizar sua carteira.</article>';
    renderWalletPriceGuide();
    renderWalletTopUpOptions();
    renderWalletPaymentMethods();
    return;
  }

  const balanceCents = state.wallet.balanceCents || 0;
  const selectedPrice = getSelectedPriceCents();
  elements.walletBalance.textContent = state.wallet.balanceFormatted || formatCurrency(balanceCents);
  if (selectedPrice > 0) {
    const difference = balanceCents - selectedPrice;
    elements.walletBalanceHint.textContent = difference >= 0
      ? `Saldo suficiente para a consulta selecionada. Restariam ${formatCurrency(difference)}.`
      : `Faltam ${formatCurrency(Math.abs(difference))} para pagar a consulta selecionada.`;
  } else {
    elements.walletBalanceHint.textContent = "Adicione fundos para pagar consultas diretamente pela plataforma.";
  }

  renderPendingTopUps();
  if (!state.wallet.transactions.length) {
    elements.walletTransactions.innerHTML = '<article class="empty-card">Ainda não há movimentações na sua carteira.</article>';
  } else {
    elements.walletTransactions.innerHTML = state.wallet.transactions.map((item) => `
      <article class="wallet-transaction ${item.direction}">
        <div class="notification-meta">
          <strong>${item.kind === "deposit" ? "Recarga" : item.kind === "refund" ? "Estorno" : "Pagamento"}</strong>
          <span>${new Date(item.createdAt).toLocaleString("pt-BR")}</span>
        </div>
        <p>${item.description}</p>
        <strong class="wallet-amount">${item.direction === "credit" ? "+" : "-"} ${item.amountFormatted}</strong>
      </article>
    `).join("");
  }

  renderWalletPriceGuide();
  renderWalletTopUpOptions();
  renderWalletPaymentMethods();
}

function renderProfessionals() {
  if (!state.professionals.length) {
    elements.professionalsGrid.innerHTML = '<article class="empty-card">Nenhum profissional disponível.</article>';
    return;
  }

  elements.professionalsGrid.innerHTML = state.professionals.map((item) => `
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
      <a class="card-link" href="#perfil-${item.slug}" data-profile="${item.slug}">Ver perfil completo</a>
    </article>
  `).join("");

  elements.professionalsGrid.querySelectorAll("[data-profile]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      openProfessionalProfile(link.dataset.profile);
    });
  });
}

function renderListItems(listElement, items = []) {
  listElement.innerHTML = items.map((item) => `<li>${item}</li>`).join("");
}

function closeProfessionalProfile() {
  state.activeProfileSlug = "";
  elements.profileSection.classList.add("hidden");
}

function renderProfessionalProfile(professional) {
  elements.profileSectionCouncil.textContent = `${professional.conselho} • ${professional.registroProfissional}`;
  elements.profileSectionName.textContent = professional.nome;
  elements.profileSectionTitle.textContent = professional.titulo;
  elements.profileSectionQuote.textContent = professional.frase;
  elements.profileSectionBio.textContent = professional.bio;
  elements.profileSectionChips.innerHTML = `
    <span class="chip">${professional.titulo}</span>
    <span class="chip">${professional.especialidades[0] || "Atendimento especializado"}</span>
  `;
  renderListItems(elements.profileSectionSpecialties, professional.especialidades || []);
  renderListItems(elements.profileSectionApproach, professional.abordagem || []);
  renderListItems(elements.profileSectionExperience, professional.experiencia || []);
}

function openProfessionalProfile(slug, options = {}) {
  const { scroll = true, pushHash = true } = options;
  const professional = state.professionals.find((item) => item.slug === slug);
  if (!professional) {
    showToast("error", "Perfil profissional não encontrado.");
    return;
  }

  state.activeProfileSlug = slug;
  renderProfessionalProfile(professional);
  elements.profileSection.classList.remove("hidden");

  if (pushHash && window.location.hash !== `#perfil-${slug}`) {
    window.location.hash = `perfil-${slug}`;
  }
  if (scroll) {
    elements.profileSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function syncProfileRoute() {
  const hash = window.location.hash || "";
  if (!hash.startsWith("#perfil-")) {
    closeProfessionalProfile();
    return;
  }

  const slug = hash.replace("#perfil-", "").trim();
  if (!slug) {
    closeProfessionalProfile();
    return;
  }
  openProfessionalProfile(slug, { scroll: false, pushHash: false });
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
  const professional = state.professionals.find((item) => String(item.id) === elements.professionalId.value);
  const date = elements.appointmentDate.value;
  const slot = state.selectedSlot;
  const service = state.services[elements.serviceSelect.value];
  const mode = state.modes[elements.modeSelect.value] || elements.modeSelect.value;
  const priceCents = getSelectedPriceCents();
  const balanceCents = state.wallet.balanceCents || 0;

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

  const balanceLine = state.user
    ? `<p class="summary-note ${balanceCents >= priceCents ? "" : "warning"}">${balanceCents >= priceCents ? "Saldo suficiente para concluir este agendamento usando seus créditos." : `Saldo insuficiente. Faltam ${formatCurrency(priceCents - balanceCents)}.`}</p>`
    : '<p class="summary-note">Faça login e adicione saldo para concluir o agendamento.</p>';
  const insufficientActions = state.user && balanceCents < priceCents
    ? `
      <div class="panel-toolbar">
        <button class="secondary-btn" data-wallet-shortcut="${priceCents - balanceCents}" type="button">Adicionar exatamente a diferença</button>
      </div>
    `
    : "";

  elements.bookingSummary.innerHTML = `
    <p class="summary-label">Resumo da escolha</p>
    <h3>${professional.nome}</h3>
    <p>${professional.titulo}</p>
    <ul class="summary-list">
      <li>Serviço: ${service}</li>
      <li>Modalidade: ${mode}</li>
      <li>Data: ${new Date(`${date}T00:00:00`).toLocaleDateString("pt-BR")}</li>
      <li>Horário: ${slot}</li>
      <li>Valor: ${formatCurrency(priceCents)}</li>
      ${state.user ? `<li>Saldo atual: ${formatCurrency(balanceCents)}</li>` : ""}
    </ul>
    ${balanceLine}
    ${insufficientActions}
  `;

  const shortcutButton = elements.bookingSummary.querySelector("[data-wallet-shortcut]");
  if (shortcutButton) {
    shortcutButton.addEventListener("click", () => {
      const missingCents = Number(shortcutButton.dataset.walletShortcut || 0);
      elements.walletAmount.value = formatCurrency(missingCents);
      document.getElementById("walletSection").scrollIntoView({ behavior: "smooth" });
    });
  }
}
function renderSlots(slots) {
  elements.slotsGrid.innerHTML = slots.map((item) => `
    <button class="slot-btn ${item.hora === state.selectedSlot ? "selected" : ""}" data-slot="${item.hora}" type="button" ${item.disponivel ? "" : "disabled"}>
      ${item.hora}
    </button>
  `).join("");

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
    const payload = await apiRequest(`/availability?professionalId=${encodeURIComponent(professionalId)}&date=${encodeURIComponent(date)}`, { method: "GET" });
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

function renderPatientAppointments() {
  if (!state.user) {
    elements.appointmentsList.innerHTML = '<article class="empty-card">Faça login para visualizar seus agendamentos.</article>';
    return;
  }
  if (!state.appointments.length) {
    elements.appointmentsList.innerHTML = '<article class="empty-card">Ainda não há consultas agendadas para esta conta.</article>';
    return;
  }

  elements.appointmentsList.innerHTML = state.appointments.map((item) => `
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
        <button class="action-btn primary" data-reschedule="${item.id}" type="button">Reagendar</button>
        <button class="action-btn danger" data-delete="${item.id}" type="button">Cancelar</button>
      </div>
    </article>
  `).join("");

  elements.appointmentsList.querySelectorAll("[data-room]").forEach((button) => {
    button.addEventListener("click", () => openVideoRoom(button.dataset.room));
  });
  elements.appointmentsList.querySelectorAll("[data-reschedule]").forEach((button) => {
    button.addEventListener("click", async () => {
      const item = state.appointments.find((appointment) => String(appointment.id) === button.dataset.reschedule);
      if (!item) {
        return;
      }
      const newDate = window.prompt("Nova data (AAAA-MM-DD):", item.data);
      if (!newDate) {
        return;
      }
      const newTime = window.prompt("Novo horário (HH:MM):", item.hora);
      if (!newTime) {
        return;
      }
      try {
        const payload = await apiRequest(`/appointments/${item.id}`, {
          method: "PUT",
          body: JSON.stringify({ data: newDate, hora: newTime }),
        });
        showToast("success", payload.message);
        await Promise.all([loadWallet(), loadAppointments(), loadNotifications(), refreshAvailability()]);
      } catch (error) {
        showToast("error", error.message);
      }
    });
  });
  elements.appointmentsList.querySelectorAll("[data-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!window.confirm("Deseja realmente cancelar este agendamento?")) {
        return;
      }
      try {
        await apiRequest(`/appointments/${button.dataset.delete}`, { method: "DELETE" });
        showToast("success", "Agendamento cancelado com sucesso.");
        await Promise.all([loadWallet(), loadAppointments(), loadNotifications(), refreshAvailability()]);
      } catch (error) {
        showToast("error", error.message);
      }
    });
  });
}

function renderNotifications() {
  if (!state.user) {
    elements.notificationsList.innerHTML = '<article class="empty-card">Faça login para visualizar notificações.</article>';
    return;
  }
  if (!state.notifications.length) {
    elements.notificationsList.innerHTML = '<article class="empty-card">Nenhuma notificação disponível no momento.</article>';
    return;
  }
  elements.notificationsList.innerHTML = state.notifications.map((item) => `
    <article class="notification-card ${item.isRead ? "" : "unread"}">
      <div class="notification-meta">
        <strong>${item.title}</strong>
        <span>${new Date(item.createdAt).toLocaleString("pt-BR")}</span>
      </div>
      <p>${item.message}</p>
    </article>
  `).join("");
}

function notifyInBrowser() {
  if (!("Notification" in window) || Notification.permission !== "granted") {
    return;
  }
  state.notifications.slice(0, 5).forEach((item) => {
    if (state.shownBrowserNotifications.has(item.id)) {
      return;
    }
    if (item.isRead) {
      return;
    }
    state.shownBrowserNotifications.add(item.id);
    new Notification(item.title, { body: item.message });
  });
}

function renderAvailabilityEditor() {
  if (!state.professionalDashboard) {
    elements.availabilityGrid.innerHTML = "";
    return;
  }
  const availability = state.professionalDashboard.availability || {};
  elements.availabilityGrid.innerHTML = Object.entries(state.weekdays).map(([day, label]) => `
    <article class="day-card">
      <h4>${label}</h4>
      <div class="day-slots">
        ${state.professionalDashboard.slots.map((slot) => `
          <label class="check-chip">
            <input type="checkbox" data-day="${day}" value="${slot}" ${availability[day]?.includes(slot) ? "checked" : ""} />
            <span>${slot}</span>
          </label>
        `).join("")}
      </div>
    </article>
  `).join("");
}

function renderProfessionalDashboard() {
  if (!state.user || state.user.tipo !== "profissional") {
    elements.professionalAppointmentsList.innerHTML = '<article class="empty-card">Faça login como profissional para gerir consultas e prontuários.</article>';
    return;
  }
  if (!state.professionalDashboard) {
    elements.professionalAppointmentsList.innerHTML = '<article class="empty-card">Carregando painel profissional...</article>';
    return;
  }

  const profile = state.professionalDashboard.profile;
  elements.profileTitle.value = profile.titulo || "";
  elements.profileBio.value = profile.bio || "";
  elements.profileQuote.value = profile.frase || "";
  elements.profileSpecialties.value = (profile.especialidades || []).join("\n");
  elements.profileApproach.value = (profile.abordagem || []).join("\n");
  elements.profileExperience.value = (profile.experiencia || []).join("\n");
  renderAvailabilityEditor();

  if (!state.professionalDashboard.appointments.length) {
    elements.professionalAppointmentsList.innerHTML = '<article class="empty-card">Nenhuma consulta vinculada ao seu perfil até agora.</article>';
    return;
  }

  elements.professionalAppointmentsList.innerHTML = state.professionalDashboard.appointments.map((item) => `
    <article class="record-card">
      <div class="notification-meta">
        <div>
          <p class="eyebrow">Consulta com paciente</p>
          <h3>${item.patientName}</h3>
        </div>
        <span class="chip">${item.data} às ${item.hora}</span>
      </div>
      <p>${state.services[item.servico] || item.servico} • ${state.modes[item.modalidade] || item.modalidade}</p>
      <p>${item.patientEmail} • ${item.patientPhone}</p>
      <p>${item.observacoes || "Sem observações prévias do paciente."}</p>
      <div class="record-grid">
        <label>
          Evolução / prontuário
          <textarea rows="5" data-record-notes="${item.appointmentId}">${item.record.notes || ""}</textarea>
        </label>
        <label>
          Plano / próximos passos
          <textarea rows="5" data-record-plan="${item.appointmentId}">${item.record.plan || ""}</textarea>
        </label>
      </div>
      <div class="appointment-actions">
        <button class="action-btn primary" data-save-record="${item.appointmentId}" type="button">Salvar prontuário</button>
        <button class="action-btn primary" data-room="${item.roomName}" type="button">Abrir sala</button>
      </div>
    </article>
  `).join("");

  elements.professionalAppointmentsList.querySelectorAll("[data-room]").forEach((button) => {
    button.addEventListener("click", () => openVideoRoom(button.dataset.room));
  });

  elements.professionalAppointmentsList.querySelectorAll("[data-save-record]").forEach((button) => {
    button.addEventListener("click", async () => {
      const appointmentId = button.dataset.saveRecord;
      const notes = elements.professionalAppointmentsList.querySelector(`[data-record-notes="${appointmentId}"]`).value;
      const plan = elements.professionalAppointmentsList.querySelector(`[data-record-plan="${appointmentId}"]`).value;
      try {
        await apiRequest(`/records/${appointmentId}`, {
          method: "PUT",
          body: JSON.stringify({ notes, plan }),
        });
        showToast("success", "Prontuário salvo com sucesso.");
        await Promise.all([loadProfessionalDashboard(), loadNotifications()]);
      } catch (error) {
        showToast("error", error.message);
      }
    });
  });
}

function renderAdminDashboard() {
  if (!state.user || state.user.tipo !== "admin") {
    elements.adminStats.innerHTML = '<article class="empty-card">Faça login como administrador para visualizar utilizadores e transações.</article>';
    elements.adminUsersList.innerHTML = '<article class="empty-card">Sem dados carregados.</article>';
    elements.adminSecurityNotes.innerHTML = '<article class="empty-card">Sem dados carregados.</article>';
    elements.adminTransactionsList.innerHTML = '<article class="empty-card">Sem transações carregadas.</article>';
    return;
  }
  if (!state.adminDashboard) {
    elements.adminStats.innerHTML = '<article class="empty-card">Carregando painel administrativo...</article>';
    return;
  }

  const stats = state.adminDashboard.stats || {};
  elements.adminStats.innerHTML = `
    <article class="story-card"><h3>Utilizadores</h3><p>${stats.users || 0} contas ativas</p></article>
    <article class="story-card"><h3>Pacientes</h3><p>${stats.patients || 0} pacientes cadastrados</p></article>
    <article class="story-card"><h3>Profissionais</h3><p>${stats.professionals || 0} profissionais vinculados</p></article>
    <article class="story-card"><h3>Volume em carteira</h3><p>${stats.walletVolumeFormatted || "R$ 0,00"}</p></article>
  `;

  elements.adminUsersList.innerHTML = (state.adminDashboard.users || []).map((item) => `
    <article class="wallet-transaction">
      <div class="notification-meta">
        <strong>${item.nome}</strong>
        <span>${item.tipo}</span>
      </div>
      <p>${item.email}</p>
    </article>
  `).join("") || '<article class="empty-card">Nenhum utilizador encontrado.</article>';

  elements.adminSecurityNotes.innerHTML = `
    <article class="wallet-transaction">
      <strong>LGPD</strong>
      <p>${state.adminDashboard.security?.lgpd || ""}</p>
    </article>
    <article class="wallet-transaction">
      <strong>Gateway</strong>
      <p>${state.adminDashboard.security?.gatewayMode || ""}</p>
    </article>
  `;

  elements.adminTransactionsList.innerHTML = (state.adminDashboard.transactions || []).map((item) => `
    <article class="wallet-transaction ${item.direction}">
      <div class="notification-meta">
        <strong>${item.kind} • ${item.amountFormatted}</strong>
        <span>${new Date(item.createdAt).toLocaleString("pt-BR")}</span>
      </div>
      <p>${item.nome} • ${item.email}</p>
      <p>${item.description}</p>
    </article>
  `).join("") || '<article class="empty-card">Nenhuma transação encontrada.</article>';
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
  state.servicePrices = payload.servicePrices || {};
  state.modes = payload.modes || {};
  state.modePriceAdjustments = payload.modePriceAdjustments || {};
  state.weekdays = payload.weekdays || {};
  renderProfessionals();
  renderSelectOptions();
  renderWallet();
  updateSummary();
  syncProfileRoute();
}
async function loadSession() {
  if (!getSessionToken()) {
    state.user = null;
    resetWalletState();
    updateHeader();
    renderWallet();
    updateSummary();
    renderPatientAppointments();
    renderNotifications();
    renderProfessionalDashboard();
    renderAdminDashboard();
    return;
  }
  try {
    const payload = await apiRequest("/me", { method: "GET" });
    state.user = payload.user;
    updateHeader();
    fillBookingFormFromUser();
    await Promise.all([loadWallet(), loadAppointments(), loadNotifications(), loadProfessionalDashboard(), loadAdminDashboard()]);
  } catch (error) {
    setSessionToken(null);
    state.user = null;
    resetWalletState();
    updateHeader();
    renderWallet();
    updateSummary();
    renderPatientAppointments();
    renderNotifications();
    renderProfessionalDashboard();
    renderAdminDashboard();
  }
}


async function loadAppointments() {
  if (!state.user) {
    state.appointments = [];
    renderPatientAppointments();
    return;
  }
  const payload = await apiRequest("/appointments", { method: "GET" });
  state.appointments = payload.appointments || [];
  renderPatientAppointments();
}


async function loadWallet() {
  if (!state.user) {
    resetWalletState();
    renderWallet();
    updateSummary();
    return;
  }
  const payload = await apiRequest("/wallet", { method: "GET" });
  state.wallet = {
    balanceCents: payload.balanceCents || 0,
    balanceFormatted: payload.balanceFormatted || formatCurrency(payload.balanceCents || 0),
    transactions: payload.transactions || [],
    pendingTopUps: payload.pendingTopUps || [],
    topUpOptions: payload.topUpOptions || [],
    paymentMethods: payload.paymentMethods || {},
  };
  renderWallet();
  updateSummary();
}


async function loadNotifications() {
  if (!state.user) {
    state.notifications = [];
    renderNotifications();
    return;
  }
  const payload = await apiRequest("/notifications", { method: "GET" });
  state.notifications = payload.notifications || [];
  renderNotifications();
  notifyInBrowser();
}

async function loadProfessionalDashboard() {
  if (!state.user || state.user.tipo !== "profissional") {
    state.professionalDashboard = null;
    renderProfessionalDashboard();
    return;
  }
  const payload = await apiRequest("/professional/dashboard", { method: "GET" });
  state.professionalDashboard = payload;
  renderProfessionalDashboard();
}

async function loadAdminDashboard() {
  if (!state.user || state.user.tipo !== "admin") {
    state.adminDashboard = null;
    renderAdminDashboard();
    return;
  }
  const payload = await apiRequest("/admin/dashboard", { method: "GET" });
  state.adminDashboard = payload;
  renderAdminDashboard();
}

async function handleLogin(event) {
  event.preventDefault();
  const submitButton = elements.loginForm.querySelector('button[type="submit"]');
  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;
  if (!isValidEmail(email) || !password) {
    showToast("error", "Informe email e senha válidos.");
    return;
  }
  try {
    await withButtonLoading(submitButton, "Entrando...", async () => {
      const payload = await apiRequest("/login", {
        method: "POST",
        body: JSON.stringify({ email, senha: password }),
      });
      setSessionToken(payload.token);
      state.user = payload.user;
      updateHeader();
      fillBookingFormFromUser();
      await Promise.all([loadWallet(), loadAppointments(), loadNotifications(), loadProfessionalDashboard(), loadAdminDashboard()]);
      closeModal(elements.authModal);
      showToast("success", "Login realizado com sucesso.");
    });
  } catch (error) {
    showToast("error", error.message);
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const submitButton = elements.registerForm.querySelector('button[type="submit"]');
  const role = elements.registerRole.value;
  const name = document.getElementById("registerName").value.trim();
  const email = document.getElementById("registerEmail").value.trim();
  const password = document.getElementById("registerPassword").value;
  const council = document.getElementById("registerCouncil").value;
  const documentId = normalizeProfessionalDocument(document.getElementById("registerDocument").value);

  if (!isValidName(name) || !isValidEmail(email) || password.length < 8) {
    showToast("error", "Preencha nome, email e senha válidos.");
    return;
  }
  if (role === "profissional" && (!council || !isValidProfessionalDocument(council, documentId))) {
    showToast("error", "Informe conselho e registro profissional válidos.");
    return;
  }

  try {
    await withButtonLoading(submitButton, "Cadastrando...", async () => {
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
    });
  } catch (error) {
    showToast("error", error.message);
  }
}

async function handleForgotPasswordRequest(event) {
  event.preventDefault();
  const submitButton = elements.forgotPasswordForm.querySelector('button[type="submit"]');
  const email = document.getElementById("forgotPasswordEmail").value.trim();
  if (!isValidEmail(email)) {
    showToast("error", "Informe um email válido.");
    return;
  }
  try {
    await withButtonLoading(submitButton, "Gerando...", async () => {
      const payload = await apiRequest("/password-reset/request", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      if (payload.resetToken) {
        document.getElementById("resetToken").value = payload.resetToken;
        showToast("success", `Código gerado: ${payload.resetToken}`);
      } else {
        showToast("success", payload.message);
      }
    });
  } catch (error) {
    showToast("error", error.message);
  }
}

async function handleForgotPasswordConfirm() {
  const button = elements.confirmResetPassword;
  const token = document.getElementById("resetToken").value.trim();
  const password = document.getElementById("resetPassword").value;
  if (!token || password.length < 8) {
    showToast("error", "Preencha o código e uma nova senha com pelo menos 8 caracteres.");
    return;
  }
  try {
    await withButtonLoading(button, "Redefinindo...", async () => {
      const payload = await apiRequest("/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({ token, senha: password }),
      });
      showToast("success", payload.message);
      elements.forgotPasswordForm.reset();
      setAuthTab("login");
    });
  } catch (error) {
    showToast("error", error.message);
  }
}

async function handleBooking(event) {
  event.preventDefault();
  const submitButton = elements.bookingForm.querySelector('button[type="submit"]');
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

  if (!payload.data || !payload.hora || !isValidName(payload.nome) || !isValidEmail(payload.email) || !isValidPhone(payload.telefone)) {
    showToast("error", "Preencha corretamente os dados do agendamento.");
    return;
  }

  try {
    await withButtonLoading(submitButton, "Agendando...", async () => {
      await apiRequest("/appointments", { method: "POST", body: JSON.stringify(payload) });
      showToast("success", "Agendamento confirmado com sucesso.");
      elements.bookingForm.reset();
      fillBookingFormFromUser();
      state.selectedSlot = "";
      await Promise.all([loadWallet(), loadAppointments(), loadNotifications(), refreshAvailability()]);
    });
  } catch (error) {
    if (error.payload?.wallet) {
      state.wallet = {
        balanceCents: error.payload.wallet.balanceCents || 0,
        balanceFormatted: error.payload.wallet.balanceFormatted || formatCurrency(error.payload.wallet.balanceCents || 0),
        transactions: error.payload.wallet.transactions || [],
        pendingTopUps: error.payload.wallet.pendingTopUps || [],
        topUpOptions: error.payload.wallet.topUpOptions || [],
        paymentMethods: error.payload.wallet.paymentMethods || {},
      };
      renderWallet();
      updateSummary();
    }
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
  state.notifications = [];
  state.professionalDashboard = null;
  state.adminDashboard = null;
  resetWalletState();
  updateHeader();
  renderWallet();
  renderPatientAppointments();
  renderNotifications();
  renderProfessionalDashboard();
  renderAdminDashboard();
  updateSummary();
  showToast("success", "Sessão encerrada.");
}
function setRole(role) {
  elements.registerRole.value = role;
  elements.roleButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.role === role);
  });
  elements.professionalFields.classList.toggle("hidden", role !== "profissional");
}

async function handleWalletSubmit(event) {
  event.preventDefault();
  if (!state.user) {
    openModal(elements.authModal);
    setAuthTab("login");
    showToast("error", "Faça login para adicionar saldo.");
    return;
  }

  const submitButton = elements.walletForm.querySelector('button[type="submit"]');
  const amountCents = parseCurrencyToCents(elements.walletAmount.value);
  if (amountCents == null) {
    showToast("error", "Informe um valor válido para a recarga.");
    return;
  }

  try {
    await withButtonLoading(submitButton, "Gerando...", async () => {
      const payload = await apiRequest("/wallet/topups", {
        method: "POST",
        body: JSON.stringify({
          amountCents,
          paymentMethod: elements.walletPaymentMethod.value,
        }),
      });
      state.wallet = payload.wallet || state.wallet;
      elements.walletAmount.value = "";
      renderWallet();
      updateSummary();
      showToast("success", payload.message || "Pagamento gerado com sucesso.");
    });
  } catch (error) {
    showToast("error", error.message);
  }
}

async function handleProfileSubmit(event) {
  event.preventDefault();
  const submitButton = elements.professionalProfileForm.querySelector('button[type="submit"]');
  try {
    await withButtonLoading(submitButton, "Salvando...", async () => {
      await apiRequest("/professional/profile", {
        method: "PUT",
        body: JSON.stringify({
          titulo: elements.profileTitle.value.trim(),
          bio: elements.profileBio.value.trim(),
          frase: elements.profileQuote.value.trim(),
          especialidades: splitTextarea(elements.profileSpecialties.value),
          abordagem: splitTextarea(elements.profileApproach.value),
          experiencia: splitTextarea(elements.profileExperience.value),
        }),
      });
      showToast("success", "Perfil profissional atualizado.");
      await Promise.all([loadProfessionalDashboard(), loadProfessionals()]);
    });
  } catch (error) {
    showToast("error", error.message);
  }
}

async function handleAvailabilitySubmit(event) {
  event.preventDefault();
  const submitButton = elements.professionalAvailabilityForm.querySelector('button[type="submit"]');
  const availability = {};
  elements.availabilityGrid.querySelectorAll("input[type='checkbox']").forEach((input) => {
    if (!input.checked) {
      return;
    }
    const day = input.dataset.day;
    availability[day] = availability[day] || [];
    availability[day].push(input.value);
  });

  try {
    await withButtonLoading(submitButton, "Salvando...", async () => {
      await apiRequest("/professional/availability", {
        method: "PUT",
        body: JSON.stringify({ availability }),
      });
      showToast("success", "Horários atualizados com sucesso.");
      await Promise.all([loadProfessionalDashboard(), refreshAvailability()]);
    });
  } catch (error) {
    showToast("error", error.message);
  }
}

async function enableBrowserNotifications() {
  if (!("Notification" in window)) {
    showToast("error", "Este navegador não suporta notificações.");
    return;
  }
  const permission = await Notification.requestPermission();
  if (permission === "granted") {
    showToast("success", "Alertas do navegador ativados.");
    notifyInBrowser();
    return;
  }
  showToast("error", "Permissão de notificações não concedida.");
}

async function registerPwa() {
  if ("serviceWorker" in navigator) {
    await navigator.serviceWorker.register("/service-worker.js");
  }
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    state.deferredPrompt = event;
    elements.installAppButton.classList.remove("hidden");
  });
  elements.installAppButton.addEventListener("click", async () => {
    if (!state.deferredPrompt) {
      return;
    }
    state.deferredPrompt.prompt();
    await state.deferredPrompt.userChoice;
    state.deferredPrompt = null;
    elements.installAppButton.classList.add("hidden");
  });
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
  elements.showForgotPassword.addEventListener("click", openForgotPasswordForm);
  elements.backToLogin.addEventListener("click", () => setAuthTab("login"));
  elements.roleButtons.forEach((button) => button.addEventListener("click", () => setRole(button.dataset.role)));
  elements.loginForm.addEventListener("submit", handleLogin);
  elements.forgotPasswordForm.addEventListener("submit", handleForgotPasswordRequest);
  elements.confirmResetPassword.addEventListener("click", handleForgotPasswordConfirm);
  elements.registerForm.addEventListener("submit", handleRegister);
  elements.walletForm.addEventListener("submit", handleWalletSubmit);
  elements.bookingForm.addEventListener("submit", handleBooking);
  elements.professionalProfileForm.addEventListener("submit", handleProfileSubmit);
  elements.professionalAvailabilityForm.addEventListener("submit", handleAvailabilitySubmit);
  elements.enableBrowserNotifications.addEventListener("click", enableBrowserNotifications);
  elements.markNotificationsRead.addEventListener("click", async () => {
    if (!state.user) {
      return;
    }
    await apiRequest("/notifications/read-all", { method: "POST" });
    await loadNotifications();
  });
  elements.profileBackButton.addEventListener("click", () => {
    closeProfessionalProfile();
    window.location.hash = "profissionais";
    document.getElementById("profissionais").scrollIntoView({ behavior: "smooth" });
  });
  elements.dashboardShortcut.addEventListener("click", () => {
    document.getElementById("dashboardSection").scrollIntoView({ behavior: "smooth" });
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

  window.addEventListener("hashchange", syncProfileRoute);
}

async function init() {
  registerEvents();
  await registerPwa();
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

