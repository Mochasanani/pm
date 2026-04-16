def test_get_board_unauthenticated(client):
    resp = client.get("/api/board")
    assert resp.status_code == 401


def test_get_board_returns_seeded_data(auth_client):
    resp = auth_client.get("/api/board")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["columns"]) == 5
    assert len(data["cards"]) == 8
    assert data["columns"][0]["title"] == "Backlog"
    assert len(data["columns"][0]["cardIds"]) == 2


def test_rename_column(auth_client):
    board = auth_client.get("/api/board").json()
    col_id = board["columns"][0]["id"]

    resp = auth_client.put(f"/api/board/columns/{col_id}", json={"title": "Todo"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Todo"

    # Verify persisted
    board = auth_client.get("/api/board").json()
    assert board["columns"][0]["title"] == "Todo"


def test_rename_column_unauthenticated(client):
    resp = client.put("/api/board/columns/1", json={"title": "Todo"})
    assert resp.status_code == 401


def test_create_card(auth_client):
    board = auth_client.get("/api/board").json()
    col_id = board["columns"][0]["id"]
    initial_count = len(board["columns"][0]["cardIds"])

    resp = auth_client.post("/api/board/cards", json={
        "column_id": col_id, "title": "New card", "details": "Some details"
    })
    assert resp.status_code == 200
    assert resp.json()["title"] == "New card"

    board = auth_client.get("/api/board").json()
    assert len(board["columns"][0]["cardIds"]) == initial_count + 1


def test_update_card(auth_client):
    board = auth_client.get("/api/board").json()
    card_id = board["columns"][0]["cardIds"][0]

    resp = auth_client.put(f"/api/board/cards/{card_id}", json={"title": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated"


def test_delete_card(auth_client):
    board = auth_client.get("/api/board").json()
    col_id = board["columns"][0]["id"]
    card_id = board["columns"][0]["cardIds"][0]
    initial_count = len(board["columns"][0]["cardIds"])

    resp = auth_client.delete(f"/api/board/cards/{card_id}")
    assert resp.status_code == 200

    board = auth_client.get("/api/board").json()
    assert len(board["columns"][0]["cardIds"]) == initial_count - 1
    assert card_id not in board["columns"][0]["cardIds"]


def test_move_card_between_columns(auth_client):
    board = auth_client.get("/api/board").json()
    card_id = board["columns"][0]["cardIds"][0]
    target_col_id = board["columns"][1]["id"]

    resp = auth_client.put(f"/api/board/cards/{card_id}/move", json={
        "column_id": target_col_id, "position": 0
    })
    assert resp.status_code == 200

    board = auth_client.get("/api/board").json()
    assert card_id not in board["columns"][0]["cardIds"]
    assert card_id in board["columns"][1]["cardIds"]


def test_rename_column_rejects_empty_title(auth_client):
    board = auth_client.get("/api/board").json()
    col_id = board["columns"][0]["id"]
    resp = auth_client.put(f"/api/board/columns/{col_id}", json={"title": ""})
    assert resp.status_code == 422


def test_create_card_rejects_empty_title(auth_client):
    board = auth_client.get("/api/board").json()
    col_id = board["columns"][0]["id"]
    resp = auth_client.post(
        "/api/board/cards", json={"column_id": col_id, "title": "", "details": "x"}
    )
    assert resp.status_code == 422


def test_create_card_empty_details_stays_empty(auth_client):
    """Empty details should persist as '' (no 'No details yet.' substitution)."""
    board = auth_client.get("/api/board").json()
    col_id = board["columns"][0]["id"]
    resp = auth_client.post(
        "/api/board/cards", json={"column_id": col_id, "title": "Blank"}
    )
    assert resp.status_code == 200
    assert resp.json()["details"] == ""


def test_move_card_rejects_negative_position(auth_client):
    board = auth_client.get("/api/board").json()
    card_id = board["columns"][0]["cardIds"][0]
    target_col = board["columns"][1]["id"]
    resp = auth_client.put(
        f"/api/board/cards/{card_id}/move",
        json={"column_id": target_col, "position": -1},
    )
    assert resp.status_code == 422


def test_move_card_to_missing_column(auth_client):
    board = auth_client.get("/api/board").json()
    card_id = board["columns"][0]["cardIds"][0]
    resp = auth_client.put(
        f"/api/board/cards/{card_id}/move",
        json={"column_id": 99999, "position": 0},
    )
    assert resp.status_code == 404


def test_update_missing_card_returns_404(auth_client):
    resp = auth_client.put("/api/board/cards/99999", json={"title": "x"})
    assert resp.status_code == 404


def test_delete_missing_card_returns_404(auth_client):
    resp = auth_client.delete("/api/board/cards/99999")
    assert resp.status_code == 404


def test_full_crud_cycle(auth_client):
    """Integration test: create, read, update, move, delete."""
    board = auth_client.get("/api/board").json()
    col_id = board["columns"][0]["id"]
    target_col_id = board["columns"][2]["id"]

    # Create
    resp = auth_client.post("/api/board/cards", json={
        "column_id": col_id, "title": "CRUD card", "details": "Testing"
    })
    card_id = resp.json()["id"]

    # Read
    board = auth_client.get("/api/board").json()
    assert card_id in board["columns"][0]["cardIds"]

    # Update
    auth_client.put(f"/api/board/cards/{card_id}", json={"title": "Updated CRUD"})
    board = auth_client.get("/api/board").json()
    assert board["cards"][str(card_id)]["title"] == "Updated CRUD"

    # Move
    auth_client.put(f"/api/board/cards/{card_id}/move", json={
        "column_id": target_col_id, "position": 0
    })
    board = auth_client.get("/api/board").json()
    assert card_id in board["columns"][2]["cardIds"]

    # Delete
    auth_client.delete(f"/api/board/cards/{card_id}")
    board = auth_client.get("/api/board").json()
    assert card_id not in board["columns"][2]["cardIds"]
    assert str(card_id) not in board["cards"]
