"""Pure board-mutation functions. Shared by the HTTP router and the AI agent."""
import sqlite3


class NotFoundError(Exception):
    pass


# Sentinel marking an optional field that was not provided. Lets us distinguish
# "client wants to clear this to null" (value=None) from "client didn't send
# this field" (value=_UNSET) on partial updates.
class _Unset:
    def __repr__(self) -> str:
        return "<UNSET>"


UNSET = _Unset()


# ---------------- Board lookup helpers ----------------

def get_user_board(conn: sqlite3.Connection, user_id: int, board_id: int) -> dict | None:
    row = conn.execute(
        "SELECT id, user_id, name, description, position, created_at, updated_at "
        "FROM boards WHERE id = ? AND user_id = ?",
        (board_id, user_id),
    ).fetchone()
    return dict(row) if row else None


def list_user_boards(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id, name, description, position, created_at, updated_at "
        "FROM boards WHERE user_id = ? ORDER BY position, id",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def create_board(
    conn: sqlite3.Connection, user_id: int, name: str, description: str = ""
) -> dict:
    pos_row = conn.execute(
        "SELECT COALESCE(MAX(position), -1) AS mp FROM boards WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    position = pos_row["mp"] + 1
    cur = conn.execute(
        "INSERT INTO boards (user_id, name, description, position) VALUES (?, ?, ?, ?)",
        (user_id, name, description, position),
    )
    conn.commit()
    board_id = cur.lastrowid
    assert board_id is not None
    from app.db import seed_board_columns
    seed_board_columns(conn, board_id, with_cards=False)
    return get_user_board(conn, user_id, board_id)  # type: ignore[return-value]


def update_board(
    conn: sqlite3.Connection,
    user_id: int,
    board_id: int,
    name: str | None,
    description: str | None,
) -> dict:
    board = get_user_board(conn, user_id, board_id)
    if not board:
        raise NotFoundError("Board not found")
    sets: list[str] = []
    params: list = []
    if name is not None:
        sets.append("name = ?")
        params.append(name)
    if description is not None:
        sets.append("description = ?")
        params.append(description)
    if sets:
        sets.append("updated_at = datetime('now')")
        params.append(board_id)
        conn.execute(f"UPDATE boards SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()
    return get_user_board(conn, user_id, board_id)  # type: ignore[return-value]


def delete_board(conn: sqlite3.Connection, user_id: int, board_id: int) -> None:
    board = get_user_board(conn, user_id, board_id)
    if not board:
        raise NotFoundError("Board not found")
    # Explicit cascade to keep working even if PRAGMA foreign_keys isn't set.
    conn.execute(
        "DELETE FROM cards WHERE column_id IN (SELECT id FROM columns WHERE board_id = ?)",
        (board_id,),
    )
    conn.execute("DELETE FROM columns WHERE board_id = ?", (board_id,))
    conn.execute("DELETE FROM boards WHERE id = ?", (board_id,))
    conn.commit()


# ---------------- Full board payload ----------------

def load_board(conn: sqlite3.Connection, board_id: int) -> dict:
    columns = conn.execute(
        "SELECT id, title, position FROM columns WHERE board_id = ? ORDER BY position",
        (board_id,),
    ).fetchall()

    # Preload all label assignments for this board in one query.
    label_rows = conn.execute(
        """
        SELECT cl.card_id, cl.label_id
        FROM card_labels cl
        JOIN cards c ON c.id = cl.card_id
        JOIN columns co ON co.id = c.column_id
        WHERE co.board_id = ?
        """,
        (board_id,),
    ).fetchall()
    labels_by_card: dict[int, list[int]] = {}
    for row in label_rows:
        labels_by_card.setdefault(row["card_id"], []).append(row["label_id"])

    result_columns = []
    all_cards: dict[int, dict] = {}
    for col in columns:
        cards = conn.execute(
            "SELECT id, title, details, due_date, position FROM cards WHERE column_id = ? ORDER BY position",
            (col["id"],),
        ).fetchall()
        card_ids = []
        for card in cards:
            card_dict = {
                "id": card["id"],
                "title": card["title"],
                "details": card["details"],
                "due_date": card["due_date"],
                "label_ids": sorted(labels_by_card.get(card["id"], [])),
            }
            all_cards[card["id"]] = card_dict
            card_ids.append(card["id"])
        result_columns.append({"id": col["id"], "title": col["title"], "cardIds": card_ids})

    labels = list_labels(conn, board_id)
    return {"columns": result_columns, "cards": all_cards, "labels": labels}


# ---------------- Labels ----------------

def list_labels(conn: sqlite3.Connection, board_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id, name, color FROM labels WHERE board_id = ? ORDER BY id",
        (board_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def create_label(
    conn: sqlite3.Connection, board_id: int, name: str, color: str
) -> dict:
    cur = conn.execute(
        "INSERT INTO labels (board_id, name, color) VALUES (?, ?, ?)",
        (board_id, name, color),
    )
    _touch_board(conn, board_id)
    conn.commit()
    return {"id": cur.lastrowid, "name": name, "color": color}


def update_label(
    conn: sqlite3.Connection,
    board_id: int,
    label_id: int,
    name: str | None,
    color: str | None,
) -> dict:
    row = conn.execute(
        "SELECT id FROM labels WHERE id = ? AND board_id = ?", (label_id, board_id)
    ).fetchone()
    if not row:
        raise NotFoundError("Label not found")

    sets: list[str] = []
    params: list = []
    if name is not None:
        sets.append("name = ?")
        params.append(name)
    if color is not None:
        sets.append("color = ?")
        params.append(color)
    if sets:
        params.append(label_id)
        conn.execute(f"UPDATE labels SET {', '.join(sets)} WHERE id = ?", params)
        _touch_board(conn, board_id)
        conn.commit()

    updated = conn.execute(
        "SELECT id, name, color FROM labels WHERE id = ?", (label_id,)
    ).fetchone()
    return dict(updated)


def delete_label(conn: sqlite3.Connection, board_id: int, label_id: int) -> None:
    row = conn.execute(
        "SELECT id FROM labels WHERE id = ? AND board_id = ?", (label_id, board_id)
    ).fetchone()
    if not row:
        raise NotFoundError("Label not found")
    conn.execute("DELETE FROM card_labels WHERE label_id = ?", (label_id,))
    conn.execute("DELETE FROM labels WHERE id = ?", (label_id,))
    _touch_board(conn, board_id)
    conn.commit()


def set_card_labels(
    conn: sqlite3.Connection,
    board_id: int,
    card_id: int,
    label_ids: list[int],
) -> list[int]:
    if not _card_for_board(conn, board_id, card_id):
        raise NotFoundError("Card not found")

    # Validate each label id belongs to this board.
    unique_ids = list(dict.fromkeys(label_ids))  # de-dupe, preserve order
    if unique_ids:
        rows = conn.execute(
            f"SELECT id FROM labels WHERE board_id = ? AND id IN "
            f"({','.join('?' * len(unique_ids))})",
            (board_id, *unique_ids),
        ).fetchall()
        found = {r["id"] for r in rows}
        if found != set(unique_ids):
            raise NotFoundError("One or more labels do not belong to this board")

    conn.execute("DELETE FROM card_labels WHERE card_id = ?", (card_id,))
    for lid in unique_ids:
        conn.execute(
            "INSERT INTO card_labels (card_id, label_id) VALUES (?, ?)",
            (card_id, lid),
        )
    _touch_board(conn, board_id)
    conn.commit()
    return sorted(unique_ids)


# ---------------- Mutation helpers (board-scoped) ----------------

def _column_for_board(conn: sqlite3.Connection, board_id: int, column_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id FROM columns WHERE id = ? AND board_id = ?",
        (column_id, board_id),
    ).fetchone()


def _card_for_board(conn: sqlite3.Connection, board_id: int, card_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """SELECT cards.id, cards.column_id, cards.position
           FROM cards
           JOIN columns ON cards.column_id = columns.id
           WHERE cards.id = ? AND columns.board_id = ?""",
        (card_id, board_id),
    ).fetchone()


def _touch_board(conn: sqlite3.Connection, board_id: int) -> None:
    conn.execute(
        "UPDATE boards SET updated_at = datetime('now') WHERE id = ?",
        (board_id,),
    )


def rename_column(
    conn: sqlite3.Connection, board_id: int, column_id: int, title: str
) -> dict:
    if not _column_for_board(conn, board_id, column_id):
        raise NotFoundError("Column not found")
    conn.execute("UPDATE columns SET title = ? WHERE id = ?", (title, column_id))
    _touch_board(conn, board_id)
    conn.commit()
    return {"id": column_id, "title": title}


def create_card(
    conn: sqlite3.Connection,
    board_id: int,
    column_id: int,
    title: str,
    details: str,
    due_date: str | None = None,
) -> dict:
    if not _column_for_board(conn, board_id, column_id):
        raise NotFoundError("Column not found")

    max_pos = conn.execute(
        "SELECT COALESCE(MAX(position), -1) AS mp FROM cards WHERE column_id = ?",
        (column_id,),
    ).fetchone()["mp"]

    cur = conn.execute(
        "INSERT INTO cards (column_id, title, details, due_date, position) VALUES (?, ?, ?, ?, ?)",
        (column_id, title, details, due_date, max_pos + 1),
    )
    _touch_board(conn, board_id)
    conn.commit()
    return {
        "id": cur.lastrowid,
        "title": title,
        "details": details,
        "due_date": due_date,
    }


def update_card(
    conn: sqlite3.Connection,
    board_id: int,
    card_id: int,
    title: str | None,
    details: str | None,
    due_date: str | None | _Unset = UNSET,
) -> dict:
    if not _card_for_board(conn, board_id, card_id):
        raise NotFoundError("Card not found")

    sets: list[str] = []
    params: list = []
    if title is not None:
        sets.append("title = ?")
        params.append(title)
    if details is not None:
        sets.append("details = ?")
        params.append(details)
    if not isinstance(due_date, _Unset):
        sets.append("due_date = ?")
        params.append(due_date)

    if sets:
        sets.append("updated_at = datetime('now')")
        params.append(card_id)
        conn.execute(f"UPDATE cards SET {', '.join(sets)} WHERE id = ?", params)
        _touch_board(conn, board_id)
        conn.commit()

    row = conn.execute(
        "SELECT id, title, details, due_date FROM cards WHERE id = ?", (card_id,)
    ).fetchone()
    return {
        "id": row["id"],
        "title": row["title"],
        "details": row["details"],
        "due_date": row["due_date"],
    }


def delete_card(conn: sqlite3.Connection, board_id: int, card_id: int) -> None:
    card = _card_for_board(conn, board_id, card_id)
    if not card:
        raise NotFoundError("Card not found")

    conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    conn.execute(
        "UPDATE cards SET position = position - 1 WHERE column_id = ? AND position > ?",
        (card["column_id"], card["position"]),
    )
    _touch_board(conn, board_id)
    conn.commit()


def move_card(
    conn: sqlite3.Connection,
    board_id: int,
    card_id: int,
    column_id: int,
    position: int,
) -> None:
    card = _card_for_board(conn, board_id, card_id)
    if not card:
        raise NotFoundError("Card not found")

    if not _column_for_board(conn, board_id, column_id):
        raise NotFoundError("Target column not found")

    conn.execute(
        "UPDATE cards SET position = position - 1 WHERE column_id = ? AND position > ?",
        (card["column_id"], card["position"]),
    )
    conn.execute(
        "UPDATE cards SET position = position + 1 WHERE column_id = ? AND position >= ?",
        (column_id, position),
    )
    conn.execute(
        "UPDATE cards SET column_id = ?, position = ? WHERE id = ?",
        (column_id, position, card_id),
    )
    _touch_board(conn, board_id)
    conn.commit()
