import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kanban.db"

DEFAULT_BOARD_NAME = "My Board"
DEFAULT_BOARD_DESCRIPTION = "Quarterly planning workspace"

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


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    return row is not None


def migrate_legacy_schema(conn: sqlite3.Connection) -> None:
    """Upgrade pre-boards schemas in place.

    Covers the early iteration where `columns.user_id` existed instead of
    `columns.board_id`, and user/card tables lacked later columns. Idempotent.
    """
    if _table_exists(conn, "users"):
        user_cols = _table_columns(conn, "users")
        if "email" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
        if "password_hash" not in user_cols:
            # Legacy users had no passwords; set a placeholder so the column
            # is NOT NULL-compatible going forward. These accounts can't log
            # in until a password is set via registration/reset.
            conn.execute(
                "ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''"
            )
        if "display_name" not in user_cols:
            conn.execute(
                "ALTER TABLE users ADD COLUMN display_name TEXT NOT NULL DEFAULT ''"
            )
            conn.execute(
                "UPDATE users SET display_name = username WHERE display_name = ''"
            )
        if "created_at" not in user_cols:
            conn.execute(
                "ALTER TABLE users ADD COLUMN created_at TEXT NOT NULL DEFAULT ''"
            )
            conn.execute(
                "UPDATE users SET created_at = datetime('now') WHERE created_at = ''"
            )

    if _table_exists(conn, "columns"):
        col_cols = _table_columns(conn, "columns")
        if "user_id" in col_cols and "board_id" not in col_cols:
            # Create a default board per user, migrate columns, then drop user_id.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS boards (
                    id          INTEGER PRIMARY KEY,
                    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name        TEXT    NOT NULL,
                    description TEXT    NOT NULL DEFAULT '',
                    position    INTEGER NOT NULL DEFAULT 0,
                    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            user_rows = conn.execute("SELECT id FROM users").fetchall()
            user_board: dict[int, int] = {}
            for row in user_rows:
                existing = conn.execute(
                    "SELECT id FROM boards WHERE user_id = ? ORDER BY position, id LIMIT 1",
                    (row["id"],),
                ).fetchone()
                if existing:
                    user_board[row["id"]] = existing["id"]
                    continue
                cur = conn.execute(
                    "INSERT INTO boards (user_id, name, description, position) "
                    "VALUES (?, ?, ?, 0)",
                    (row["id"], DEFAULT_BOARD_NAME, DEFAULT_BOARD_DESCRIPTION),
                )
                assert cur.lastrowid is not None
                user_board[row["id"]] = cur.lastrowid

            # Rebuild columns table with board_id instead of user_id. Disable
            # FK enforcement during the swap so cascading on the dropped table
            # doesn't wipe child `cards` rows. PRAGMA must run outside any
            # pending transaction, so commit first.
            conn.commit()
            conn.execute("PRAGMA foreign_keys=OFF")
            try:
                conn.execute(
                    """
                    CREATE TABLE columns_new (
                        id       INTEGER PRIMARY KEY,
                        board_id INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
                        title    TEXT    NOT NULL,
                        position INTEGER NOT NULL
                    )
                    """
                )
                for row in conn.execute(
                    "SELECT id, user_id, title, position FROM columns"
                ).fetchall():
                    board_id = user_board.get(row["user_id"])
                    if board_id is None:
                        continue
                    conn.execute(
                        "INSERT INTO columns_new (id, board_id, title, position) "
                        "VALUES (?, ?, ?, ?)",
                        (row["id"], board_id, row["title"], row["position"]),
                    )
                conn.execute("DROP TABLE columns")
                conn.execute("ALTER TABLE columns_new RENAME TO columns")
                conn.commit()
            finally:
                conn.execute("PRAGMA foreign_keys=ON")

    if _table_exists(conn, "cards"):
        card_cols = _table_columns(conn, "cards")
        if "created_at" not in card_cols:
            conn.execute(
                "ALTER TABLE cards ADD COLUMN created_at TEXT NOT NULL DEFAULT ''"
            )
            conn.execute(
                "UPDATE cards SET created_at = datetime('now') WHERE created_at = ''"
            )
        if "updated_at" not in card_cols:
            conn.execute(
                "ALTER TABLE cards ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''"
            )
            conn.execute(
                "UPDATE cards SET updated_at = datetime('now') WHERE updated_at = ''"
            )
        if "due_date" not in card_cols:
            conn.execute("ALTER TABLE cards ADD COLUMN due_date TEXT")

    conn.commit()


def init_db(conn: sqlite3.Connection) -> None:
    migrate_legacy_schema(conn)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY,
            username      TEXT    UNIQUE NOT NULL,
            email         TEXT    UNIQUE,
            password_hash TEXT    NOT NULL,
            display_name  TEXT    NOT NULL DEFAULT '',
            created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS boards (
            id          INTEGER PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name        TEXT    NOT NULL,
            description TEXT    NOT NULL DEFAULT '',
            position    INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS columns (
            id       INTEGER PRIMARY KEY,
            board_id INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
            title    TEXT    NOT NULL,
            position INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cards (
            id         INTEGER PRIMARY KEY,
            column_id  INTEGER NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
            title      TEXT    NOT NULL,
            details    TEXT    NOT NULL DEFAULT '',
            due_date   TEXT,
            position   INTEGER NOT NULL,
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS labels (
            id       INTEGER PRIMARY KEY,
            board_id INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
            name     TEXT    NOT NULL,
            color    TEXT    NOT NULL DEFAULT '#888888'
        );
        CREATE TABLE IF NOT EXISTS card_labels (
            card_id  INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
            label_id INTEGER NOT NULL REFERENCES labels(id) ON DELETE CASCADE,
            PRIMARY KEY (card_id, label_id)
        );
        CREATE INDEX IF NOT EXISTS idx_boards_user ON boards(user_id);
        CREATE INDEX IF NOT EXISTS idx_columns_board ON columns(board_id);
        CREATE INDEX IF NOT EXISTS idx_cards_column ON cards(column_id);
        CREATE INDEX IF NOT EXISTS idx_labels_board ON labels(board_id);
        CREATE INDEX IF NOT EXISTS idx_card_labels_card ON card_labels(card_id);
        CREATE INDEX IF NOT EXISTS idx_card_labels_label ON card_labels(label_id);
    """)
    conn.commit()


def seed_board_columns(conn: sqlite3.Connection, board_id: int, with_cards: bool = True) -> None:
    """Seed the default columns (and optionally cards) on a fresh board."""
    existing = conn.execute(
        "SELECT COUNT(*) AS c FROM columns WHERE board_id = ?", (board_id,)
    ).fetchone()
    if existing["c"] > 0:
        return

    col_ids: dict[str, int] = {}
    for title, position in DEFAULT_COLUMNS:
        cur = conn.execute(
            "INSERT INTO columns (board_id, title, position) VALUES (?, ?, ?)",
            (board_id, title, position),
        )
        col_ids[title] = cur.lastrowid  # type: ignore[assignment]

    if with_cards:
        for col_title, card_title, details, position in DEFAULT_CARDS:
            conn.execute(
                "INSERT INTO cards (column_id, title, details, position) VALUES (?, ?, ?, ?)",
                (col_ids[col_title], card_title, details, position),
            )

    conn.commit()


def ensure_default_board(conn: sqlite3.Connection, user_id: int) -> int:
    """Ensure the user has at least one board. Returns the id of their first board."""
    row = conn.execute(
        "SELECT id FROM boards WHERE user_id = ? ORDER BY position, id LIMIT 1",
        (user_id,),
    ).fetchone()
    if row:
        return row["id"]

    cur = conn.execute(
        "INSERT INTO boards (user_id, name, description, position) VALUES (?, ?, ?, 0)",
        (user_id, DEFAULT_BOARD_NAME, DEFAULT_BOARD_DESCRIPTION),
    )
    board_id = cur.lastrowid
    assert board_id is not None
    seed_board_columns(conn, board_id, with_cards=True)
    return board_id
