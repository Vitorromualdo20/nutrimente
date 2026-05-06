# Backend Nutrimente

API em Python + SQLite para autenticação, listagem de profissionais, gestão de agendamentos, prontuários, notificações e disponibilidade do profissional.

## Como executar

```powershell
python backend/server.py
```

Aplicação web: `http://127.0.0.1:8000`

Base da API: `http://127.0.0.1:8000/api`

## Endpoints principais

- `GET /api/health`
- `GET /api/professionals`
- `GET /api/availability?professionalId=1&date=2026-04-10`
- `POST /api/register`
- `POST /api/login`
- `POST /api/password-reset/request`
- `POST /api/password-reset/confirm`
- `POST /api/logout`
- `GET /api/me`
- `GET /api/appointments`
- `POST /api/appointments`
- `PUT /api/appointments/{id}`
- `DELETE /api/appointments/{id}`
- `GET /api/notifications`
- `POST /api/notifications/read-all`
- `GET /api/professional/dashboard`
- `PUT /api/professional/profile`
- `PUT /api/professional/availability`
- `PUT /api/records/{appointmentId}`

## Observações

- O banco `backend/nutrimente.db` é criado e atualizado automaticamente.
- Os profissionais padrão são semeados na inicialização da API.
- Cada profissional possui bloqueio próprio de horário por data.
- O frontend é servido pela própria API em `http://127.0.0.1:8000`.
- A aplicação inclui manifesto e service worker para instalação como PWA.
- Em ambiente local, a recuperação de senha devolve o código temporário na resposta para facilitar testes.
- Cancelamento e reagendamento pelo paciente exigem 12 horas de antecedência.
- Sessões autenticadas expiram após 8 horas de inatividade.
