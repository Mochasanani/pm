"""Pure board-mutation functions. Shared by the HTTP router and the AI agent."""
import sqlite3


class NotFoundError(Exception):
    pass


def load_board(conn: sqlite3.Connection, user_id: int) -> dict:
    columns = conn.execute(
        "SELECT id, title, position FROM columns WHERE user_id = ? ORDER BY position",
        (user_id,),
    ).fetchall()

    result_columns = []
    all_cards: dict[int, dict] = {}
    for col in columns:
        cards = conn.execute(
            "SELECT id, title, details, position FROM cards WHERE column_id = ? ORDER BY position",
            (col["id"],),
        ).fetchall()
        card_ids = []
        for card in cards:
            card_dict = {"id": card["id"], "title": card["title"], "details": card["details"]}
            all_cards[card["id"]] = card_dict
            card_ids.append(card["id"])
        result_columns.append({"id": col["id"], "title": col["title"], "cardIds": card_ids})

    return {"columns": result_columns, "cards": all_cards}


def rename_column(conn: sqlite3.Connection, user_id: int, column_id: int, title: str) -> dict:
    col = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND user_id = ?", (column_id, user_id)
    ).fetchone()
    if not col:
        raise NotFoundError("Column not found")
    conn.execute("UPDATE columns SET title = ? WHERE id = ?", (title, column_id))
    conn.commit()
    return {"id": column_id, "title": title}


def create_card(
    conn: sqlite3.Connection, user_id: int, column_id: int, title: str, details: str
) -> dict:
    col = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND user_id = ?", (column_id, user_id)
    ).fetchone()
    if not col:
        raise NotFoundError("Column not found")

    max_pos = conn.execute(
        "SELECT COALESCE(MAX(position), -1) AS mp FROM cards WHERE column_id = ?",
        (column_id,),
    ).fetchone()["mp"]

    cur = conn.execute(
        "INSERT INTO cards (column_id, title, details, position) VALUES (?, ?, ?, ?)",
        (column_id, title, details, max_pos + 1),
    )
    conn.commit()
    return {"id": cur.lastrowid, "title": title, "details": details}


def update_card(
    conn: sqlite3.Connection,
    user_id: int,
    card_id: int,
    title: str | None,
    details: str | None,
) -> dict:
    card = conn.execute(
        """SELECT cards.id FROM cards
           JOIN columns ON cards.column_id = columns.id
           WHERE cards.id = ? AND columns.user_id = ?""",
        (card_id, user_id),
    ).fetchone()
    if not card:
        raise NotFoundError("Card not found")

    sets: list[str] = []
    params: list = []
    if title is not None:
        sets.append("title = ?")
        params.append(title)
    if details is not None:
        sets.append("details = ?")
        params.append(details)

    if sets:
        params.append(card_id)
        conn.execute(f"UPDATE cards SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()

    row = conn.execute("SELECT id, title, details FROM cards WHERE id = ?", (card_id,)).fetchone()
    return {"id": row["id"], "title": row["title"], "details": row["details"]}


def delete_card(conn: sqlite3.Connection, user_id: int, card_id: int) -> None:
    card = conn.execute(
        """SELECT cards.id, cards.column_id, cards.position FROM cards
           JOIN columns ON cards.column_id = columns.id
           WHERE cards.id = ? AND columns.user_id = ?""",
        (card_id, user_id),
    ).fetchone()
    if not card:
        raise NotFoundError("Card not found")

    conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    conn.execute(
        "UPDATE cards SET position = position - 1 WHERE column_id = ? AND position > ?",
        (card["column_id"], card["position"]),
    )
    conn.commit()


def move_card(
    conn: sqlite3.Connection,
    user_id: int,
    card_id: int,
    column_id: int,
    position: int,
) -> None:
    card = conn.execute(
        """SELECT cards.id, cards.column_id, cards.position FROM cards
           JOIN columns ON cards.column_id = columns.id
           WHERE cards.id = ? AND columns.user_id = ?""",
        (card_id, user_id),
    ).fetchone()
    if not card:
        raise NotFoundError("Card not found")

    target = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND user_id = ?", (column_id, user_id)
    ).fetchone()
    if not target:
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
    conn.commit()
