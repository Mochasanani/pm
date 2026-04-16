import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kanban.db"

DEFAULT_COLUMNS = [
    ("Backlog", 0),
    ("Discovery", 1),
    ("In Progress", 2),
    ("Review", 3),
    ("Done", 4),
]

DEFAULT_CARDS: list[tuple[str, str, str, int]] = [
    ("Backlog", "Align roadmap themes", "Draft quarterly themes with impact statements and metrics.", 0),
    ("Backlog", "Gather customer signals", "Review support tags, sales notes, and churn feedback.", 1),
    ("Discovery", "Prototype analytics view", "Sketch initial dashboard layout and key drill-downs.", 0),
    ("In Progress", "Refine status language", "Standardize column labels and tone across the board.", 0),
    ("In Progress", "Design card layout", "Add hierarchy and spacing for scanning dense lists.", 1),
    ("Review", "QA micro-interactions", "Verify hover, focus, and loading states.", 0),
    ("Done", "Ship marketing page", "Final copy approved and asset pack delivered.", 0),
    ("Done", "Close onboarding sprint", "Document release notes and share internally.", 1),
]


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def db_conn():
    """FastAPI dependency: yields a connection and closes it after the request."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY,
            username TEXT    UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS columns (
            id       INTEGER PRIMARY KEY,
            user_id  INTEGER NOT NULL REFERENCES users(id),
            title    TEXT    NOT NULL,
            position INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cards (
            id        INTEGER PRIMARY KEY,
            column_id INTEGER NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
            title     TEXT    NOT NULL,
            details   TEXT    NOT NULL DEFAULT '',
            position  INTEGER NOT NULL
        );
    """)


def ensure_user(conn: sqlite3.Connection, username: str) -> int:
    """Get or create a user, returning the user id."""
    row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO users (username) VALUES (?)", (username,))
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def seed_board(conn: sqlite3.Connection, user_id: int) -> None:
    """Seed the default board if the user has no columns."""
    existing = conn.execute("SELECT COUNT(*) as c FROM columns WHERE user_id = ?", (user_id,)).fetchone()
    if existing["c"] > 0:
        return

    # Insert columns
    col_ids: dict[str, int] = {}
    for title, position in DEFAULT_COLUMNS:
        cur = conn.execute(
            "INSERT INTO columns (user_id, title, position) VALUES (?, ?, ?)",
            (user_id, title, position),
        )
        col_ids[title] = cur.lastrowid  # type: ignore[assignment]

    # Insert cards
    for col_title, card_title, details, position in DEFAULT_CARDS:
        conn.execute(
            "INSERT INTO cards (column_id, title, details, position) VALUES (?, ?, ?, ?)",
            (col_ids[col_title], card_title, details, position),
        )

    conn.commit()
