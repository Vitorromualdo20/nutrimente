import hashlib
import hmac
import json
import mimetypes
import re
import secrets
import sqlite3
import threading
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR.parent
DB_PATH = BASE_DIR / "nutrimente.db"
HOST = "127.0.0.1"
PORT = 8000
DEBUG = True  # Defina como False em produção — oculta tokens de reset e restringe CORS
ALLOWED_ORIGIN = f"http://{HOST}:{PORT}"  # Substitua pelo domínio real em produção
CANCELLATION_WINDOW_HOURS = 12
SESSION_IDLE_HOURS = 8
REMINDER_LEAD_MINUTES = 60
REMINDER_TOLERANCE_MINUTES = 2
REMINDER_WORKER_INTERVAL_SECONDS = 60
TOP_UP_OPTIONS_CENTS = [5000, 10000, 20000, 50000]
WALLET_PAYMENT_METHODS = {
    "card": "Cartão de crédito",
    "pix": "Pix",
}

AVAILABLE_SLOTS = ["08:00", "09:00", "10:00", "14:00", "15:00", "16:00"]
WEEKDAYS = {
    0: "Segunda",
    1: "Terça",
    2: "Quarta",
    3: "Quinta",
    4: "Sexta",
    5: "Sábado",
    6: "Domingo",
}
SERVICES = {
    "psicologia_nutricional": "Psicologia Nutricional",
    "psicoterapia_individual": "Psicoterapia Individual",
    "terapia_casal": "Terapia de Casal",
}
MODES = {"online": "Online", "presencial": "Presencial"}
SERVICE_PRICES_CENTS = {
    "psicologia_nutricional": 18000,
    "psicoterapia_individual": 16000,
    "terapia_casal": 22000,
}
MODE_PRICE_ADJUSTMENTS_CENTS = {"online": 0, "presencial": 2000}
MIN_WALLET_TOP_UP_CENTS = 1000
MAX_WALLET_TOP_UP_CENTS = 500000
ADMIN_SEED_EMAIL = "admin@nutrimente.com.br"
ADMIN_SEED_PASSWORD = "Admin123!"
PROFESSIONAL_SEED = [
    {
        "slug": "mariana-souza",
        "nome": "Dra. Mariana Souza",
        "titulo": "Psicologia Clínica e Nutricional",
        "conselho": "CFP",
        "registro_profissional": "06/12345",
        "bio": "Psicóloga com atuação clínica em sofrimento psíquico relacionado à alimentação, ansiedade, imagem corporal e processos de autocuidado. Realiza acompanhamento individual com foco em avaliação, formulação clínica e plano terapêutico personalizado.",
        "especialidades": [
            "Ansiedade associada ao comportamento alimentar",
            "Compulsão alimentar e regulação emocional",
            "Imagem corporal, autoestima e autoaceitação",
            "Psicoeducação em saúde e hábitos alimentares",
        ],
        "abordagem": [
            "Terapia Cognitivo-Comportamental com objetivos terapêuticos definidos",
            "Intervenções estruturadas para manejo de sintomas e prevenção de recaídas",
            "Construção de plano terapêutico individualizado e acompanhamento interdisciplinar",
        ],
        "experiencia": [
            "Atendimento clínico individual em contexto ambulatorial",
            "Projetos de promoção de saúde e educação em hábitos de vida",
            "Atuação integrada com profissionais de nutrição e saúde mental",
        ],
        "frase": "O cuidado clínico da relação com a alimentação exige acolhimento, técnica e continuidade terapêutica.",
    },
    {
        "slug": "lucas-fernandes",
        "nome": "Dr. Lucas Fernandes",
        "titulo": "Nutrição Comportamental",
        "conselho": "CFN",
        "registro_profissional": "12345/SP",
        "bio": "Nutricionista com enfoque em nutrição comportamental, adesão terapêutica e organização da rotina alimentar. Atua no desenvolvimento de estratégias sustentáveis para melhorar a relação com a comida sem prescrições rígidas ou extremismos.",
        "especialidades": [
            "Nutrição comportamental e alimentação consciente",
            "Planejamento alimentar individualizado",
            "Reeducação alimentar com foco em adesão",
            "Estruturação de rotina alimentar para diferentes contextos de vida",
        ],
        "abordagem": [
            "Educação nutricional baseada em contexto, rotina e comportamento",
            "Metas progressivas com monitoramento clínico de evolução",
            "Protocolos aplicáveis à vida real, com foco em autonomia alimentar",
        ],
        "experiencia": [
            "Atendimento nutricional individual para adultos",
            "Programas clínicos de mudança de hábito e adesão alimentar",
            "Atuação em equipes multidisciplinares de cuidado integrado",
        ],
        "frase": "Intervenções nutricionais consistentes precisam ser clinicamente úteis e viáveis na rotina do paciente.",
    },
    {
        "slug": "fernanda-lima",
        "nome": "Dra. Fernanda Lima",
        "titulo": "Terapia Cognitivo-Comportamental",
        "conselho": "CFP",
        "registro_profissional": "06/54321",
        "bio": "Psicóloga clínica com ênfase em Terapia Cognitivo-Comportamental para manejo de estresse, sobrecarga emocional, padrões cognitivos disfuncionais e fortalecimento de recursos internos.",
        "especialidades": [
            "Regulação emocional e manejo de sintomas ansiosos",
            "Estresse, sobrecarga psíquica e exaustão",
            "Autoconhecimento e reestruturação cognitiva",
            "Fortalecimento de autoestima e repertório de enfrentamento",
        ],
        "abordagem": [
            "Terapia Cognitivo-Comportamental baseada em metas terapêuticas",
            "Estratégias práticas para manejo diário de pensamentos, emoções e comportamentos",
            "Acompanhamento clínico com monitoramento de progresso e prevenção de recaídas",
        ],
        "experiencia": [
            "Atendimento psicológico individual para adultos",
            "Projetos de prevenção e promoção em saúde mental",
            "Intervenções focadas em reestruturação emocional e funcionalidade",
        ],
        "frase": "Compreender padrões emocionais é parte essencial da construção de escolhas mais conscientes e estáveis.",
    },
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def future_iso(hours=0, minutes=0):
    return (datetime.utcnow() + timedelta(hours=hours, minutes=minutes)).isoformat(timespec="seconds") + "Z"


def parse_utc_iso(value):
    return datetime.fromisoformat(str(value).replace("Z", ""))


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


def is_valid_professional_document(council, document_id):
    value = (document_id or "").strip().upper().replace(" ", "")
    patterns = {
        "CFP": r"^\d{2}/\d{4,6}(?:-\d)?$",
        "CFN": r"^\d{4,6}(?:/[A-Z]{2})?$",
    }
    pattern = patterns.get((council or "").strip().upper())
    return bool(pattern and re.fullmatch(pattern, value))


def slugify(value):
    normalized = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower())
    return normalized.strip("-") or f"usuario-{secrets.token_hex(3)}"


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email):
    return bool(_EMAIL_RE.fullmatch(email or ""))


def user_payload(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "tipo": row["tipo"],
        "conselho": row["conselho"],
        "registroProfissional": row["registro_profissional"],
        "professionalId": row["professional_id"],
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
        "userId": row["user_id"],
    }


def notification_payload(row):
    return {
        "id": row["id"],
        "kind": row["kind"],
        "title": row["title"],
        "message": row["message"],
        "isRead": bool(row["is_read"]),
        "createdAt": row["created_at"],
    }


def availability_payload(rows):
    matrix = {str(day): [] for day in WEEKDAYS}
    for row in rows:
        matrix[str(row["weekday"])].append(row["slot"])
    for key in matrix:
        matrix[key] = sorted(matrix[key])
    return matrix


def create_notification(conn, user_id, kind, title, message, external_key=None):
    try:
        conn.execute(
            """
            INSERT INTO notifications (user_id, kind, title, message, external_key, is_read, created_at)
            VALUES (?, ?, ?, ?, ?, 0, ?)
            """,
            (user_id, kind, title, message, external_key, now_iso()),
        )
    except sqlite3.IntegrityError:
        return


def should_send_reminder(
    appointment_dt,
    now_utc=None,
    lead_minutes=REMINDER_LEAD_MINUTES,
    tolerance_minutes=REMINDER_TOLERANCE_MINUTES,
):
    reference = now_utc or datetime.utcnow()
    reminder_at = appointment_dt - timedelta(minutes=lead_minutes)
    reminder_until = reminder_at + timedelta(minutes=tolerance_minutes)
    return reminder_at <= reference < reminder_until


def enqueue_automatic_reminders(conn, now_utc=None):
    reference = now_utc or datetime.utcnow()
    rows = conn.execute(
        """
        SELECT
            appointments.id,
            appointments.data,
            appointments.hora,
            appointments.nome AS patient_name,
            appointments.user_id AS patient_user_id,
            professionals.nome AS professional_name,
            professionals.user_id AS professional_user_id
        FROM appointments
        JOIN professionals ON professionals.id = appointments.professional_id
        WHERE appointments.data >= ?
        """,
        ((reference - timedelta(days=1)).strftime("%Y-%m-%d"),),
    ).fetchall()

    created = 0
    for row in rows:
        appointment_dt = appointment_datetime(row["data"], row["hora"])
        if not should_send_reminder(appointment_dt, now_utc=reference):
            continue

        before_changes = conn.total_changes
        create_notification(
            conn,
            row["patient_user_id"],
            "info",
            "Consulta em 1 hora",
            f"Lembrete: sua consulta com {row['professional_name']} começa às {row['hora']}.",
            external_key=f"auto-reminder:{REMINDER_LEAD_MINUTES}:{row['id']}:{row['patient_user_id']}",
        )
        if conn.total_changes > before_changes:
            created += 1

        if row["professional_user_id"]:
            before_changes = conn.total_changes
            create_notification(
                conn,
                row["professional_user_id"],
                "info",
                "Consulta em 1 hora",
                f"Lembrete: sua consulta com {row['patient_name']} começa às {row['hora']}.",
                external_key=f"auto-reminder:{REMINDER_LEAD_MINUTES}:{row['id']}:{row['professional_user_id']}",
            )
            if conn.total_changes > before_changes:
                created += 1

    return created


def reminder_worker_loop(stop_event, interval_seconds=REMINDER_WORKER_INTERVAL_SECONDS):
    while not stop_event.is_set():
        try:
            with get_db() as conn:
                enqueue_automatic_reminders(conn)
        except sqlite3.Error as exc:
            print(f"Worker de lembretes: falha ao gerar notificações ({exc}).")

        stop_event.wait(interval_seconds)


def generate_reset_token():
    return secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8].upper()


def appointment_datetime(date_value, time_value):
    return datetime.strptime(f"{date_value} {time_value}", "%Y-%m-%d %H:%M")


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
        "priceCents": row["price_cents"],
        "priceFormatted": format_brl(row["price_cents"]),
    }


def format_brl(amount_cents):
    value = (int(amount_cents or 0)) / 100
    formatted = f"{value:,.2f}"
    return f"R$ {formatted}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_money_to_cents(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value * 100))

    text = str(value).strip()
    if not text:
        return None

    text = text.replace("R$", "").replace(" ", "")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")

    try:
        amount = Decimal(text).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None

    return int(amount * 100)


def calculate_appointment_price_cents(servico, modalidade):
    return SERVICE_PRICES_CENTS.get(servico, 0) + MODE_PRICE_ADJUSTMENTS_CENTS.get(modalidade, 0)


def wallet_balance_cents(conn, user_id):
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_cents), 0) AS balance FROM wallet_transactions WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return int(row["balance"] or 0)


def wallet_transaction_payload(row):
    amount_cents = int(row["amount_cents"] or 0)
    return {
        "id": row["id"],
        "kind": row["kind"],
        "amountCents": amount_cents,
        "amountFormatted": format_brl(abs(amount_cents)),
        "signedAmountFormatted": format_brl(amount_cents),
        "direction": "credit" if amount_cents >= 0 else "debit",
        "description": row["description"],
        "appointmentId": row["appointment_id"],
        "topUpId": row["topup_id"],
        "receiptCode": f"NTM-TX-{int(row['id']):06d}",
        "createdAt": row["created_at"],
    }


def wallet_topup_payload(row):
    amount_cents = int(row["amount_cents"] or 0)
    return {
        "id": row["id"],
        "amountCents": amount_cents,
        "amountFormatted": format_brl(amount_cents),
        "paymentMethod": row["payment_method"],
        "paymentMethodLabel": WALLET_PAYMENT_METHODS.get(row["payment_method"], row["payment_method"]),
        "gatewayProvider": row["gateway_provider"],
        "status": row["status"],
        "externalReference": row["external_reference"],
        "createdAt": row["created_at"],
        "confirmedAt": row["confirmed_at"],
        "expiresAt": row["expires_at"],
        "isPending": row["status"] == "pending",
    }


def wallet_payload(conn, user_id, limit=8):
    balance_cents = wallet_balance_cents(conn, user_id)
    rows = conn.execute(
        """
        SELECT id, kind, amount_cents, description, appointment_id, topup_id, created_at
        FROM wallet_transactions
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, int(limit)),
    ).fetchall()
    topups = conn.execute(
        """
        SELECT id, amount_cents, payment_method, gateway_provider, status, external_reference, created_at, confirmed_at, expires_at
        FROM wallet_topups
        WHERE user_id = ? AND status = 'pending'
        ORDER BY id DESC
        LIMIT 3
        """,
        (user_id,),
    ).fetchall()
    return {
        "balanceCents": balance_cents,
        "balanceFormatted": format_brl(balance_cents),
        "transactions": [wallet_transaction_payload(row) for row in rows],
        "pendingTopUps": [wallet_topup_payload(row) for row in topups],
        "topUpOptions": [
            {"amountCents": amount_cents, "amountFormatted": format_brl(amount_cents)}
            for amount_cents in TOP_UP_OPTIONS_CENTS
        ],
        "paymentMethods": WALLET_PAYMENT_METHODS,
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


def seed_availability(conn):
    professionals = conn.execute("SELECT id FROM professionals").fetchall()
    for professional in professionals:
        total = conn.execute(
            "SELECT COUNT(*) AS total FROM professional_availability WHERE professional_id = ?",
            (professional["id"],),
        ).fetchone()["total"]
        if total:
            continue
        for weekday in range(5):
            for slot in AVAILABLE_SLOTS:
                conn.execute(
                    """
                    INSERT INTO professional_availability (professional_id, weekday, slot)
                    VALUES (?, ?, ?)
                    """,
                    (professional["id"], weekday, slot),
                )


def seed_admin(conn):
    existing = conn.execute(
        "SELECT id FROM users WHERE email = ?",
        (ADMIN_SEED_EMAIL,),
    ).fetchone()
    if existing:
        return
    conn.execute(
        """
        INSERT INTO users (
            nome, email, tipo, conselho, registro_profissional, password_hash, created_at
        )
        VALUES (?, ?, 'admin', NULL, NULL, ?, ?)
        """,
        ("Administrador NutriMente", ADMIN_SEED_EMAIL, hash_password(ADMIN_SEED_PASSWORD), now_iso()),
    )


def create_wallet_topup(conn, user_id, amount_cents, payment_method, gateway_provider="simulado"):
    external_reference = f"topup-{user_id}-{secrets.token_hex(6)}"
    expires_at = future_iso(minutes=30)
    cursor = conn.execute(
        """
        INSERT INTO wallet_topups (
            user_id, amount_cents, payment_method, gateway_provider, status, external_reference, created_at, expires_at
        )
        VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
        """,
        (user_id, amount_cents, payment_method, gateway_provider, external_reference, now_iso(), expires_at),
    )
    return conn.execute(
        """
        SELECT id, amount_cents, payment_method, gateway_provider, status, external_reference, created_at, confirmed_at, expires_at
        FROM wallet_topups
        WHERE id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()


def confirm_wallet_topup(conn, topup_id, user_id):
    if not conn.in_transaction:
        conn.execute("BEGIN IMMEDIATE")
    topup = conn.execute(
        """
        SELECT id, user_id, amount_cents, payment_method, gateway_provider, status, external_reference, created_at, confirmed_at, expires_at
        FROM wallet_topups
        WHERE id = ?
        """,
        (int(topup_id),),
    ).fetchone()

    if topup is None or int(topup["user_id"]) != int(user_id):
        raise ValueError("Recarga não encontrada para esta conta.")
    if topup["status"] == "paid":
        return topup, wallet_payload(conn, user_id), True
    if topup["status"] != "pending":
        raise ValueError("Esta recarga não pode mais ser confirmada.")
    if topup["expires_at"] and datetime.utcnow() > parse_utc_iso(topup["expires_at"]):
        conn.execute("UPDATE wallet_topups SET status = 'expired' WHERE id = ?", (int(topup_id),))
        raise ValueError("Esta cobrança expirou. Gere uma nova recarga.")

    conn.execute(
        "UPDATE wallet_topups SET status = 'paid', confirmed_at = ? WHERE id = ?",
        (now_iso(), int(topup_id)),
    )
    conn.execute(
        """
        INSERT INTO wallet_transactions (
            user_id, appointment_id, topup_id, kind, amount_cents, description, created_at
        )
        VALUES (?, NULL, ?, 'deposit', ?, ?, ?)
        """,
        (
            user_id,
            int(topup_id),
            int(topup["amount_cents"]),
            f"Recarga confirmada via {WALLET_PAYMENT_METHODS.get(topup['payment_method'], topup['payment_method'])} no valor de {format_brl(topup['amount_cents'])}.",
            now_iso(),
        ),
    )
    create_notification(
        conn,
        user_id,
        "success",
        "Saldo confirmado",
        f"Sua carteira recebeu {format_brl(topup['amount_cents'])} após a confirmação do pagamento.",
        external_key=f"wallet-topup-paid:{topup_id}:{user_id}",
    )
    confirmed = conn.execute(
        """
        SELECT id, amount_cents, payment_method, gateway_provider, status, external_reference, created_at, confirmed_at, expires_at
        FROM wallet_topups
        WHERE id = ?
        """,
        (int(topup_id),),
    ).fetchone()
    return confirmed, wallet_payload(conn, user_id), False


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
                expires_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS professionals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                slug TEXT NOT NULL UNIQUE,
                nome TEXT NOT NULL,
                titulo TEXT NOT NULL,
                conselho TEXT NOT NULL,
                registro_profissional TEXT NOT NULL,
                bio TEXT NOT NULL,
                especialidades TEXT NOT NULL,
                abordagem TEXT NOT NULL,
                experiencia TEXT NOT NULL,
                frase TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS professional_availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                professional_id INTEGER NOT NULL,
                weekday INTEGER NOT NULL,
                slot TEXT NOT NULL,
                UNIQUE(professional_id, weekday, slot),
                FOREIGN KEY(professional_id) REFERENCES professionals(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                appointment_id INTEGER NOT NULL UNIQUE,
                professional_id INTEGER NOT NULL,
                patient_user_id INTEGER NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                plan TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                FOREIGN KEY(appointment_id) REFERENCES appointments(id) ON DELETE CASCADE,
                FOREIGN KEY(professional_id) REFERENCES professionals(id) ON DELETE CASCADE,
                FOREIGN KEY(patient_user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                external_key TEXT UNIQUE,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
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
                price_cents INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(professional_id, data, hora),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(professional_id) REFERENCES professionals(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS wallet_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                appointment_id INTEGER,
                topup_id INTEGER,
                kind TEXT NOT NULL,
                amount_cents INTEGER NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(appointment_id) REFERENCES appointments(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS wallet_topups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount_cents INTEGER NOT NULL,
                payment_method TEXT NOT NULL,
                gateway_provider TEXT NOT NULL DEFAULT 'simulado',
                status TEXT NOT NULL DEFAULT 'pending',
                external_reference TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                confirmed_at TEXT,
                expires_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_appointments_user_id
                ON appointments(user_id);
            CREATE INDEX IF NOT EXISTS idx_appointments_professional_date
                ON appointments(professional_id, data);
            CREATE INDEX IF NOT EXISTS idx_notifications_user_read
                ON notifications(user_id, is_read);
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id
                ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_wallet_transactions_user_id
                ON wallet_transactions(user_id);
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
            "professionals",
            "user_id",
            "ALTER TABLE professionals ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL",
        )
        ensure_column(
            conn,
            "sessions",
            "expires_at",
            "ALTER TABLE sessions ADD COLUMN expires_at TEXT",
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
        ensure_column(
            conn,
            "appointments",
            "price_cents",
            "ALTER TABLE appointments ADD COLUMN price_cents INTEGER NOT NULL DEFAULT 0",
        )
        ensure_column(
            conn,
            "wallet_transactions",
            "topup_id",
            "ALTER TABLE wallet_transactions ADD COLUMN topup_id INTEGER",
        )

        seed_professionals(conn)
        seed_availability(conn)
        seed_admin(conn)
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
        service_case = "\n".join(
            f"                WHEN '{k}' THEN {v}" for k, v in SERVICE_PRICES_CENTS.items()
        )
        mode_case = "\n".join(
            f"                WHEN '{k}' THEN {v}" for k, v in MODE_PRICE_ADJUSTMENTS_CENTS.items()
        )
        conn.execute(
            f"""
            UPDATE appointments
            SET price_cents = CASE servico
{service_case}
                ELSE 0
            END + CASE modalidade
{mode_case}
                ELSE 0
            END
            WHERE price_cents IS NULL OR price_cents = 0
            """
        )


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "NutrimenteAPI/2.0"

    def log_message(self, fmt, *args):
        return

    def end_headers(self):
        origin = self.headers.get("Origin", "")
        allowed = "*" if DEBUG else ALLOWED_ORIGIN
        self.send_header("Access-Control-Allow-Origin", allowed if DEBUG or origin == ALLOWED_ORIGIN else "null")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
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

        if parsed.path == "/api/wallet":
            user = self.require_user()
            if not user:
                return
            return self.handle_get_wallet(user)

        if parsed.path == "/api/appointments":
            user = self.require_user()
            if not user:
                return
            return self.handle_list_appointments(user)
        if parsed.path == "/api/notifications":
            user = self.require_user()
            if not user:
                return
            return self.handle_list_notifications(user)
        if parsed.path == "/api/professional/dashboard":
            user = self.require_user()
            if not user:
                return
            return self.handle_professional_dashboard(user)
        if parsed.path == "/api/admin/dashboard":
            user = self.require_user()
            if not user:
                return
            return self.handle_admin_dashboard(user)

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
        if parsed.path == "/api/password-reset/request":
            data = self.read_json()
            if data is None:
                return
            return self.handle_password_reset_request(data)
        if parsed.path == "/api/password-reset/confirm":
            data = self.read_json()
            if data is None:
                return
            return self.handle_password_reset_confirm(data)

        if parsed.path == "/api/logout":
            token = self.get_token()
            if token:
                with get_db() as conn:
                    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return self.json_response(200, {"message": "Sessão encerrada."})

        if parsed.path == "/api/wallet/add-funds":
            user = self.require_user()
            if not user:
                return
            data = self.read_json()
            if data is None:
                return
            return self.handle_add_funds(user, data)
        if parsed.path == "/api/wallet/topups":
            user = self.require_user()
            if not user:
                return
            data = self.read_json()
            if data is None:
                return
            return self.handle_create_wallet_topup(user, data)
        if parsed.path.startswith("/api/wallet/topups/") and parsed.path.endswith("/confirm"):
            user = self.require_user()
            if not user:
                return
            topup_id = parsed.path.split("/")[-2]
            return self.handle_confirm_wallet_topup(user, topup_id)

        if parsed.path == "/api/appointments":
            user = self.require_user()
            if not user:
                return
            data = self.read_json()
            if data is None:
                return
            return self.handle_create_appointment(user, data)
        if parsed.path == "/api/notifications/read-all":
            user = self.require_user()
            if not user:
                return
            with get_db() as conn:
                conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user["id"],))
            return self.json_response(200, {"message": "Notificações marcadas como lidas."})

        return self.json_response(404, {"error": "Rota não encontrada."})

    def do_PUT(self):
        parsed = urlparse(self.path)
        user = self.require_user()
        if not user:
            return
        data = self.read_json()
        if data is None:
            return

        if parsed.path == "/api/professional/profile":
            return self.handle_update_professional_profile(user, data)
        if parsed.path == "/api/professional/availability":
            return self.handle_update_professional_availability(user, data)
        if parsed.path.startswith("/api/appointments/"):
            appointment_id = parsed.path.rsplit("/", 1)[-1]
            return self.handle_reschedule_appointment(user, appointment_id, data)
        if parsed.path.startswith("/api/records/"):
            appointment_id = parsed.path.rsplit("/", 1)[-1]
            return self.handle_save_record(user, appointment_id, data)

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
            conn.execute("BEGIN IMMEDIATE")
            appointment = conn.execute(
                """
                SELECT appointments.*, professionals.user_id AS professional_user_id
                FROM appointments
                JOIN professionals ON professionals.id = appointments.professional_id
                WHERE appointments.id = ?
                """,
                (int(appointment_id),),
            ).fetchone()

            if appointment is None:
                return self.json_response(404, {"error": "Agendamento não encontrado."})

            allowed = user["id"] == appointment["user_id"] or user["id"] == appointment["professional_user_id"]
            if not allowed:
                return self.json_response(403, {"error": "Sem permissão para cancelar este agendamento."})

            if (
                user["id"] == appointment["user_id"]
                and appointment_datetime(appointment["data"], appointment["hora"]) - datetime.utcnow()
                < timedelta(hours=CANCELLATION_WINDOW_HOURS)
            ):
                return self.json_response(
                    409,
                    {"error": f"Cancelamentos pelo paciente exigem pelo menos {CANCELLATION_WINDOW_HOURS} horas de antecedência."},
                )

            refund_amount = int(appointment["price_cents"] or 0)
            if refund_amount > 0:
                conn.execute(
                    """
                    INSERT INTO wallet_transactions (
                        user_id, appointment_id, topup_id, kind, amount_cents, description, created_at
                    )
                    VALUES (?, ?, NULL, 'refund', ?, ?, ?)
                    """,
                    (
                        appointment["user_id"],
                        int(appointment_id),
                        refund_amount,
                        f"Estorno da consulta cancelada de {appointment['data']} as {appointment['hora']}.",
                        now_iso(),
                    ),
                )
            conn.execute("DELETE FROM appointments WHERE id = ?", (int(appointment_id),))
            create_notification(
                conn,
                appointment["user_id"],
                "warning",
                "Consulta cancelada",
                f"A consulta de {appointment['data']} às {appointment['hora']} foi cancelada.",
                external_key=f"cancel:{appointment_id}:patient",
            )
            if refund_amount > 0:
                create_notification(
                    conn,
                    appointment["user_id"],
                    "success",
                    "Estorno realizado",
                    f"O valor de {format_brl(refund_amount)} voltou para sua carteira.",
                    external_key=f"refund:{appointment_id}:patient",
                )
            if appointment["professional_user_id"]:
                create_notification(
                    conn,
                    appointment["professional_user_id"],
                    "warning",
                    "Consulta cancelada",
                    f"A consulta com o paciente {appointment['nome']} foi cancelada.",
                    external_key=f"cancel:{appointment_id}:professional",
                )

        return self.json_response(200, {"message": "Agendamento cancelado."})

    def handle_reschedule_appointment(self, user, appointment_id, data):
        if not str(appointment_id).isdigit():
            return self.json_response(400, {"error": "Agendamento inválido."})

        new_date = (data.get("data") or "").strip()
        new_time = (data.get("hora") or "").strip()
        if not new_date or not new_time:
            return self.json_response(400, {"error": "Informe a nova data e horário."})

        try:
            new_dt = appointment_datetime(new_date, new_time)
        except ValueError:
            return self.json_response(400, {"error": "Nova data ou horário inválidos."})

        with get_db() as conn:
            appointment = conn.execute(
                """
                SELECT appointments.*, professionals.user_id AS professional_user_id
                FROM appointments
                JOIN professionals ON professionals.id = appointments.professional_id
                WHERE appointments.id = ?
                """,
                (int(appointment_id),),
            ).fetchone()

            if appointment is None:
                return self.json_response(404, {"error": "Agendamento não encontrado."})

            allowed = user["id"] == appointment["user_id"] or user["id"] == appointment["professional_user_id"]
            if not allowed:
                return self.json_response(403, {"error": "Sem permissão para reagendar este agendamento."})
            if (
                user["id"] == appointment["user_id"]
                and appointment_datetime(appointment["data"], appointment["hora"]) - datetime.utcnow()
                < timedelta(hours=CANCELLATION_WINDOW_HOURS)
            ):
                return self.json_response(
                    409,
                    {"error": f"Reagendamentos pelo paciente exigem pelo menos {CANCELLATION_WINDOW_HOURS} horas de antecedência."},
                )

            allowed_slot = conn.execute(
                """
                SELECT 1
                FROM professional_availability
                WHERE professional_id = ? AND weekday = ? AND slot = ?
                """,
                (appointment["professional_id"], new_dt.weekday(), new_time),
            ).fetchone()
            if allowed_slot is None:
                return self.json_response(409, {"error": "O novo horário não está disponível para este profissional."})

            try:
                conn.execute(
                    """
                    UPDATE appointments
                    SET data = ?, hora = ?, room_name = ?
                    WHERE id = ?
                    """,
                    (
                        new_date,
                        new_time,
                        self.build_room_name(appointment["nome"], new_date, new_time),
                        int(appointment_id),
                    ),
                )
            except sqlite3.IntegrityError:
                return self.json_response(409, {"error": "O novo horário já foi reservado."})

            create_notification(
                conn,
                appointment["user_id"],
                "info",
                "Consulta reagendada",
                f"Sua consulta agora está marcada para {new_date} às {new_time}.",
                external_key=f"reschedule:{appointment_id}:patient:{new_date}:{new_time}",
            )
            if appointment["professional_user_id"]:
                create_notification(
                    conn,
                    appointment["professional_user_id"],
                    "info",
                    "Consulta reagendada",
                    f"O agendamento de {appointment['nome']} foi movido para {new_date} às {new_time}.",
                    external_key=f"reschedule:{appointment_id}:professional:{new_date}:{new_time}",
                )

        return self.json_response(200, {"message": "Agendamento reagendado com sucesso."})

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
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT users.id, users.nome, users.email, users.tipo, users.conselho, users.registro_profissional,
                       professionals.id AS professional_id,
                       sessions.expires_at AS session_expires_at
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                LEFT JOIN professionals ON professionals.user_id = users.id
                WHERE sessions.token = ?
                """,
                (token,),
            ).fetchone()

            if row is None:
                self.json_response(401, {"error": "Sessão inválida ou expirada."})
                return None

            expires_at = row["session_expires_at"]
            if expires_at and datetime.utcnow() > parse_utc_iso(expires_at):
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                self.json_response(401, {"error": "Sessão expirada. Faça login novamente."})
                return None

            conn.execute(
                "UPDATE sessions SET expires_at = ? WHERE token = ?",
                (future_iso(hours=SESSION_IDLE_HOURS), token),
            )

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
                "servicePrices": SERVICE_PRICES_CENTS,
                "modePriceAdjustments": MODE_PRICE_ADJUSTMENTS_CENTS,
                "slots": AVAILABLE_SLOTS,
                "weekdays": WEEKDAYS,
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

        weekday = datetime.strptime(date_value, "%Y-%m-%d").weekday()
        with get_db() as conn:
            allowed_rows = conn.execute(
                """
                SELECT slot
                FROM professional_availability
                WHERE professional_id = ? AND weekday = ?
                ORDER BY slot
                """,
                (int(professional_id), weekday),
            ).fetchall()
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
            {"hora": row["slot"], "disponivel": row["slot"] not in booked}
            for row in allowed_rows
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
            .replace(" ", "")
            or None
        )

        if len(nome) < 3:
            return self.json_response(400, {"error": "Nome inválido."})
        if not is_valid_email(email):
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
        if tipo == "profissional" and not is_valid_professional_document(
            conselho, registro_profissional
        ):
            return self.json_response(
                400,
                {"error": "Informe um registo profissional válido para o conselho selecionado."},
            )

        try:
            with get_db() as conn:
                cursor = conn.execute(
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

                if tipo == "profissional":
                    professional = conn.execute(
                        """
                        SELECT id, user_id
                        FROM professionals
                        WHERE conselho = ? AND registro_profissional = ?
                        """,
                        (conselho, registro_profissional),
                    ).fetchone()

                    if professional and professional["user_id"] not in {None, cursor.lastrowid}:
                        raise sqlite3.IntegrityError

                    if professional:
                        conn.execute(
                            "UPDATE professionals SET user_id = ?, nome = ? WHERE id = ?",
                            (cursor.lastrowid, nome, professional["id"]),
                        )
                    else:
                        base_slug = slugify(nome)
                        slug = base_slug
                        suffix = 1
                        while conn.execute(
                            "SELECT 1 FROM professionals WHERE slug = ?",
                            (slug,),
                        ).fetchone():
                            suffix += 1
                            slug = f"{base_slug}-{suffix}"

                        conn.execute(
                            """
                            INSERT INTO professionals (
                                user_id, slug, nome, titulo, conselho, registro_profissional,
                                bio, especialidades, abordagem, experiencia, frase
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                cursor.lastrowid,
                                slug,
                                nome,
                                "Profissional NutriMente",
                                conselho,
                                registro_profissional,
                                "Edite o seu perfil profissional para apresentar sua abordagem.",
                                json.dumps(["Especialidade principal"], ensure_ascii=False),
                                json.dumps(["Descreva a sua abordagem"], ensure_ascii=False),
                                json.dumps(["Adicione a sua experiência"], ensure_ascii=False),
                                "Transformando cuidado em acompanhamento consistente.",
                            ),
                        )
                        professional_id = conn.execute(
                            "SELECT id FROM professionals WHERE user_id = ?",
                            (cursor.lastrowid,),
                        ).fetchone()["id"]
                        for weekday in range(5):
                            for slot in AVAILABLE_SLOTS:
                                conn.execute(
                                    """
                                    INSERT INTO professional_availability (professional_id, weekday, slot)
                                    VALUES (?, ?, ?)
                                    """,
                                    (professional_id, weekday, slot),
                                )
        except sqlite3.IntegrityError:
            return self.json_response(409, {"error": "Email já cadastrado."})
        except sqlite3.Error:
            return self.json_response(
                500, {"error": "Não foi possível concluir o cadastro no momento."}
            )

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
                "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token, user["id"], now_iso(), future_iso(hours=SESSION_IDLE_HOURS)),
            )
            hydrated = conn.execute(
                """
                SELECT users.id, users.nome, users.email, users.tipo, users.conselho, users.registro_profissional,
                       professionals.id AS professional_id
                FROM users
                LEFT JOIN professionals ON professionals.user_id = users.id
                WHERE users.id = ?
                """,
                (user["id"],),
            ).fetchone()

        return self.json_response(
            200,
            {"token": token, "user": user_payload(hydrated), "message": "Login realizado."},
        )

    def handle_password_reset_request(self, data):
        email = (data.get("email") or "").strip().lower()
        if not is_valid_email(email):
            return self.json_response(400, {"error": "Informe um email válido."})

        with get_db() as conn:
            user = conn.execute(
                "SELECT id, nome FROM users WHERE email = ?",
                (email,),
            ).fetchone()
            if not user:
                return self.json_response(
                    200,
                    {"message": "Se a conta existir, um código de recuperação foi gerado."},
                )

            conn.execute(
                "DELETE FROM password_resets WHERE user_id = ? AND used_at IS NULL",
                (user["id"],),
            )
            token = generate_reset_token()
            expires_at = (datetime.utcnow() + timedelta(minutes=30)).isoformat(timespec="seconds") + "Z"
            conn.execute(
                """
                INSERT INTO password_resets (user_id, token, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user["id"], token, expires_at, now_iso()),
            )
            create_notification(
                conn,
                user["id"],
                "info",
                "Código de recuperação gerado",
                "Use o código recebido para redefinir sua senha na tela de acesso.",
                external_key=f"password-reset:{user['id']}:{token}",
            )

        return self.json_response(
            200,
            {
                "message": "Código de recuperação gerado. Em produção ele seria enviado por e-mail.",
                **({"resetToken": token, "expiresInMinutes": 30} if DEBUG else {}),
            },
        )

    def handle_password_reset_confirm(self, data):
        token = (data.get("token") or "").strip().upper()
        senha = data.get("senha") or ""

        if len(token) < 6:
            return self.json_response(400, {"error": "Código de recuperação inválido."})
        if len(senha) < 8:
            return self.json_response(400, {"error": "A nova senha deve ter pelo menos 8 caracteres."})

        with get_db() as conn:
            row = conn.execute(
                """
                SELECT id, user_id, expires_at, used_at
                FROM password_resets
                WHERE token = ?
                """,
                (token,),
            ).fetchone()
            if row is None:
                return self.json_response(404, {"error": "Código de recuperação não encontrado."})
            if row["used_at"]:
                return self.json_response(409, {"error": "Este código já foi utilizado."})
            if datetime.utcnow() > datetime.fromisoformat(row["expires_at"].replace("Z", "")):
                return self.json_response(410, {"error": "Este código expirou. Solicite outro."})

            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(senha), row["user_id"]),
            )
            conn.execute(
                "UPDATE password_resets SET used_at = ? WHERE id = ?",
                (now_iso(), row["id"]),
            )
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (row["user_id"],))
            create_notification(
                conn,
                row["user_id"],
                "success",
                "Senha redefinida",
                "Sua senha foi alterada com sucesso. Faça login novamente.",
                external_key=f"password-reset-complete:{row['id']}",
            )

        return self.json_response(200, {"message": "Senha redefinida com sucesso."})

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

    def handle_get_wallet(self, user):
        with get_db() as conn:
            snapshot = wallet_payload(conn, user["id"])
        return self.json_response(200, snapshot)

    def handle_create_wallet_topup(self, user, data):
        amount_cents = data.get("amountCents")
        if amount_cents is None:
            amount_cents = parse_money_to_cents(data.get("amount"))
        elif isinstance(amount_cents, bool):
            amount_cents = None
        else:
            try:
                amount_cents = int(amount_cents)
            except (TypeError, ValueError):
                amount_cents = None

        payment_method = (data.get("paymentMethod") or "card").strip().lower()

        if amount_cents is None:
            return self.json_response(400, {"error": "Informe um valor válido para a recarga."})
        if amount_cents < MIN_WALLET_TOP_UP_CENTS:
            return self.json_response(
                400,
                {"error": f"A recarga mínima é de {format_brl(MIN_WALLET_TOP_UP_CENTS)}."},
            )
        if amount_cents > MAX_WALLET_TOP_UP_CENTS:
            return self.json_response(
                400,
                {"error": f"A recarga máxima por operação é de {format_brl(MAX_WALLET_TOP_UP_CENTS)}."},
            )
        if payment_method not in WALLET_PAYMENT_METHODS:
            return self.json_response(400, {"error": "Método de pagamento inválido para a recarga."})

        with get_db() as conn:
            topup = create_wallet_topup(conn, user["id"], amount_cents, payment_method)
            snapshot = wallet_payload(conn, user["id"])

        return self.json_response(
            201,
            {
                "message": "Recarga criada. Confirme o pagamento para liberar o saldo.",
                "topUp": wallet_topup_payload(topup),
                "wallet": snapshot,
            },
        )

    def handle_confirm_wallet_topup(self, user, topup_id):
        if not str(topup_id).isdigit():
            return self.json_response(400, {"error": "Recarga inválida."})

        try:
            with get_db() as conn:
                topup, snapshot, already_paid = confirm_wallet_topup(conn, int(topup_id), user["id"])
        except ValueError as exc:
            return self.json_response(409, {"error": str(exc)})

        return self.json_response(
            200,
            {
                "message": "Pagamento já confirmado anteriormente." if already_paid else "Pagamento confirmado e saldo disponível.",
                "topUp": wallet_topup_payload(topup),
                "wallet": snapshot,
            },
        )

    def handle_add_funds(self, user, data):
        """Rota legada — delega para handle_create_wallet_topup e confirma automaticamente (ambiente local)."""
        amount_cents = data.get("amountCents")
        if amount_cents is None:
            amount_cents = parse_money_to_cents(data.get("amount"))
        elif isinstance(amount_cents, bool):
            amount_cents = None
        else:
            try:
                amount_cents = int(amount_cents)
            except (TypeError, ValueError):
                amount_cents = None

        if amount_cents is None:
            return self.json_response(400, {"error": "Informe um valor válido para a recarga."})
        if amount_cents < MIN_WALLET_TOP_UP_CENTS:
            return self.json_response(
                400,
                {"error": f"A recarga mínima é de {format_brl(MIN_WALLET_TOP_UP_CENTS)}."},
            )
        if amount_cents > MAX_WALLET_TOP_UP_CENTS:
            return self.json_response(
                400,
                {"error": f"A recarga máxima por operação é de {format_brl(MAX_WALLET_TOP_UP_CENTS)}."},
            )
        if (data.get("paymentMethod") or "card").strip().lower() not in WALLET_PAYMENT_METHODS:
            return self.json_response(400, {"error": "Método de pagamento inválido para a recarga."})

        with get_db() as conn:
            topup = create_wallet_topup(conn, user["id"], amount_cents, "card", gateway_provider="simulado")
            confirm_wallet_topup(conn, topup["id"], user["id"])
            snapshot = wallet_payload(conn, user["id"])

        return self.json_response(
            201,
            {"message": "Saldo adicionado com sucesso.", "wallet": snapshot},
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
        price_cents = calculate_appointment_price_cents(servico, modalidade)

        if not appointment_date or not appointment_time:
            return self.json_response(400, {"error": "Data e horário são obrigatórios."})
        if len(nome) < 3:
            return self.json_response(400, {"error": "Nome inválido."})
        if not is_valid_email(email):
            return self.json_response(400, {"error": "Email inválido."})
        if len(telefone) < 8:
            return self.json_response(400, {"error": "Telefone inválido."})
        if servico not in SERVICES:
            return self.json_response(400, {"error": "Serviço inválido."})
        if modalidade not in MODES:
            return self.json_response(400, {"error": "Modalidade inválida."})
        if not professional_id.isdigit():
            return self.json_response(400, {"error": "Profissional inválido."})

        try:
            appointment_dt = datetime.strptime(
                f"{appointment_date} {appointment_time}",
                "%Y-%m-%d %H:%M",
            )
        except ValueError:
            return self.json_response(400, {"error": "Data ou horário inválidos."})

        if appointment_dt.date() < datetime.utcnow().date():
            return self.json_response(400, {"error": "Selecione uma data futura."})

        room_name = self.build_room_name(nome, appointment_date, appointment_time)

        try:
            with get_db() as conn:
                conn.execute("BEGIN IMMEDIATE")
                professional = conn.execute(
                    "SELECT id, slug, nome, titulo, user_id FROM professionals WHERE id = ?",
                    (int(professional_id),),
                ).fetchone()
                if professional is None:
                    return self.json_response(404, {"error": "Profissional não encontrado."})
                allowed = conn.execute(
                    """
                    SELECT 1
                    FROM professional_availability
                    WHERE professional_id = ? AND weekday = ? AND slot = ?
                    """,
                    (professional["id"], appointment_dt.weekday(), appointment_time),
                ).fetchone()
                if allowed is None:
                    return self.json_response(
                        409,
                        {"error": "Esse horário não está disponível para o profissional selecionado."},
                    )

                current_balance = wallet_balance_cents(conn, user["id"])
                if current_balance < price_cents:
                    missing_balance = price_cents - current_balance
                    return self.json_response(
                        409,
                        {
                            "error": f"Saldo insuficiente. Adicione pelo menos {format_brl(missing_balance)} para concluir o agendamento.",
                            "wallet": wallet_payload(conn, user["id"]),
                            "priceCents": price_cents,
                            "priceFormatted": format_brl(price_cents),
                        },
                    )

                cursor = conn.execute(
                    """
                    INSERT INTO appointments (
                        user_id, professional_id, data, hora, nome, email, telefone,
                        servico, modalidade, observacoes, room_name, price_cents, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        price_cents,
                        now_iso(),
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO wallet_transactions (
                        user_id, appointment_id, topup_id, kind, amount_cents, description, created_at
                    )
                    VALUES (?, ?, NULL, 'payment', ?, ?, ?)
                    """,
                    (
                        user["id"],
                        cursor.lastrowid,
                        -price_cents,
                        f"Pagamento da consulta com {professional['nome']} em {appointment_date} as {appointment_time}.",
                        now_iso(),
                    ),
                )
                create_notification(
                    conn,
                    user["id"],
                    "success",
                    "Consulta confirmada",
                    f"Sua consulta com {professional['nome']} foi agendada para {appointment_date} às {appointment_time}.",
                    external_key=f"booking:{cursor.lastrowid}:patient",
                )
                if professional["user_id"]:
                    create_notification(
                        conn,
                        professional["user_id"],
                        "info",
                        "Nova consulta agendada",
                        f"{nome} marcou atendimento para {appointment_date} às {appointment_time}.",
                        external_key=f"booking:{cursor.lastrowid}:professional",
                    )
                new_appointment_id = cursor.lastrowid
                snapshot = wallet_payload(conn, user["id"])
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
                    "id": new_appointment_id,
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
                    "priceCents": price_cents,
                    "priceFormatted": format_brl(price_cents),
                },
                "wallet": snapshot,
            },
        )

    def handle_list_notifications(self, user):
        with get_db() as conn:
            self.sync_reminders(conn, user)
            rows = conn.execute(
                """
                SELECT id, kind, title, message, is_read, created_at
                FROM notifications
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 25
                """,
                (user["id"],),
            ).fetchall()
        return self.json_response(200, {"notifications": [notification_payload(row) for row in rows]})

    def handle_professional_dashboard(self, user):
        if user["tipo"] != "profissional" or not user["professional_id"]:
            return self.json_response(403, {"error": "Apenas profissionais têm acesso a este painel."})

        with get_db() as conn:
            self.sync_reminders(conn, user)
            profile = conn.execute(
                "SELECT * FROM professionals WHERE id = ?",
                (user["professional_id"],),
            ).fetchone()
            availability_rows = conn.execute(
                """
                SELECT weekday, slot
                FROM professional_availability
                WHERE professional_id = ?
                ORDER BY weekday, slot
                """,
                (user["professional_id"],),
            ).fetchall()
            appointment_rows = conn.execute(
                """
                SELECT
                    appointments.id AS appointment_id,
                    appointments.data,
                    appointments.hora,
                    appointments.servico,
                    appointments.modalidade,
                    appointments.observacoes,
                    appointments.room_name,
                    patients.id AS patient_id,
                    patients.nome AS patient_nome,
                    patients.email AS patient_email,
                    appointments.telefone,
                    records.notes AS record_notes,
                    records.plan AS record_plan,
                    records.updated_at AS record_updated_at
                FROM appointments
                JOIN users AS patients ON patients.id = appointments.user_id
                LEFT JOIN records ON records.appointment_id = appointments.id
                WHERE appointments.professional_id = ?
                ORDER BY appointments.data, appointments.hora
                """,
                (user["professional_id"],),
            ).fetchall()

        appointments = []
        for row in appointment_rows:
            appointments.append(
                {
                    "appointmentId": row["appointment_id"],
                    "data": row["data"],
                    "hora": row["hora"],
                    "servico": row["servico"],
                    "modalidade": row["modalidade"],
                    "observacoes": row["observacoes"] or "",
                    "roomName": row["room_name"],
                    "patientId": row["patient_id"],
                    "patientName": row["patient_nome"],
                    "patientEmail": row["patient_email"],
                    "patientPhone": row["telefone"],
                    "record": {
                        "notes": row["record_notes"] or "",
                        "plan": row["record_plan"] or "",
                        "updatedAt": row["record_updated_at"],
                    },
                }
            )

        return self.json_response(
            200,
            {
                "profile": professional_payload(profile),
                "availability": availability_payload(availability_rows),
                "appointments": appointments,
                "weekdays": WEEKDAYS,
                "slots": AVAILABLE_SLOTS,
            },
        )

    def handle_admin_dashboard(self, user):
        if user["tipo"] != "admin":
            return self.json_response(403, {"error": "Apenas administradores podem acessar este painel."})

        with get_db() as conn:
            user_rows = conn.execute(
                """
                SELECT id, nome, email, tipo, created_at
                FROM users
                ORDER BY id DESC
                LIMIT 20
                """
            ).fetchall()
            transaction_rows = conn.execute(
                """
                SELECT
                    wallet_transactions.id,
                    wallet_transactions.kind,
                    wallet_transactions.amount_cents,
                    wallet_transactions.description,
                    wallet_transactions.created_at,
                    users.nome,
                    users.email
                FROM wallet_transactions
                JOIN users ON users.id = wallet_transactions.user_id
                ORDER BY wallet_transactions.id DESC
                LIMIT 30
                """
            ).fetchall()
            stats = {
                "users": conn.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"],
                "patients": conn.execute("SELECT COUNT(*) AS total FROM users WHERE tipo = 'cliente'").fetchone()["total"],
                "professionals": conn.execute("SELECT COUNT(*) AS total FROM users WHERE tipo = 'profissional'").fetchone()["total"],
                "walletVolumeCents": conn.execute(
                    "SELECT COALESCE(SUM(amount_cents), 0) AS total FROM wallet_transactions WHERE kind = 'deposit'"
                ).fetchone()["total"],
                "appointmentsPaidCents": conn.execute(
                    "SELECT COALESCE(SUM(ABS(amount_cents)), 0) AS total FROM wallet_transactions WHERE kind = 'payment'"
                ).fetchone()["total"],
            }

        return self.json_response(
            200,
            {
                "stats": {
                    **stats,
                    "walletVolumeFormatted": format_brl(stats["walletVolumeCents"]),
                    "appointmentsPaidFormatted": format_brl(stats["appointmentsPaidCents"]),
                },
                "users": [
                    {
                        "id": row["id"],
                        "nome": row["nome"],
                        "email": row["email"],
                        "tipo": row["tipo"],
                        "createdAt": row["created_at"],
                    }
                    for row in user_rows
                ],
                "transactions": [
                    {
                        "id": row["id"],
                        "kind": row["kind"],
                        "amountCents": row["amount_cents"],
                        "amountFormatted": format_brl(abs(row["amount_cents"])),
                        "description": row["description"],
                        "nome": row["nome"],
                        "email": row["email"],
                        "createdAt": row["created_at"],
                        "direction": "credit" if int(row["amount_cents"] or 0) >= 0 else "debit",
                    }
                    for row in transaction_rows
                ],
                "security": {
                    "lgpd": "Dados financeiros e clínicos exibidos apenas para perfis autorizados. Recomenda-se consentimento explícito, política de retenção e trilha de auditoria em produção.",
                    "gatewayMode": "Simulado para ambiente local. Substitua por webhooks reais do Stripe ou Mercado Pago em produção.",
                },
            },
        )

    def handle_update_professional_profile(self, user, data):
        if user["tipo"] != "profissional" or not user["professional_id"]:
            return self.json_response(403, {"error": "Apenas profissionais podem editar o perfil."})

        titulo = (data.get("titulo") or "").strip()
        bio = (data.get("bio") or "").strip()
        frase = (data.get("frase") or "").strip()
        especialidades = [item.strip() for item in (data.get("especialidades") or []) if str(item).strip()]
        abordagem = [item.strip() for item in (data.get("abordagem") or []) if str(item).strip()]
        experiencia = [item.strip() for item in (data.get("experiencia") or []) if str(item).strip()]

        if not titulo or not bio or not frase:
            return self.json_response(400, {"error": "Título, bio e frase são obrigatórios."})

        with get_db() as conn:
            conn.execute(
                """
                UPDATE professionals
                SET titulo = ?, bio = ?, frase = ?, especialidades = ?, abordagem = ?, experiencia = ?
                WHERE id = ?
                """,
                (
                    titulo,
                    bio,
                    frase,
                    json.dumps(especialidades or ["Especialidade principal"], ensure_ascii=False),
                    json.dumps(abordagem or ["Descreva a sua abordagem"], ensure_ascii=False),
                    json.dumps(experiencia or ["Adicione a sua experiência"], ensure_ascii=False),
                    user["professional_id"],
                ),
            )
        return self.json_response(200, {"message": "Perfil profissional atualizado."})

    def handle_update_professional_availability(self, user, data):
        if user["tipo"] != "profissional" or not user["professional_id"]:
            return self.json_response(403, {"error": "Apenas profissionais podem editar horários."})

        availability = data.get("availability") or {}
        rows = []
        valid_days = {str(key) for key in WEEKDAYS}
        for weekday, slots in availability.items():
            if str(weekday) not in valid_days:
                continue
            for slot in slots:
                if slot in AVAILABLE_SLOTS:
                    rows.append((user["professional_id"], int(weekday), slot))

        if not rows:
            return self.json_response(400, {"error": "Selecione pelo menos um horário disponível."})

        with get_db() as conn:
            conn.execute("DELETE FROM professional_availability WHERE professional_id = ?", (user["professional_id"],))
            conn.executemany(
                """
                INSERT INTO professional_availability (professional_id, weekday, slot)
                VALUES (?, ?, ?)
                """,
                rows,
            )
        return self.json_response(200, {"message": "Disponibilidade atualizada."})

    def handle_save_record(self, user, appointment_id, data):
        if user["tipo"] != "profissional" or not user["professional_id"]:
            return self.json_response(403, {"error": "Apenas profissionais podem atualizar prontuários."})
        if not str(appointment_id).isdigit():
            return self.json_response(400, {"error": "Consulta inválida."})

        notes = (data.get("notes") or "").strip()
        plan = (data.get("plan") or "").strip()

        with get_db() as conn:
            appointment = conn.execute(
                """
                SELECT id, user_id
                FROM appointments
                WHERE id = ? AND professional_id = ?
                """,
                (int(appointment_id), user["professional_id"]),
            ).fetchone()
            if appointment is None:
                return self.json_response(404, {"error": "Consulta não encontrada para este profissional."})

            exists = conn.execute(
                "SELECT id FROM records WHERE appointment_id = ?",
                (int(appointment_id),),
            ).fetchone()
            if exists:
                conn.execute(
                    "UPDATE records SET notes = ?, plan = ?, updated_at = ? WHERE appointment_id = ?",
                    (notes, plan, now_iso(), int(appointment_id)),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO records (appointment_id, professional_id, patient_user_id, notes, plan, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (int(appointment_id), user["professional_id"], appointment["user_id"], notes, plan, now_iso()),
                )

            create_notification(
                conn,
                appointment["user_id"],
                "info",
                "Prontuário atualizado",
                "O profissional registrou a evolução do seu atendimento na plataforma.",
                external_key=f"record:{appointment_id}:{appointment['user_id']}",
            )

        return self.json_response(200, {"message": "Prontuário atualizado com sucesso."})

    def sync_reminders(self, conn, user):
        now_utc = datetime.utcnow()
        limit = now_utc + timedelta(hours=24)

        if user["tipo"] == "profissional" and user["professional_id"]:
            rows = conn.execute(
                """
                SELECT id, data, hora, nome
                FROM appointments
                WHERE professional_id = ?
                """,
                (user["professional_id"],),
            ).fetchall()
            for row in rows:
                appointment_dt = datetime.strptime(f"{row['data']} {row['hora']}", "%Y-%m-%d %H:%M")
                if now_utc <= appointment_dt <= limit:
                    create_notification(
                        conn,
                        user["id"],
                        "info",
                        "Lembrete de consulta",
                        f"Você tem consulta com {row['nome']} em {row['data']} às {row['hora']}.",
                        external_key=f"reminder:{row['id']}:{user['id']}",
                    )
        else:
            rows = conn.execute(
                """
                SELECT appointments.id, appointments.data, appointments.hora, professionals.nome AS professional_name
                FROM appointments
                JOIN professionals ON professionals.id = appointments.professional_id
                WHERE appointments.user_id = ?
                """,
                (user["id"],),
            ).fetchall()
            for row in rows:
                appointment_dt = datetime.strptime(f"{row['data']} {row['hora']}", "%Y-%m-%d %H:%M")
                if now_utc <= appointment_dt <= limit:
                    create_notification(
                        conn,
                        user["id"],
                        "info",
                        "Lembrete de consulta",
                        f"Lembrete: consulta com {row['professional_name']} em {row['data']} às {row['hora']}.",
                        external_key=f"reminder:{row['id']}:{user['id']}",
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
    stop_event = threading.Event()
    reminder_thread = threading.Thread(
        target=reminder_worker_loop,
        args=(stop_event,),
        daemon=True,
        name="nutrimente-reminders",
    )
    reminder_thread.start()

    server = ThreadingHTTPServer((HOST, PORT), ApiHandler)
    print(f"Nutrimente API ativa em http://{HOST}:{PORT}/api")
    print("Worker de lembretes automáticos ativo a cada 60 segundos.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        server.server_close()
        reminder_thread.join(timeout=1)


if __name__ == "__main__":
    run()


