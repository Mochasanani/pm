import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";

const { fixtureBoard, fixtureBoards } = vi.hoisted(() => ({
  fixtureBoards: [
    {
      id: 1,
      name: "My Board",
      description: "",
      position: 0,
      created_at: "2026-01-01",
      updated_at: "2026-01-01",
    },
    {
      id: 2,
      name: "Side Project",
      description: "",
      position: 1,
      created_at: "2026-01-02",
      updated_at: "2026-01-02",
    },
  ],
  fixtureBoard: {
    board: {
      id: 1,
      name: "My Board",
      description: "",
      position: 0,
      created_at: "2026-01-01",
      updated_at: "2026-01-01",
    },
    columns: [
      { id: "col-1", title: "Backlog", cardIds: ["c1", "c2", "c3"] },
      { id: "col-2", title: "Discovery", cardIds: [] },
      { id: "col-3", title: "In Progress", cardIds: [] },
      { id: "col-4", title: "Review", cardIds: [] },
      { id: "col-5", title: "Done", cardIds: [] },
    ],
    cards: {
      c1: { id: "c1", title: "Seed", details: "Seed details", label_ids: [] },
      c2: { id: "c2", title: "Cypress docs", details: "e2e notes", label_ids: [10] },
      c3: { id: "c3", title: "Launch email", details: "draft copy", label_ids: [11] },
    },
    labels: [
      { id: 10, name: "Urgent", color: "#ff0000" },
      { id: 11, name: "Low", color: "#00ff00" },
    ],
  },
}));

vi.mock("@/lib/api", () => ({
  listBoards: vi.fn().mockResolvedValue(fixtureBoards),
  createBoard: vi.fn().mockImplementation((name: string) =>
    Promise.resolve({
      id: 3,
      name,
      description: "",
      position: 2,
      created_at: "2026-01-03",
      updated_at: "2026-01-03",
    })
  ),
  renameBoard: vi.fn().mockImplementation((id: number, changes: { name: string }) =>
    Promise.resolve({
      id,
      name: changes.name,
      description: "",
      position: 0,
      created_at: "2026-01-01",
      updated_at: "2026-01-01",
    })
  ),
  deleteBoard: vi.fn().mockResolvedValue(undefined),
  fetchBoardById: vi.fn().mockResolvedValue(fixtureBoard),
  renameColumnOnBoard: vi.fn().mockResolvedValue(undefined),
  createCardOnBoard: vi
    .fn()
    .mockResolvedValue({ id: 999, title: "New card", details: "Notes" }),
  deleteCardOnBoard: vi.fn().mockResolvedValue(undefined),
  updateCardOnBoard: vi
    .fn()
    .mockImplementation((_boardId, _cardId, changes) =>
      Promise.resolve({ id: 1, ...changes })
    ),
  moveCardOnBoard: vi.fn().mockResolvedValue(undefined),
  setCardLabels: vi.fn().mockResolvedValue([]),
  listLabels: vi.fn().mockResolvedValue([]),
  createLabel: vi.fn().mockResolvedValue({ id: 99, name: "new", color: "#888888" }),
  logout: vi.fn().mockResolvedValue(undefined),
  updateMe: vi.fn().mockImplementation((changes) =>
    Promise.resolve({
      id: 1,
      username: "user",
      email: changes.email ?? null,
      display_name: changes.display_name ?? "Demo User",
    })
  ),
  sendChat: vi.fn().mockResolvedValue({ response: "ok", board_updates: [] }),
  clearConversation: vi.fn().mockResolvedValue(undefined),
}));

const testUser = {
  id: 1,
  username: "user",
  email: null,
  display_name: "Demo User",
};

const renderBoard = async () => {
  render(
    <KanbanBoard user={testUser} onUserUpdated={() => {}} onLogout={() => {}} />
  );
  await waitFor(() => {
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
  });
};

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];

describe("KanbanBoard", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("renders five columns after loading", async () => {
    await renderBoard();
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column", async () => {
    await renderBoard();
    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    await renderBoard();
    const column = getFirstColumn();
    await userEvent.click(within(column).getByRole("button", { name: /add a card/i }));

    await userEvent.type(within(column).getByPlaceholderText(/card title/i), "New card");
    await userEvent.type(within(column).getByPlaceholderText(/details/i), "Notes");
    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    await waitFor(() => {
      expect(within(column).getByText("New card")).toBeInTheDocument();
    });

    await userEvent.click(within(column).getByRole("button", { name: /delete new card/i }));
    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("shows the board switcher with the current board name", async () => {
    await renderBoard();
    const switcher = screen.getByTestId("board-switcher");
    expect(within(switcher).getByText("My Board")).toBeInTheDocument();
  });

  it("switches to another board and reloads its content", async () => {
    const api = await import("@/lib/api");
    await renderBoard();

    await userEvent.click(screen.getByRole("button", { name: /switch board/i }));
    await userEvent.click(screen.getByRole("button", { name: "Side Project" }));

    await waitFor(() => {
      expect(api.fetchBoardById).toHaveBeenCalledWith(2);
    });
  });

  it("opens the card edit modal and saves changes", async () => {
    const api = await import("@/lib/api");
    await renderBoard();

    await userEvent.click(screen.getByRole("button", { name: /open seed/i }));
    const modal = await screen.findByTestId("card-edit-modal");
    const titleInput = within(modal).getByLabelText(/title/i);
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "Updated");
    await userEvent.click(within(modal).getByRole("button", { name: /^save$/i }));

    await waitFor(() => {
      expect(api.updateCardOnBoard).toHaveBeenCalledWith(1, "c1", {
        title: "Updated",
        details: "Seed details",
        due_date: null,
      });
    });
  });

  it("saves a due date from the card edit modal and shows the badge", async () => {
    const api = await import("@/lib/api");
    await renderBoard();

    await userEvent.click(screen.getByRole("button", { name: /open seed/i }));
    const modal = await screen.findByTestId("card-edit-modal");
    const dueInput = within(modal).getByLabelText(/due date/i);
    await userEvent.clear(dueInput);
    await userEvent.type(dueInput, "2027-10-15");
    await userEvent.click(within(modal).getByRole("button", { name: /^save$/i }));

    await waitFor(() => {
      expect(api.updateCardOnBoard).toHaveBeenCalledWith(1, "c1", {
        title: "Seed",
        details: "Seed details",
        due_date: "2027-10-15",
      });
    });

    expect(screen.getByTestId("due-date-c1")).toBeInTheDocument();
  });

  it("opens the profile modal and saves a new display name", async () => {
    const api = await import("@/lib/api");
    const onUserUpdated = vi.fn();
    render(
      <KanbanBoard user={testUser} onUserUpdated={onUserUpdated} onLogout={() => {}} />
    );
    await waitFor(() => {
      expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
    });

    await userEvent.click(screen.getByRole("button", { name: /edit profile/i }));
    const modal = await screen.findByTestId("profile-modal");
    const nameInput = within(modal).getByLabelText(/display name/i);
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, "Renamed");
    await userEvent.click(within(modal).getByRole("button", { name: /^save$/i }));

    await waitFor(() => {
      expect(api.updateMe).toHaveBeenCalledWith({ display_name: "Renamed" });
    });
    expect(onUserUpdated).toHaveBeenCalled();
  });

  it("filters cards by the search box", async () => {
    await renderBoard();
    expect(screen.getByText("Seed")).toBeInTheDocument();
    expect(screen.getByText("Cypress docs")).toBeInTheDocument();

    await userEvent.type(screen.getByTestId("card-search"), "cypress");

    await waitFor(() => {
      expect(screen.queryByText("Seed")).not.toBeInTheDocument();
    });
    expect(screen.getByText("Cypress docs")).toBeInTheDocument();
    expect(screen.queryByText("Launch email")).not.toBeInTheDocument();
  });

  it("filters cards by clicking a label chip", async () => {
    await renderBoard();
    await userEvent.click(screen.getByTestId("filter-label-10"));

    await waitFor(() => {
      expect(screen.queryByText("Seed")).not.toBeInTheDocument();
    });
    expect(screen.getByText("Cypress docs")).toBeInTheDocument();
    expect(screen.queryByText("Launch email")).not.toBeInTheDocument();
  });

  it("assigns a label to a card from the edit modal", async () => {
    const api = await import("@/lib/api");
    await renderBoard();

    await userEvent.click(screen.getByRole("button", { name: /open seed/i }));
    const modal = await screen.findByTestId("card-edit-modal");
    await userEvent.click(within(modal).getByTestId("label-toggle-10"));
    await userEvent.click(within(modal).getByRole("button", { name: /^save$/i }));

    await waitFor(() => {
      expect(api.setCardLabels).toHaveBeenCalledWith(1, "c1", [10]);
    });
  });

  it("creates a new board via the switcher", async () => {
    const api = await import("@/lib/api");
    await renderBoard();

    await userEvent.click(screen.getByRole("button", { name: /switch board/i }));
    await userEvent.click(screen.getByRole("button", { name: /new board/i }));
    await userEvent.type(screen.getByLabelText(/new board name/i), "Fresh");
    await userEvent.click(screen.getByRole("button", { name: /^add$/i }));

    await waitFor(() => {
      expect(api.createBoard).toHaveBeenCalledWith("Fresh");
    });
  });
});
