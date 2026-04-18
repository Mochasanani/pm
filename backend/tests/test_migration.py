"""Tests for in-place schema migration from pre-boards layouts."""
import sqlite3

from app.db import init_db, migrate_legacy_schema


def _legacy_schema(conn: sqlite3.Connection) -> None:
    """Recreate the early iteration of the schema (no boards, user-owned columns)."""
    conn.executescript(
        """
        CREATE TABLE users (
            id       INTEGER PRIMARY KEY,
            username TEXT    UNIQUE NOT NULL
        );
        CREATE TABLE columns (
            id       INTEGER PRIMARY KEY,
            user_id  INTEGER NOT NULL REFERENCES users(id),
            title    TEXT    NOT NULL,
            position INTEGER NOT NULL
        );
        CREATE TABLE cards (
            id        INTEGER PRIMARY KEY,
            column_id INTEGER NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
            title     TEXT    NOT NULL,
            details   TEXT    NOT NULL DEFAULT '',
            position  INTEGER NOT NULL
        );
        """
    )
    conn.commit()


def _seed_legacy_rows(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO users (username) VALUES ('alice')")
    conn.execute("INSERT INTO users (username) VALUES ('bob')")
    conn.execute(
        "INSERT INTO columns (id, user_id, title, position) VALUES (10, 1, 'Todo', 0)"
    )
    conn.execute(
        "INSERT INTO columns (id, user_id, title, position) VALUES (11, 1, 'Done', 1)"
    )
    conn.execute(
        "INSERT INTO columns (id, user_id, title, position) VALUES (20, 2, 'Inbox', 0)"
    )
    conn.execute(
        "INSERT INTO cards (column_id, title, details, position) VALUES (10, 'c1', 'd', 0)"
    )
    conn.execute(
        "INSERT INTO cards (column_id, title, details, position) VALUES (11, 'c2', '', 0)"
    )
    conn.execute(
        "INSERT INTO cards (column_id, title, details, position) VALUES (20, 'c3', '', 0)"
    )
    conn.commit()


def _open(tmp_path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def test_migration_creates_boards_and_preserves_cards(tmp_path):
    conn = _open(tmp_path)
    _legacy_schema(conn)
    _seed_legacy_rows(conn)

    migrate_legacy_schema(conn)

    board_rows = conn.execute("SELECT user_id FROM boards ORDER BY user_id").fetchall()
    assert [r["user_id"] for r in board_rows] == [1, 2]

    col_info = {row["name"] for row in conn.execute("PRAGMA table_info(columns)")}
    assert "board_id" in col_info and "user_id" not in col_info

    alice_board = conn.execute("SELECT id FROM boards WHERE user_id = 1").fetchone()["id"]
    alice_cols = conn.execute(
        "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position",
        (alice_board,),
    ).fetchall()
    assert [(r["id"], r["title"]) for r in alice_cols] == [(10, "Todo"), (11, "Done")]

    card_titles = {
        r["title"]
        for r in conn.execute(
            "SELECT title FROM cards WHERE column_id IN (10, 11)"
        ).fetchall()
    }
    assert card_titles == {"c1", "c2"}


def test_init_db_is_idempotent_on_legacy(tmp_path):
    conn = _open(tmp_path)
    _legacy_schema(conn)
    _seed_legacy_rows(conn)

    init_db(conn)
    init_db(conn)

    user_cols = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    for expected in ("email", "password_hash", "display_name", "created_at"):
        assert expected in user_cols

    card_cols = {row["name"] for row in conn.execute("PRAGMA table_info(cards)")}
    for expected in ("created_at", "updated_at"):
        assert expected in card_cols


def test_migration_no_op_on_fresh_db(tmp_path):
    conn = _open(tmp_path)
    init_db(conn)
    # Re-running migrate must not break the fresh schema.
    migrate_legacy_schema(conn)
    init_db(conn)

    col_info = {row["name"] for row in conn.execute("PRAGMA table_info(columns)")}
    assert "board_id" in col_info
