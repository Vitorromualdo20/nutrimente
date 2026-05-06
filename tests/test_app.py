import json
import sqlite3
import threading
import time
import unittest
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError

from backend import server


class NutrimenteApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_db_path = server.DB_PATH
        cls.temp_root = Path(__file__).resolve().parent / "_tmp"
        cls.temp_root.mkdir(exist_ok=True)
        cls.test_db = cls.temp_root / "test.db"
        if cls.test_db.exists():
            cls.test_db.unlink()
        server.DB_PATH = cls.test_db
        server.init_db()
        cls.httpd = server.ThreadingHTTPServer((server.HOST, 0), server.ApiHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=1)
        server.DB_PATH = cls.original_db_path

    def api_request(self, path, method="GET", data=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        body = None if data is None else json.dumps(data).encode("utf-8")
        request = urllib.request.Request(
            f"http://{server.HOST}:{self.port}/api{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request) as response:
                payload = response.read().decode()
                return response.status, json.loads(payload) if payload else {}
        except HTTPError as exc:
            payload = exc.read().decode()
            return exc.code, json.loads(payload) if payload else {}

    def unique_email(self, prefix):
        return f"{prefix}.{time.time_ns()}@example.com"

    def future_business_date(self, days_ahead=7):
        target = datetime.now() + timedelta(days=days_ahead)
        while target.weekday() > 4:
            target += timedelta(days=1)
        return target.strftime("%Y-%m-%d")

    def add_funds(self, token, amount_cents=50000):
        return self.api_request(
            "/wallet/add-funds",
            "POST",
            {"amountCents": amount_cents},
            token,
        )

    def test_wallet_topup_requires_confirmation_before_crediting_balance(self):
        email = self.unique_email("walletflow")
        self.api_request(
            "/register",
            "POST",
            {"nome": "Cliente Carteira", "email": email, "senha": "Senha123!", "tipo": "cliente"},
        )
        token = self.api_request("/login", "POST", {"email": email, "senha": "Senha123!"})[1]["token"]

        status, created = self.api_request(
            "/wallet/topups",
            "POST",
            {"amountCents": 20000, "paymentMethod": "pix"},
            token,
        )
        self.assertEqual(status, 201)
        self.assertEqual(created["topUp"]["status"], "pending")

        status, wallet_before = self.api_request("/wallet", token=token)
        self.assertEqual(status, 200)
        self.assertEqual(wallet_before["balanceCents"], 0)
        self.assertEqual(len(wallet_before["pendingTopUps"]), 1)
        self.assertTrue(wallet_before["topUpOptions"])

        status, confirmed = self.api_request(
            f"/wallet/topups/{created['topUp']['id']}/confirm",
            "POST",
            token=token,
        )
        self.assertEqual(status, 200)
        self.assertEqual(confirmed["topUp"]["status"], "paid")
        self.assertEqual(confirmed["wallet"]["balanceCents"], 20000)

    def test_admin_dashboard_returns_users_and_transactions(self):
        status, login = self.api_request(
            "/login",
            "POST",
            {"email": server.ADMIN_SEED_EMAIL, "senha": server.ADMIN_SEED_PASSWORD},
        )
        self.assertEqual(status, 200)
        token = login["token"]

        status, dashboard = self.api_request("/admin/dashboard", token=token)
        self.assertEqual(status, 200)
        self.assertIn("stats", dashboard)
        self.assertIn("users", dashboard)
        self.assertIn("transactions", dashboard)
        self.assertIn("security", dashboard)

    def test_register_login_and_schedule(self):
        email = self.unique_email("cliente")
        status, _ = self.api_request(
            "/register",
            "POST",
            {"nome": "Cliente Teste", "email": email, "senha": "Senha123!", "tipo": "cliente"},
        )
        self.assertEqual(status, 201)

        status, login = self.api_request(
            "/login",
            "POST",
            {"email": email, "senha": "Senha123!"},
        )
        self.assertEqual(status, 200)
        token = login["token"]

        status, professionals = self.api_request("/professionals")
        self.assertEqual(status, 200)
        professional_id = professionals["professionals"][0]["id"]

        status, wallet = self.add_funds(token)
        self.assertEqual(status, 201)
        self.assertIn("wallet", wallet)

        status, booking = self.api_request(
            "/appointments",
            "POST",
            {
                "professionalId": professional_id,
                "servico": "psicologia_nutricional",
                "modalidade": "online",
                "data": self.future_business_date(7),
                "hora": "08:00",
                "nome": "Cliente Teste",
                "email": email,
                "telefone": "11999990000",
                "observacoes": "teste automatizado",
            },
            token,
        )
        self.assertEqual(status, 201)
        self.assertIn("appointment", booking)
        self.assertIn("id", booking["appointment"])

        status, appointments = self.api_request("/appointments", token=token)
        self.assertEqual(status, 200)
        self.assertEqual(len(appointments["appointments"]), 1)
        self.assertGreater(appointments["appointments"][0]["priceCents"], 0)

        status, wallet_snapshot = self.api_request("/wallet", token=token)
        self.assertEqual(status, 200)
        self.assertLess(wallet_snapshot["balanceCents"], 50000)

    def test_schedule_requires_sufficient_balance(self):
        email = self.unique_email("saldo")
        self.api_request(
            "/register",
            "POST",
            {"nome": "Cliente Saldo", "email": email, "senha": "Senha123!", "tipo": "cliente"},
        )
        token = self.api_request("/login", "POST", {"email": email, "senha": "Senha123!"})[1]["token"]
        professionals = self.api_request("/professionals")[1]["professionals"]
        professional_id = next(
            item["id"]
            for item in professionals
            if item["conselho"] == "CFP" and item["registroProfissional"] == "06/12345"
        )

        status, payload = self.api_request(
            "/appointments",
            "POST",
            {
                "professionalId": professional_id,
                "servico": "psicologia_nutricional",
                "modalidade": "online",
                "data": self.future_business_date(7),
                "hora": "08:00",
                "nome": "Cliente Saldo",
                "email": email,
                "telefone": "11999998888",
                "observacoes": "sem saldo",
            },
            token,
        )
        self.assertEqual(status, 409)
        self.assertIn("Saldo insuficiente", payload["error"])
        self.assertIn("wallet", payload)

    def test_password_reset_flow(self):
        email = self.unique_email("reset")
        self.api_request(
            "/register",
            "POST",
            {"nome": "Reset Teste", "email": email, "senha": "Senha123!", "tipo": "cliente"},
        )

        status, reset = self.api_request(
            "/password-reset/request",
            "POST",
            {"email": email},
        )
        self.assertEqual(status, 200)
        self.assertIn("resetToken", reset)

        status, confirm = self.api_request(
            "/password-reset/confirm",
            "POST",
            {"token": reset["resetToken"], "senha": "NovaSenha123!"},
        )
        self.assertEqual(status, 200)
        self.assertIn("Senha redefinida", confirm["message"])

        status, old_login = self.api_request(
            "/login",
            "POST",
            {"email": email, "senha": "Senha123!"},
        )
        self.assertEqual(status, 401)

        status, new_login = self.api_request(
            "/login",
            "POST",
            {"email": email, "senha": "NovaSenha123!"},
        )
        self.assertEqual(status, 200)
        self.assertIn("token", new_login)

    def test_reschedule_flow(self):
        email = self.unique_email("reschedule")
        self.api_request(
            "/register",
            "POST",
            {"nome": "Cliente Reagenda", "email": email, "senha": "Senha123!", "tipo": "cliente"},
        )
        token = self.api_request("/login", "POST", {"email": email, "senha": "Senha123!"})[1]["token"]
        professional_id = self.api_request("/professionals")[1]["professionals"][0]["id"]
        self.add_funds(token)

        status, booking = self.api_request(
            "/appointments",
            "POST",
            {
                "professionalId": professional_id,
                "servico": "psicologia_nutricional",
                "modalidade": "online",
                "data": self.future_business_date(8),
                "hora": "09:00",
                "nome": "Cliente Reagenda",
                "email": email,
                "telefone": "11999991111",
                "observacoes": "teste reagendamento",
            },
            token,
        )
        self.assertEqual(status, 201)
        appointment_id = booking["appointment"]["id"]

        status, response = self.api_request(
            f"/appointments/{appointment_id}",
            "PUT",
            {"data": self.future_business_date(8), "hora": "10:00"},
            token,
        )
        self.assertEqual(status, 200)
        self.assertIn("reagendado", response["message"].lower())

        status, appointments = self.api_request("/appointments", token=token)
        self.assertEqual(status, 200)
        self.assertEqual(appointments["appointments"][0]["hora"], "10:00")

    def test_expired_session_is_rejected(self):
        email = self.unique_email("expired")
        self.api_request(
            "/register",
            "POST",
            {"nome": "Sessao Expirada", "email": email, "senha": "Senha123!", "tipo": "cliente"},
        )
        token = self.api_request("/login", "POST", {"email": email, "senha": "Senha123!"})[1]["token"]

        conn = sqlite3.connect(server.DB_PATH)
        conn.execute(
            "UPDATE sessions SET expires_at = ? WHERE token = ?",
            ((datetime.utcnow() - timedelta(minutes=1)).isoformat(timespec="seconds") + "Z", token),
        )
        conn.commit()
        conn.close()

        status, payload = self.api_request("/appointments", token=token)
        self.assertEqual(status, 401)
        self.assertIn("expirada", payload["error"].lower())

    def test_patient_cannot_cancel_inside_window(self):
        email = self.unique_email("window")
        self.api_request(
            "/register",
            "POST",
            {"nome": "Cliente Janela", "email": email, "senha": "Senha123!", "tipo": "cliente"},
        )
        token = self.api_request("/login", "POST", {"email": email, "senha": "Senha123!"})[1]["token"]
        professional_id = self.api_request("/professionals")[1]["professionals"][0]["id"]
        self.add_funds(token)

        status, booking = self.api_request(
            "/appointments",
            "POST",
            {
                "professionalId": professional_id,
                "servico": "psicologia_nutricional",
                "modalidade": "online",
                "data": self.future_business_date(9),
                "hora": "08:00",
                "nome": "Cliente Janela",
                "email": email,
                "telefone": "11999992222",
                "observacoes": "teste cancelamento",
            },
            token,
        )
        self.assertEqual(status, 201)
        appointment_id = booking["appointment"]["id"]

        conn = sqlite3.connect(server.DB_PATH)
        near = datetime.now() + timedelta(hours=11)
        conn.execute(
            "UPDATE appointments SET data = ?, hora = ? WHERE id = ?",
            (near.strftime("%Y-%m-%d"), near.strftime("%H:00"), appointment_id),
        )
        conn.commit()
        conn.close()

        status, payload = self.api_request(f"/appointments/{appointment_id}", "DELETE", token=token)
        self.assertEqual(status, 409)
        self.assertIn("12 horas", payload["error"])

    def test_automatic_reminders_are_generated_once(self):
        professional_email = self.unique_email("proreminder")
        status, _ = self.api_request(
            "/register",
            "POST",
            {
                "nome": "Mariana Profissional",
                "email": professional_email,
                "senha": "Senha123!",
                "tipo": "profissional",
                "conselho": "CFP",
                "registroProfissional": "06/12345",
            },
        )
        self.assertEqual(status, 201)
        professional_token = self.api_request(
            "/login",
            "POST",
            {"email": professional_email, "senha": "Senha123!"},
        )[1]["token"]
        self.assertTrue(professional_token)

        patient_email = self.unique_email("patientreminder")
        self.api_request(
            "/register",
            "POST",
            {"nome": "Paciente Reminder", "email": patient_email, "senha": "Senha123!", "tipo": "cliente"},
        )
        patient_token = self.api_request("/login", "POST", {"email": patient_email, "senha": "Senha123!"})[1]["token"]
        professionals = self.api_request("/professionals")[1]["professionals"]
        professional_id = next(
            item["id"]
            for item in professionals
            if item["conselho"] == "CFP" and item["registroProfissional"] == "06/12345"
        )
        self.add_funds(patient_token)

        status, booking = self.api_request(
            "/appointments",
            "POST",
            {
                "professionalId": professional_id,
                "servico": "psicologia_nutricional",
                "modalidade": "online",
                "data": self.future_business_date(10),
                "hora": "08:00",
                "nome": "Paciente Reminder",
                "email": patient_email,
                "telefone": "11999994444",
                "observacoes": "teste worker",
            },
            patient_token,
        )
        self.assertEqual(status, 201)
        appointment_id = booking["appointment"]["id"]

        reference = datetime.utcnow().replace(second=0, microsecond=0)
        reminder_target = reference + timedelta(minutes=server.REMINDER_LEAD_MINUTES)

        conn = server.get_db()
        conn.execute(
            "UPDATE appointments SET data = ?, hora = ? WHERE id = ?",
            (reminder_target.strftime("%Y-%m-%d"), reminder_target.strftime("%H:%M"), appointment_id),
        )
        conn.commit()
        created_once = server.enqueue_automatic_reminders(conn, now_utc=reference)
        created_twice = server.enqueue_automatic_reminders(conn, now_utc=reference)
        rows = conn.execute(
            "SELECT user_id, title FROM notifications WHERE external_key LIKE 'auto-reminder:%' ORDER BY user_id"
        ).fetchall()
        conn.close()

        self.assertEqual(created_once, 2)
        self.assertEqual(created_twice, 0)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["title"] == "Consulta em 1 hora" for row in rows))

    def test_cancellation_refunds_wallet_balance(self):
        email = self.unique_email("refund")
        self.api_request(
            "/register",
            "POST",
            {"nome": "Cliente Estorno", "email": email, "senha": "Senha123!", "tipo": "cliente"},
        )
        token = self.api_request("/login", "POST", {"email": email, "senha": "Senha123!"})[1]["token"]
        professional_id = self.api_request("/professionals")[1]["professionals"][0]["id"]

        status, deposit = self.add_funds(token, 30000)
        self.assertEqual(status, 201)
        initial_balance = deposit["wallet"]["balanceCents"]

        status, booking = self.api_request(
            "/appointments",
            "POST",
            {
                "professionalId": professional_id,
                "servico": "psicologia_nutricional",
                "modalidade": "online",
                "data": self.future_business_date(10),
                "hora": "09:00",
                "nome": "Cliente Estorno",
                "email": email,
                "telefone": "11999997777",
                "observacoes": "teste estorno",
            },
            token,
        )
        self.assertEqual(status, 201)
        appointment_id = booking["appointment"]["id"]
        charged_balance = booking["wallet"]["balanceCents"]
        self.assertLess(charged_balance, initial_balance)

        status, _ = self.api_request(f"/appointments/{appointment_id}", "DELETE", token=token)
        self.assertEqual(status, 200)

        status, wallet = self.api_request("/wallet", token=token)
        self.assertEqual(status, 200)
        self.assertEqual(wallet["balanceCents"], initial_balance)


if __name__ == "__main__":
    unittest.main()
