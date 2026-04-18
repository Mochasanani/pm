"""Tests for the multi-board API under /api/boards."""


def test_list_boards_requires_auth(client):
    resp = client.get("/api/boards")
    assert resp.status_code == 401


def test_list_boards_returns_seeded_default(auth_client):
    resp = auth_client.get("/api/boards")
    assert resp.status_code == 200
    boards = resp.json()
    assert len(boards) == 1
    assert boards[0]["name"]
    assert "created_at" in boards[0]


def test_create_board(auth_client):
    resp = auth_client.post(
        "/api/boards", json={"name": "Personal", "description": "Side quests"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Personal"
    assert body["description"] == "Side quests"

    boards = auth_client.get("/api/boards").json()
    assert len(boards) == 2
    names = [b["name"] for b in boards]
    assert "Personal" in names


def test_create_board_seeds_columns_but_no_cards(auth_client):
    resp = auth_client.post("/api/boards", json={"name": "Fresh"})
    board_id = resp.json()["id"]

    full = auth_client.get(f"/api/boards/{board_id}").json()
    assert len(full["columns"]) == 5
    assert full["cards"] == {}


def test_create_board_rejects_empty_name(auth_client):
    resp = auth_client.post("/api/boards", json={"name": ""})
    assert resp.status_code == 422


def test_get_board(auth_client):
    boards = auth_client.get("/api/boards").json()
    board_id = boards[0]["id"]
    resp = auth_client.get(f"/api/boards/{board_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["board"]["id"] == board_id
    assert len(body["columns"]) == 5
    assert len(body["cards"]) == 8


def test_get_missing_board(auth_client):
    assert auth_client.get("/api/boards/99999").status_code == 404


def test_rename_board(auth_client):
    boards = auth_client.get("/api/boards").json()
    board_id = boards[0]["id"]
    resp = auth_client.put(
        f"/api/boards/{board_id}",
        json={"name": "Renamed", "description": "Updated"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"
    assert resp.json()["description"] == "Updated"


def test_rename_board_missing(auth_client):
    resp = auth_client.put("/api/boards/99999", json={"name": "x"})
    assert resp.status_code == 404


def test_delete_board_removes_cascade(auth_client):
    created = auth_client.post("/api/boards", json={"name": "Disposable"}).json()
    board_id = created["id"]

    # Add a card
    full = auth_client.get(f"/api/boards/{board_id}").json()
    col_id = full["columns"][0]["id"]
    auth_client.post(
        f"/api/boards/{board_id}/cards",
        json={"column_id": col_id, "title": "temp"},
    )

    resp = auth_client.delete(f"/api/boards/{board_id}")
    assert resp.status_code == 200

    # Gone from list
    ids = [b["id"] for b in auth_client.get("/api/boards").json()]
    assert board_id not in ids

    # 404 when read
    assert auth_client.get(f"/api/boards/{board_id}").status_code == 404


def test_delete_missing_board(auth_client):
    assert auth_client.delete("/api/boards/99999").status_code == 404


def test_cannot_access_other_users_board(client):
    # Register alice
    client.post(
        "/api/register", json={"username": "alice", "password": "secretpass"}
    )
    alice_board = client.post("/api/boards", json={"name": "Alice"}).json()

    # Log in as default user
    client.cookies.clear()
    client.post("/api/login", json={"username": "user", "password": "password"})

    assert client.get(f"/api/boards/{alice_board['id']}").status_code == 404
    assert client.put(
        f"/api/boards/{alice_board['id']}", json={"name": "Hax"}
    ).status_code == 404
    assert client.delete(f"/api/boards/{alice_board['id']}").status_code == 404


# ---------- Scoped column/card operations ----------

def test_scoped_rename_column(auth_client):
    boards = auth_client.get("/api/boards").json()
    board_id = boards[0]["id"]
    full = auth_client.get(f"/api/boards/{board_id}").json()
    col_id = full["columns"][0]["id"]

    resp = auth_client.put(
        f"/api/boards/{board_id}/columns/{col_id}", json={"title": "Todo"}
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Todo"


def test_scoped_create_and_delete_card(auth_client):
    boards = auth_client.get("/api/boards").json()
    board_id = boards[0]["id"]
    full = auth_client.get(f"/api/boards/{board_id}").json()
    col_id = full["columns"][0]["id"]

    created = auth_client.post(
        f"/api/boards/{board_id}/cards",
        json={"column_id": col_id, "title": "Scoped card"},
    )
    assert created.status_code == 200
    card_id = created.json()["id"]

    full = auth_client.get(f"/api/boards/{board_id}").json()
    assert card_id in full["columns"][0]["cardIds"]

    # Delete
    resp = auth_client.delete(f"/api/boards/{board_id}/cards/{card_id}")
    assert resp.status_code == 200


def test_scoped_update_and_move_card(auth_client):
    boards = auth_client.get("/api/boards").json()
    board_id = boards[0]["id"]
    full = auth_client.get(f"/api/boards/{board_id}").json()
    card_id = full["columns"][0]["cardIds"][0]
    target_col = full["columns"][2]["id"]

    upd = auth_client.put(
        f"/api/boards/{board_id}/cards/{card_id}",
        json={"title": "Edited"},
    )
    assert upd.status_code == 200
    assert upd.json()["title"] == "Edited"

    mv = auth_client.put(
        f"/api/boards/{board_id}/cards/{card_id}/move",
        json={"column_id": target_col, "position": 0},
    )
    assert mv.status_code == 200

    full = auth_client.get(f"/api/boards/{board_id}").json()
    assert card_id in full["columns"][2]["cardIds"]


def test_scoped_ops_reject_cross_board_ids(auth_client):
    first = auth_client.get("/api/boards").json()[0]["id"]
    other = auth_client.post("/api/boards", json={"name": "Other"}).json()["id"]

    first_full = auth_client.get(f"/api/boards/{first}").json()
    first_card = first_full["columns"][0]["cardIds"][0]
    first_col = first_full["columns"][0]["id"]

    # Using a card from the first board against the other board should 404
    assert auth_client.put(
        f"/api/boards/{other}/cards/{first_card}", json={"title": "x"}
    ).status_code == 404
    assert auth_client.delete(
        f"/api/boards/{other}/cards/{first_card}"
    ).status_code == 404
    assert auth_client.put(
        f"/api/boards/{other}/columns/{first_col}", json={"title": "x"}
    ).status_code == 404


def test_full_multi_board_crud_cycle(auth_client):
    """Integration: create a board, add/update/move/delete cards, delete board."""
    created = auth_client.post(
        "/api/boards", json={"name": "Lifecycle"}
    ).json()
    board_id = created["id"]
    full = auth_client.get(f"/api/boards/{board_id}").json()
    col_a = full["columns"][0]["id"]
    col_b = full["columns"][1]["id"]

    # Create
    card = auth_client.post(
        f"/api/boards/{board_id}/cards",
        json={"column_id": col_a, "title": "c1"},
    ).json()

    # Update
    auth_client.put(
        f"/api/boards/{board_id}/cards/{card['id']}", json={"details": "Edited"}
    )

    # Move
    auth_client.put(
        f"/api/boards/{board_id}/cards/{card['id']}/move",
        json={"column_id": col_b, "position": 0},
    )
    full = auth_client.get(f"/api/boards/{board_id}").json()
    assert card["id"] in full["columns"][1]["cardIds"]

    # Delete
    auth_client.delete(f"/api/boards/{board_id}/cards/{card['id']}")
    full = auth_client.get(f"/api/boards/{board_id}").json()
    assert card["id"] not in full["columns"][1]["cardIds"]

    # Tear down board
    auth_client.delete(f"/api/boards/{board_id}")


# ---------------- Card due dates ----------------

def _first_column(auth_client, board_id: int) -> int:
    full = auth_client.get(f"/api/boards/{board_id}").json()
    return full["columns"][0]["id"]


def test_create_card_with_due_date(auth_client):
    board_id = auth_client.get("/api/boards").json()[0]["id"]
    col_id = _first_column(auth_client, board_id)

    resp = auth_client.post(
        f"/api/boards/{board_id}/cards",
        json={"column_id": col_id, "title": "Plan", "due_date": "2026-06-01"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["due_date"] == "2026-06-01"

    full = auth_client.get(f"/api/boards/{board_id}").json()
    assert full["cards"][str(body["id"])]["due_date"] == "2026-06-01"


def test_create_card_rejects_bad_due_date(auth_client):
    board_id = auth_client.get("/api/boards").json()[0]["id"]
    col_id = _first_column(auth_client, board_id)
    resp = auth_client.post(
        f"/api/boards/{board_id}/cards",
        json={"column_id": col_id, "title": "Plan", "due_date": "next-tuesday"},
    )
    assert resp.status_code == 422


def test_update_card_sets_and_clears_due_date(auth_client):
    board_id = auth_client.get("/api/boards").json()[0]["id"]
    col_id = _first_column(auth_client, board_id)
    card_id = auth_client.post(
        f"/api/boards/{board_id}/cards",
        json={"column_id": col_id, "title": "c"},
    ).json()["id"]

    # Set a due date.
    resp = auth_client.put(
        f"/api/boards/{board_id}/cards/{card_id}",
        json={"due_date": "2026-07-15"},
    )
    assert resp.status_code == 200
    assert resp.json()["due_date"] == "2026-07-15"

    # Clear it via explicit null (field present in body).
    resp = auth_client.put(
        f"/api/boards/{board_id}/cards/{card_id}",
        json={"due_date": None},
    )
    assert resp.status_code == 200
    assert resp.json()["due_date"] is None


def test_update_card_leaves_due_date_untouched_when_omitted(auth_client):
    board_id = auth_client.get("/api/boards").json()[0]["id"]
    col_id = _first_column(auth_client, board_id)
    card_id = auth_client.post(
        f"/api/boards/{board_id}/cards",
        json={"column_id": col_id, "title": "c", "due_date": "2026-08-01"},
    ).json()["id"]

    # Update only the title — due_date must be preserved.
    resp = auth_client.put(
        f"/api/boards/{board_id}/cards/{card_id}",
        json={"title": "renamed"},
    )
    assert resp.status_code == 200
    assert resp.json()["due_date"] == "2026-08-01"
    assert resp.json()["title"] == "renamed"


# ---------------- Labels ----------------

def _first_card(auth_client, board_id: int) -> int:
    full = auth_client.get(f"/api/boards/{board_id}").json()
    return full["columns"][0]["cardIds"][0]


def test_labels_start_empty(auth_client):
    board_id = auth_client.get("/api/boards").json()[0]["id"]
    resp = auth_client.get(f"/api/boards/{board_id}/labels")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_label(auth_client):
    board_id = auth_client.get("/api/boards").json()[0]["id"]
    resp = auth_client.post(
        f"/api/boards/{board_id}/labels",
        json={"name": "Urgent", "color": "#ff3344"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Urgent"
    assert body["color"] == "#ff3344"

    listed = auth_client.get(f"/api/boards/{board_id}/labels").json()
    assert len(listed) == 1
    assert listed[0]["id"] == body["id"]


def test_create_label_rejects_bad_color(auth_client):
    board_id = auth_client.get("/api/boards").json()[0]["id"]
    resp = auth_client.post(
        f"/api/boards/{board_id}/labels",
        json={"name": "Bad", "color": "red"},
    )
    assert resp.status_code == 422


def test_update_label(auth_client):
    board_id = auth_client.get("/api/boards").json()[0]["id"]
    label_id = auth_client.post(
        f"/api/boards/{board_id}/labels",
        json={"name": "Old", "color": "#111111"},
    ).json()["id"]

    resp = auth_client.put(
        f"/api/boards/{board_id}/labels/{label_id}",
        json={"name": "New", "color": "#aaaaaa"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"
    assert resp.json()["color"] == "#aaaaaa"


def test_delete_label_removes_assignments(auth_client):
    board_id = auth_client.get("/api/boards").json()[0]["id"]
    card_id = _first_card(auth_client, board_id)
    label_id = auth_client.post(
        f"/api/boards/{board_id}/labels",
        json={"name": "Tag"},
    ).json()["id"]

    # Assign
    auth_client.put(
        f"/api/boards/{board_id}/cards/{card_id}/labels",
        json={"label_ids": [label_id]},
    )
    full = auth_client.get(f"/api/boards/{board_id}").json()
    assert full["cards"][str(card_id)]["label_ids"] == [label_id]

    # Delete the label
    resp = auth_client.delete(f"/api/boards/{board_id}/labels/{label_id}")
    assert resp.status_code == 200

    full = auth_client.get(f"/api/boards/{board_id}").json()
    assert full["cards"][str(card_id)]["label_ids"] == []
    assert full["labels"] == []


def test_set_card_labels_round_trip(auth_client):
    board_id = auth_client.get("/api/boards").json()[0]["id"]
    card_id = _first_card(auth_client, board_id)

    a = auth_client.post(
        f"/api/boards/{board_id}/labels", json={"name": "A", "color": "#aaaaaa"}
    ).json()["id"]
    b = auth_client.post(
        f"/api/boards/{board_id}/labels", json={"name": "B", "color": "#bbbbbb"}
    ).json()["id"]

    resp = auth_client.put(
        f"/api/boards/{board_id}/cards/{card_id}/labels",
        json={"label_ids": [a, b]},
    )
    assert resp.status_code == 200
    assert sorted(resp.json()["label_ids"]) == sorted([a, b])

    full = auth_client.get(f"/api/boards/{board_id}").json()
    assert sorted(full["cards"][str(card_id)]["label_ids"]) == sorted([a, b])
    assert len(full["labels"]) == 2

    # Clearing replaces the set.
    auth_client.put(
        f"/api/boards/{board_id}/cards/{card_id}/labels",
        json={"label_ids": []},
    )
    full = auth_client.get(f"/api/boards/{board_id}").json()
    assert full["cards"][str(card_id)]["label_ids"] == []


def test_set_card_labels_rejects_cross_board_label(auth_client):
    b1 = auth_client.get("/api/boards").json()[0]["id"]
    b2 = auth_client.post("/api/boards", json={"name": "Other"}).json()["id"]
    card_id = _first_card(auth_client, b1)

    foreign_label = auth_client.post(
        f"/api/boards/{b2}/labels", json={"name": "Alien"}
    ).json()["id"]

    resp = auth_client.put(
        f"/api/boards/{b1}/cards/{card_id}/labels",
        json={"label_ids": [foreign_label]},
    )
    assert resp.status_code == 404


def test_update_missing_label(auth_client):
    board_id = auth_client.get("/api/boards").json()[0]["id"]
    resp = auth_client.put(
        f"/api/boards/{board_id}/labels/99999", json={"name": "Ghost"}
    )
    assert resp.status_code == 404
