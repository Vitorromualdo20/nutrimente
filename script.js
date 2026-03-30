// MENU HAMBURGUER
const menuToggle = document.getElementById('menuToggle');
const menuNav = document.getElementById('menuNav');
menuToggle.onclick = () => menuNav.classList.toggle('active');

// MODAL LOGIN
const modal = document.getElementById('modalLogin');
const abrir = document.getElementById('abrirLogin');
const fechar = document.getElementById('fecharModal');
const formLogin = document.getElementById('formLogin');
const formCadastro = document.getElementById('formCadastro');
const mostrarCadastro = document.getElementById('mostrarCadastro');
const mostrarLogin = document.getElementById('mostrarLogin');
const titulo = document.getElementById('tituloLogin');

// Inputs de cadastro
const cadastroNome = document.getElementById('cadastroNome');
const cadastroEmail = document.getElementById('cadastroEmail');
const cadastroSenha = document.getElementById('cadastroSenha');

// Inputs de Login
const loginEmail = document.getElementById('loginEmail');
const loginSenha = document.getElementById('loginSenha');

const listaAgendamentos = document.getElementById('listaAgendamentos');
const boxAgendamentos = document.getElementById('meusAgendamentos');

let usuarioAtual = JSON.parse(localStorage.getItem('usuarioLogado') || 'null');

abrir.onclick = () => modal.style.display = 'flex';
fechar.onclick = () => modal.style.display = 'none';

mostrarCadastro.onclick = () => { 
  formLogin.style.display = 'none'; 
  formCadastro.style.display = 'block'; 
  titulo.textContent = 'Cadastro'; 
};

mostrarLogin.onclick = () => { 
  formLogin.style.display = 'block'; 
  formCadastro.style.display = 'none'; 
  titulo.textContent = 'Entrar'; 
};

// 🔎 Funções de validação
function validarEmail(email) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email); }
function validarSenha(senha) { return /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$/.test(senha); }
function validarNome(nome) { return /^[A-Za-zÀ-ÿ\s]{3,}$/.test(nome); }
function validarTelefone(tel) { return /^(\(?\d{2}\)?\s?)?\d{4,5}-?\d{4}$/.test(tel); }
function mostrarErro(msg) { alert("⚠️ " + msg); }

// CADASTRO
document.getElementById('btnCadastro').onclick = () => {
  const nome = cadastroNome.value.trim();
  const email = cadastroEmail.value.trim();
  const senha = cadastroSenha.value;

  if (!validarNome(nome)) return mostrarErro('Digite um nome válido (mínimo 3 letras).');
  if (!validarEmail(email)) return mostrarErro('Digite um email válido.');
  if (!validarSenha(senha)) return mostrarErro('A senha deve ter ao menos 6 caracteres, incluindo letras e números.');

  let users = JSON.parse(localStorage.getItem('usuarios') || '[]');
  if (users.find(u => u.email === email)) return mostrarErro('Email já cadastrado!');

  users.push({ nome, email, senha, agendamentos: [] });
  localStorage.setItem('usuarios', JSON.stringify(users));

  alert('✅ Cadastro realizado! Faça login.');
  formCadastro.style.display = 'none';
  formLogin.style.display = 'block';
  titulo.textContent = 'Entrar';
};

// LOGIN
document.getElementById('btnLogin').onclick = () => {
  const email = loginEmail.value.trim();
  const senha = loginSenha.value;
  if (!validarEmail(email)) return mostrarErro('Email inválido.');
  if (senha.length < 1) return mostrarErro('Digite sua senha.');

  const users = JSON.parse(localStorage.getItem('usuarios') || '[]');
  const user = users.find(u => u.email === email && u.senha === senha);
  if (!user) return mostrarErro('Credenciais inválidas.');
  
  usuarioAtual = user;
  localStorage.setItem('usuarioLogado', JSON.stringify(user));
  modal.style.display = 'none';
  atualizarSaudacao();
};

// SAUDAÇÃO E LOGOUT
function atualizarSaudacao() {
  const existente = document.querySelector('.user-menu');
  if (existente) existente.remove();

  const inputNomeAgendamento = document.getElementById('nome');
  const inputEmailAgendamento = document.getElementById('email');

  if (usuarioAtual) {
    abrir.style.display = 'none';
    
    // Puxa os dados para o formulário de agendamento automaticamente
    inputNomeAgendamento.value = usuarioAtual.nome;
    inputEmailAgendamento.value = usuarioAtual.email;

    const userMenu = document.createElement('div');
    userMenu.className = 'user-menu';
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = usuarioAtual.nome.split(' ').map(p => p[0]).join('').substring(0, 2).toUpperCase();
    
    const name = document.createElement('span');
    name.textContent = usuarioAtual.nome.split(' ')[0] + ' ▾';
    
    const dropdown = document.createElement('div');
    dropdown.className = 'user-dropdown';
    const sairBtn = document.createElement('button');
    sairBtn.textContent = 'Sair';
    
    sairBtn.onclick = () => {
      localStorage.removeItem('usuarioLogado');
      usuarioAtual = null;
      userMenu.remove();
      abrir.style.display = 'inline-block';
      boxAgendamentos.style.display = 'none';
      
      // Limpa os campos do formulário de agendamento ao deslogar
      inputNomeAgendamento.value = '';
      inputEmailAgendamento.value = '';
    };
    
    dropdown.appendChild(sairBtn);
    userMenu.appendChild(avatar);
    userMenu.appendChild(name);
    userMenu.appendChild(dropdown);
    document.querySelector('header').appendChild(userMenu);
    userMenu.onclick = () => userMenu.classList.toggle('active');
    carregarAgendamentos();
  } else {
    abrir.style.display = 'inline-block';
    boxAgendamentos.style.display = 'none';
  }
}

// AGENDA
const horarios = document.querySelectorAll('.horario-btn');
horarios.forEach(btn => btn.onclick = () => {
  horarios.forEach(b => b.classList.remove('selecionado'));
  btn.classList.add('selecionado');
});

document.querySelector('.form-agenda').addEventListener('submit', e => {
  e.preventDefault();
  if (!usuarioAtual) return mostrarErro('Faça login para agendar.');

  const data = document.getElementById('data').value;
  const nome = document.getElementById('nome').value.trim();
  const email = document.getElementById('email').value.trim();
  const telefone = document.getElementById('telefone').value.trim();
  const horarioSelecionado = document.querySelector('.horario-btn.selecionado');

  if (!data) return mostrarErro('Selecione uma data.');
  if (new Date(data) < new Date().setHours(0, 0, 0, 0)) return mostrarErro('Selecione uma data futura.');
  if (!horarioSelecionado) return mostrarErro('Escolha um horário.');
  if (!validarNome(nome)) return mostrarErro('Nome inválido.');
  if (!validarEmail(email)) return mostrarErro('Email inválido.');
  if (!validarTelefone(telefone)) return mostrarErro('Telefone inválido. Ex: (11) 98765-4321');

  const agendamento = { data, hora: horarioSelecionado.dataset.hora, nome, email, telefone };
  let users = JSON.parse(localStorage.getItem('usuarios') || '[]');
  const idx = users.findIndex(u => u.email === usuarioAtual.email);
  
  if (idx !== -1) {
    users[idx].agendamentos.push(agendamento);
    usuarioAtual = users[idx];
    localStorage.setItem('usuarios', JSON.stringify(users));
    localStorage.setItem('usuarioLogado', JSON.stringify(usuarioAtual));
  }

  alert('✅ Agendamento confirmado!');
  horarios.forEach(b => b.classList.remove('selecionado'));
  document.getElementById('data').value = '';
  document.getElementById('telefone').value = '';
  carregarAgendamentos();
});

function carregarAgendamentos() {
  if (!usuarioAtual?.agendamentos?.length) {
    boxAgendamentos.style.display = 'none';
    return;
  }
  boxAgendamentos.style.display = 'block';
  listaAgendamentos.innerHTML = '';
  usuarioAtual.agendamentos.forEach((a, i) => {
    const item = document.createElement('div');
    item.style.marginBottom = "10px";
    item.innerHTML = `📅 ${a.data} às ${a.hora} — ${a.nome} (${a.telefone})
      <button class="cancelar-btn" data-index="${i}">Cancelar</button>`;
    listaAgendamentos.appendChild(item);
  });

  document.querySelectorAll('.cancelar-btn').forEach(btn => {
    btn.onclick = () => {
      if (confirm('Deseja realmente cancelar este agendamento?')) {
        const idx = +btn.dataset.index;
        usuarioAtual.agendamentos.splice(idx, 1);
        let users = JSON.parse(localStorage.getItem('usuarios') || '[]');
        const uidx = users.findIndex(u => u.email === usuarioAtual.email);
        if (uidx !== -1) users[uidx] = usuarioAtual;
        localStorage.setItem('usuarios', JSON.stringify(users));
        localStorage.setItem('usuarioLogado', JSON.stringify(usuarioAtual));
        carregarAgendamentos();
      }
    };
  });
}

atualizarSaudacao();
