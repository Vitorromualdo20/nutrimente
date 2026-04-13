import hashlib
import hmac
import json
import mimetypes
import secrets
import sqlite3
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR.parent
DB_PATH = BASE_DIR / "nutrimente.db"
HOST = "127.0.0.1"
PORT = 8000

AVAILABLE_SLOTS = ["08:00", "09:00", "10:00", "14:00", "15:00", "16:00"]
SERVICES = {
    "psicologia_nutricional": "Psicologia Nutricional",
    "psicoterapia_individual": "Psicoterapia Individual",
    "terapia_casal": "Terapia de Casal",
}
MODES = {"online": "Online", "presencial": "Presencial"}
PROFESSIONAL_SEED = [
    {
        "slug": "mariana-souza",
        "nome": "Dra. Mariana Souza",
        "titulo": "Psicologia Clínica e Nutricional",
        "conselho": "CFP",
        "registro_profissional": "06/12345",
        "bio": "Especialista em saúde mental integrada, ansiedade alimentar e autocuidado.",
        "especialidades": [
            "Ansiedade relacionada à alimentação",
            "Compulsão alimentar emocional",
            "Autoimagem e autoestima",
            "Psicoeducação nutricional",
        ],
        "abordagem": [
            "Terapia Cognitivo-Comportamental",
            "Intervenções focadas em metas",
            "Plano terapêutico individualizado",
        ],
        "experiencia": [
            "Atendimento clínico individual",
            "Projetos de educação em saúde",
            "Acompanhamento interdisciplinar",
        ],
        "frase": "A relação com a comida pode ser mais leve quando acolhimento e estratégia caminham juntos.",
    },
    {
        "slug": "lucas-fernandes",
        "nome": "Dr. Lucas Fernandes",
        "titulo": "Nutrição Comportamental",
        "conselho": "CFN",
        "registro_profissional": "12345/SP",
        "bio": "Nutricionista com foco em hábitos sustentáveis e rotina alimentar sem extremismos.",
        "especialidades": [
            "Nutrição comportamental",
            "Planejamento alimentar personalizado",
            "Reeducação alimentar",
            "Hábitos saudáveis para rotina corrida",
        ],
        "abordagem": [
            "Educação nutricional sem restrição extrema",
            "Metas progressivas com acompanhamento próximo",
            "Organização alimentar aplicável à vida real",
        ],
        "experiencia": [
            "Consultoria individual",
            "Programas de mudança de hábito",
            "Atuação em equipes multidisciplinares",
        ],
        "frase": "Nutrição de verdade precisa caber na rotina para gerar constância.",
    },
    {
        "slug": "fernanda-lima",
        "nome": "Dra. Fernanda Lima",
        "titulo": "Terapia Cognitivo-Comportamental",
        "conselho": "CFP",
        "registro_profissional": "06/54321",
        "bio": "Psicóloga especialista em gestão emocional, clareza mental e fortalecimento da autoestima.",
        "especialidades": [
            "Gestão emocional",
            "Estresse e sobrecarga",
            "Autoconhecimento",
            "Fortalecimento da autoestima",
        ],
        "abordagem": [
            "Terapia Cognitivo-Comportamental",
            "Estratégias práticas para o dia a dia",
            "Acompanhamento com foco em progresso contínuo",
        ],
        "experiencia": [
            "Atendimento individual adulto",
            "Projetos de prevenção em saúde mental",
            "Reestruturação emocional",
        ],
        "frase": "Compreender padrões emocionais abre espaço para escolhas mais conscientes.",
    },
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return f"{salt}${derived}"


def verify_password(password, stored_hash):
    try:
        salt, expected = stored_hash.split("$", 1)
    except ValueError:
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return hmac.compare_digest(candidate, expected)


def user_payload(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "tipo": row["tipo"],
        "conselho": row["conselho"],
        "registroProfissional": row["registro_profissional"],
    }


def professional_payload(row):
    return {
        "id": row["id"],
        "slug": row["slug"],
        "nome": row["nome"],
        "titulo": row["titulo"],
        "conselho": row["conselho"],
        "registroProfissional": row["registro_profissional"],
        "bio": row["bio"],
        "especialidades": json.loads(row["especialidades"]),
        "abordagem": json.loads(row["abordagem"]),
        "experiencia": json.loads(row["experiencia"]),
        "frase": row["frase"],
    }


def appointment_payload(row):
    return {
        "id": row["id"],
        "data": row["data"],
        "hora": row["hora"],
        "nome": row["nome"],
        "email": row["email"],
        "telefone": row["telefone"],
        "servico": row["servico"],
        "modalidade": row["modalidade"],
        "observacoes": row["observacoes"] or "",
        "professionalId": row["professional_id"],
        "professionalSlug": row["professional_slug"],
        "professionalName": row["professional_nome"],
        "professionalTitle": row["professional_titulo"],
        "roomName": row["room_name"],
    }


def ensure_column(conn, table_name, column_name, statement):
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})")}
    if column_name not in columns:
        conn.execute(statement)


def seed_professionals(conn):
    for item in PROFESSIONAL_SEED:
        conn.execute(
            """
            INSERT INTO professionals (
                slug, nome, titulo, conselho, registro_profissional, bio,
                especialidades, abordagem, experiencia, frase
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                nome = excluded.nome,
                titulo = excluded.titulo,
                conselho = excluded.conselho,
                registro_profissional = excluded.registro_profissional,
                bio = excluded.bio,
                especialidades = excluded.especialidades,
                abordagem = excluded.abordagem,
                experiencia = excluded.experiencia,
                frase = excluded.frase
            """,
            (
                item["slug"],
                item["nome"],
                item["titulo"],
                item["conselho"],
                item["registro_profissional"],
                item["bio"],
                json.dumps(item["especialidades"], ensure_ascii=False),
                json.dumps(item["abordagem"], ensure_ascii=False),
                json.dumps(item["experiencia"], ensure_ascii=False),
                item["frase"],
            ),
        )


def init_db():
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                tipo TEXT NOT NULL DEFAULT 'cliente',
                conselho TEXT,
                registro_profissional TEXT,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS professionals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                nome TEXT NOT NULL,
                titulo TEXT NOT NULL,
                conselho TEXT NOT NULL,
                registro_profissional TEXT NOT NULL,
                bio TEXT NOT NULL,
                especialidades TEXT NOT NULL,
                abordagem TEXT NOT NULL,
                experiencia TEXT NOT NULL,
                frase TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                professional_id INTEGER NOT NULL,
                data TEXT NOT NULL,
                hora TEXT NOT NULL,
                nome TEXT NOT NULL,
                email TEXT NOT NULL,
                telefone TEXT NOT NULL,
                servico TEXT NOT NULL DEFAULT 'psicologia_nutricional',
                modalidade TEXT NOT NULL DEFAULT 'online',
                observacoes TEXT,
                room_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(professional_id, data, hora),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(professional_id) REFERENCES professionals(id) ON DELETE CASCADE
            );
            """
        )

        ensure_column(
            conn,
            "users",
            "tipo",
            "ALTER TABLE users ADD COLUMN tipo TEXT NOT NULL DEFAULT 'cliente'",
        )
        ensure_column(
            conn,
            "users",
            "conselho",
            "ALTER TABLE users ADD COLUMN conselho TEXT",
        )
        ensure_column(
            conn,
            "users",
            "registro_profissional",
            "ALTER TABLE users ADD COLUMN registro_profissional TEXT",
        )
        ensure_column(
            conn,
            "appointments",
            "professional_id",
            "ALTER TABLE appointments ADD COLUMN professional_id INTEGER REFERENCES professionals(id)",
        )
        ensure_column(
            conn,
            "appointments",
            "servico",
            "ALTER TABLE appointments ADD COLUMN servico TEXT NOT NULL DEFAULT 'psicologia_nutricional'",
        )
        ensure_column(
            conn,
            "appointments",
            "modalidade",
            "ALTER TABLE appointments ADD COLUMN modalidade TEXT NOT NULL DEFAULT 'online'",
        )
        ensure_column(
            conn,
            "appointments",
            "observacoes",
            "ALTER TABLE appointments ADD COLUMN observacoes TEXT",
        )
        ensure_column(
            conn,
            "appointments",
            "room_name",
            "ALTER TABLE appointments ADD COLUMN room_name TEXT NOT NULL DEFAULT ''",
        )

        seed_professionals(conn)
        default_professional = conn.execute(
            "SELECT id FROM professionals ORDER BY id LIMIT 1"
        ).fetchone()
        if default_professional:
            conn.execute(
                """
                UPDATE appointments
                SET professional_id = COALESCE(professional_id, ?),
                    room_name = CASE
                        WHEN room_name IS NULL OR room_name = ''
                        THEN 'nutrimente-consulta'
                        ELSE room_name
                    END
                WHERE professional_id IS NULL OR professional_id = 0 OR room_name IS NULL OR room_name = ''
                """,
                (default_professional["id"],),
            )


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "NutrimenteAPI/2.0"

    def log_message(self, fmt, *args):
        return

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            return self.json_response(200, {"status": "ok"})

        if parsed.path == "/api/professionals":
            return self.handle_list_professionals()

        if parsed.path == "/api/availability":
            return self.handle_availability(parsed.query)

        if parsed.path == "/api/me":
            user = self.require_user()
            if not user:
                return
            return self.json_response(200, {"user": user_payload(user)})

        if parsed.path == "/api/appointments":
            user = self.require_user()
            if not user:
                return
            return self.handle_list_appointments(user)

        if parsed.path.startswith("/api/"):
            return self.json_response(404, {"error": "Rota não encontrada."})

        return self.serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/register":
            data = self.read_json()
            if data is None:
                return
            return self.handle_register(data)

        if parsed.path == "/api/login":
            data = self.read_json()
            if data is None:
                return
            return self.handle_login(data)

        if parsed.path == "/api/logout":
            token = self.get_token()
            if token:
                with get_db() as conn:
                    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return self.json_response(200, {"message": "Sessão encerrada."})

        if parsed.path == "/api/appointments":
            user = self.require_user()
            if not user:
                return
            data = self.read_json()
            if data is None:
                return
            return self.handle_create_appointment(user, data)

        return self.json_response(404, {"error": "Rota não encontrada."})

    def do_DELETE(self):
        parsed = urlparse(self.path)

        if not parsed.path.startswith("/api/appointments/"):
            return self.json_response(404, {"error": "Rota não encontrada."})

        user = self.require_user()
        if not user:
            return

        appointment_id = parsed.path.rsplit("/", 1)[-1]
        if not appointment_id.isdigit():
            return self.json_response(400, {"error": "Agendamento inválido."})

        with get_db() as conn:
            deleted = conn.execute(
                "DELETE FROM appointments WHERE id = ? AND user_id = ?",
                (int(appointment_id), user["id"]),
            ).rowcount

        if not deleted:
            return self.json_response(404, {"error": "Agendamento não encontrado."})

        return self.json_response(200, {"message": "Agendamento cancelado."})

    def read_json(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0

        raw = self.rfile.read(content_length) if content_length else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.json_response(400, {"error": "JSON inválido."})
            return None

    def get_token(self):
        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        return auth_header.split(" ", 1)[1].strip()

    def require_user(self):
        token = self.get_token()
        if not token:
            self.json_response(401, {"error": "Sessão não autenticada."})
            return None

        with get_db() as conn:
            row = conn.execute(
                """
                SELECT users.id, users.nome, users.email, users.tipo, users.conselho, users.registro_profissional
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token = ?
                """,
                (token,),
            ).fetchone()

        if row is None:
            self.json_response(401, {"error": "Sessão inválida ou expirada."})
            return None

        return row

    def handle_list_professionals(self):
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM professionals ORDER BY nome"
            ).fetchall()

        return self.json_response(
            200,
            {
                "professionals": [professional_payload(row) for row in rows],
                "services": SERVICES,
                "modes": MODES,
                "slots": AVAILABLE_SLOTS,
            },
        )

    def handle_availability(self, query_string):
        query = parse_qs(query_string)
        date_value = (query.get("date") or [""])[0].strip()
        professional_id = (query.get("professionalId") or [""])[0].strip()

        if not date_value:
            return self.json_response(400, {"error": "Informe a data desejada."})
        if not professional_id.isdigit():
            return self.json_response(
                400,
                {"error": "Informe um profissional válido para consultar horários."},
            )

        try:
            datetime.strptime(date_value, "%Y-%m-%d")
        except ValueError:
            return self.json_response(400, {"error": "Data inválida."})

        with get_db() as conn:
            booked_rows = conn.execute(
                """
                SELECT hora
                FROM appointments
                WHERE professional_id = ? AND data = ?
                """,
                (int(professional_id), date_value),
            ).fetchall()

        booked = {row["hora"] for row in booked_rows}
        slots = [
            {"hora": slot, "disponivel": slot not in booked}
            for slot in AVAILABLE_SLOTS
        ]
        return self.json_response(200, {"date": date_value, "slots": slots})

    def handle_register(self, data):
        nome = (data.get("nome") or "").strip()
        email = (data.get("email") or "").strip().lower()
        senha = data.get("senha") or ""
        tipo = (data.get("tipo") or "cliente").strip().lower()
        conselho = (data.get("conselho") or "").strip().upper() or None
        registro_profissional = (
            (data.get("registroProfissional") or data.get("registro_profissional") or "")
            .strip()
            .upper()
            or None
        )

        if len(nome) < 3:
            return self.json_response(400, {"error": "Nome inválido."})
        if "@" not in email or "." not in email:
            return self.json_response(400, {"error": "Email inválido."})
        if len(senha) < 8:
            return self.json_response(
                400,
                {"error": "A senha deve ter pelo menos 8 caracteres."},
            )
        if tipo not in {"cliente", "profissional"}:
            return self.json_response(400, {"error": "Tipo de utilizador inválido."})
        if tipo == "profissional" and (not conselho or not registro_profissional):
            return self.json_response(
                400,
                {"error": "Conselho e registo profissional são obrigatórios."},
            )

        try:
            with get_db() as conn:
                conn.execute(
                    """
                    INSERT INTO users (
                        nome, email, tipo, conselho, registro_profissional, password_hash, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        nome,
                        email,
                        tipo,
                        conselho,
                        registro_profissional,
                        hash_password(senha),
                        now_iso(),
                    ),
                )
        except sqlite3.IntegrityError:
            return self.json_response(409, {"error": "Email já cadastrado."})

        return self.json_response(201, {"message": "Cadastro realizado com sucesso."})

    def handle_login(self, data):
        email = (data.get("email") or "").strip().lower()
        senha = data.get("senha") or ""

        with get_db() as conn:
            user = conn.execute(
                """
                SELECT id, nome, email, tipo, conselho, registro_profissional, password_hash
                FROM users
                WHERE email = ?
                """,
                (email,),
            ).fetchone()

            if user is None or not verify_password(senha, user["password_hash"]):
                return self.json_response(401, {"error": "Credenciais inválidas."})

            token = secrets.token_urlsafe(32)
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                (token, user["id"], now_iso()),
            )

        return self.json_response(
            200,
            {"token": token, "user": user_payload(user), "message": "Login realizado."},
        )

    def handle_list_appointments(self, user):
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT
                    appointments.*,
                    professionals.slug AS professional_slug,
                    professionals.nome AS professional_nome,
                    professionals.titulo AS professional_titulo
                FROM appointments
                JOIN professionals ON professionals.id = appointments.professional_id
                WHERE appointments.user_id = ?
                ORDER BY appointments.data, appointments.hora
                """,
                (user["id"],),
            ).fetchall()

        return self.json_response(
            200,
            {"appointments": [appointment_payload(row) for row in rows]},
        )

    def handle_create_appointment(self, user, data):
        appointment_date = (data.get("data") or "").strip()
        appointment_time = (data.get("hora") or "").strip()
        nome = (data.get("nome") or "").strip()
        email = (data.get("email") or "").strip().lower()
        telefone = (data.get("telefone") or "").strip()
        servico = (data.get("servico") or "psicologia_nutricional").strip()
        modalidade = (data.get("modalidade") or "online").strip()
        observacoes = (data.get("observacoes") or "").strip()
        professional_id = str(data.get("professionalId") or "").strip()

        if not appointment_date or not appointment_time:
            return self.json_response(400, {"error": "Data e horário são obrigatórios."})
        if len(nome) < 3:
            return self.json_response(400, {"error": "Nome inválido."})
        if "@" not in email or "." not in email:
            return self.json_response(400, {"error": "Email inválido."})
        if len(telefone) < 8:
            return self.json_response(400, {"error": "Telefone inválido."})
        if servico not in SERVICES:
            return self.json_response(400, {"error": "Serviço inválido."})
        if modalidade not in MODES:
            return self.json_response(400, {"error": "Modalidade inválida."})
        if appointment_time not in AVAILABLE_SLOTS:
            return self.json_response(400, {"error": "Horário inválido."})
        if not professional_id.isdigit():
            return self.json_response(400, {"error": "Profissional inválido."})

        try:
            appointment_dt = datetime.strptime(
                f"{appointment_date} {appointment_time}",
                "%Y-%m-%d %H:%M",
            )
        except ValueError:
            return self.json_response(400, {"error": "Data ou horário inválidos."})

        if appointment_dt.date() < datetime.now().date():
            return self.json_response(400, {"error": "Selecione uma data futura."})

        room_name = self.build_room_name(nome, appointment_date, appointment_time)

        try:
            with get_db() as conn:
                professional = conn.execute(
                    "SELECT id, slug, nome, titulo FROM professionals WHERE id = ?",
                    (int(professional_id),),
                ).fetchone()
                if professional is None:
                    return self.json_response(404, {"error": "Profissional não encontrado."})

                cursor = conn.execute(
                    """
                    INSERT INTO appointments (
                        user_id, professional_id, data, hora, nome, email, telefone,
                        servico, modalidade, observacoes, room_name, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user["id"],
                        professional["id"],
                        appointment_date,
                        appointment_time,
                        nome,
                        email,
                        telefone,
                        servico,
                        modalidade,
                        observacoes,
                        room_name,
                        now_iso(),
                    ),
                )
        except sqlite3.IntegrityError:
            return self.json_response(
                409,
                {"error": "Esse horário já foi reservado para o profissional selecionado."},
            )

        return self.json_response(
            201,
            {
                "message": "Agendamento confirmado.",
                "appointment": {
                    "id": cursor.lastrowid,
                    "data": appointment_date,
                    "hora": appointment_time,
                    "nome": nome,
                    "email": email,
                    "telefone": telefone,
                    "servico": servico,
                    "modalidade": modalidade,
                    "observacoes": observacoes,
                    "professionalId": professional["id"],
                    "professionalSlug": professional["slug"],
                    "professionalName": professional["nome"],
                    "professionalTitle": professional["titulo"],
                    "roomName": room_name,
                },
            },
        )

    def build_room_name(self, nome, data, hora):
        tokens = f"{nome}-{data}-{hora}".lower()
        safe = "".join(
            char if char.isalnum() else "-"
            for char in tokens
        ).strip("-")
        return f"nutrimente-{safe[:48] or 'consulta'}"

    def serve_static(self, path):
        normalized = "/" if path in {"", "/"} else path
        relative_path = "index.html" if normalized == "/" else normalized.lstrip("/")
        file_path = (APP_DIR / relative_path).resolve()

        if APP_DIR not in file_path.parents and file_path != APP_DIR:
            return self.json_response(403, {"error": "Acesso negado."})
        if not file_path.exists() or not file_path.is_file():
            return self.json_response(404, {"error": "Página não encontrada."})

        content_type, _ = mimetypes.guess_type(file_path.name)
        content_type = content_type or "application/octet-stream"
        body = file_path.read_bytes()

        self.send_response(200)
        if content_type.startswith("text/") or content_type in {
            "application/javascript",
            "application/json",
        }:
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        else:
            self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def json_response(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run():
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), ApiHandler)
    print(f"Nutrimente API ativa em http://{HOST}:{PORT}/api")
    server.serve_forever()


if __name__ == "__main__":
    run()
