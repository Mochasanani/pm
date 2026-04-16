import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";

const { fixtureBoard } = vi.hoisted(() => ({
  fixtureBoard: {
    columns: [
      { id: "col-1", title: "Backlog", cardIds: ["c1"] },
      { id: "col-2", title: "Discovery", cardIds: [] },
      { id: "col-3", title: "In Progress", cardIds: [] },
      { id: "col-4", title: "Review", cardIds: [] },
      { id: "col-5", title: "Done", cardIds: [] },
    ],
    cards: {
      c1: { id: "c1", title: "Seed", details: "Seed details" },
    },
  },
}));

vi.mock("@/lib/api", () => ({
  fetchBoard: vi.fn().mockResolvedValue(fixtureBoard),
  renameColumn: vi.fn().mockResolvedValue(undefined),
  createCard: vi.fn().mockResolvedValue({ id: 999, title: "New card", details: "Notes" }),
  deleteCard: vi.fn().mockResolvedValue(undefined),
  moveCardApi: vi.fn().mockResolvedValue(undefined),
  logout: vi.fn().mockResolvedValue(undefined),
  sendChat: vi.fn().mockResolvedValue({ response: "ok", board_updates: [] }),
  clearConversation: vi.fn().mockResolvedValue(undefined),
}));

const renderBoard = async () => {
  render(<KanbanBoard user="user" onLogout={() => {}} />);
  await waitFor(() => {
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
  });
};

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];

describe("KanbanBoard", () => {
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
});
