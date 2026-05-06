# NutriMente

Software web instalável como app (PWA) para apresentação da clínica, cadastro de utilizadores, escolha de profissionais, agendamento de consultas, notificações e prontuários.

## Executar

1. Inicie o servidor:

```powershell
python backend/server.py
```

2. Abra [http://127.0.0.1:8000](http://127.0.0.1:8000) no navegador.

Evite abrir o `index.html` diretamente por `file:///...`, porque o fluxo de cadastro e login depende do servidor ativo.

## Funcionalidades

- Cadastro e login de cliente ou profissional
- Recuperação de senha por código temporário gerado na tela de acesso
- Listagem de profissionais com páginas de perfil
- Agendamento por serviço, modalidade, data e horário
- Cancelamento e reagendamento pelo paciente com antecedência mínima de 12 horas
- Sessão expira automaticamente após período de inatividade
- Painel com agendamentos da conta autenticada
- Central de notificações e lembretes na interface
- Painel do profissional para editar perfil e gerir horários disponíveis
- Prontuários/evolução por consulta dentro do painel profissional
- Instalação como aplicativo via navegador (PWA)
- Entrada em sala online privada via Jitsi

## Testes

```powershell
python -m unittest tests.test_app -v
```

## Recuperação de senha

- Na tela de login, use `Esqueci minha senha`
- Informe o email da conta para gerar um código temporário
- Em ambiente local, o código é mostrado na interface para facilitar os testes
- Depois informe o código e a nova senha
