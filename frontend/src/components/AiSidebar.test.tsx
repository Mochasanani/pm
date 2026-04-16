import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { AiSidebar } from "@/components/AiSidebar";

vi.mock("@/lib/api", () => ({
  sendChat: vi.fn(),
}));

import { sendChat } from "@/lib/api";

const mockedSendChat = sendChat as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => {
  mockedSendChat.mockReset();
});

describe("AiSidebar", () => {
  it("renders collapsed rail when closed", () => {
    render(<AiSidebar open={false} onToggle={() => {}} onBoardChanged={() => {}} />);
    const sidebar = screen.getByTestId("ai-sidebar");
    expect(sidebar).toHaveAttribute("data-state", "collapsed");
    expect(screen.getByRole("button", { name: /open chat/i })).toBeInTheDocument();
    expect(screen.queryByLabelText("Chat message")).toBeNull();
  });

  it("calls onToggle from the collapsed rail", async () => {
    const onToggle = vi.fn();
    render(<AiSidebar open={false} onToggle={onToggle} onBoardChanged={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /open chat/i }));
    expect(onToggle).toHaveBeenCalled();
  });

  it("renders expanded panel with input when open", () => {
    render(<AiSidebar open onToggle={() => {}} onBoardChanged={() => {}} />);
    expect(screen.getByTestId("ai-sidebar")).toHaveAttribute("data-state", "expanded");
    expect(screen.getByLabelText("Chat message")).toBeInTheDocument();
  });

  it("calls onToggle when Collapse clicked", async () => {
    const onToggle = vi.fn();
    render(<AiSidebar open onToggle={onToggle} onBoardChanged={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /collapse chat/i }));
    expect(onToggle).toHaveBeenCalled();
  });

  it("sends a message and displays assistant reply", async () => {
    mockedSendChat.mockResolvedValue({ response: "Hello back", board_updates: [] });
    render(<AiSidebar open onToggle={() => {}} onBoardChanged={() => {}} />);

    await userEvent.type(screen.getByLabelText("Chat message"), "hi");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(mockedSendChat).toHaveBeenCalledWith("hi");
    await waitFor(() => {
      expect(screen.getByTestId("ai-msg-user")).toHaveTextContent("hi");
      expect(screen.getByTestId("ai-msg-assistant")).toHaveTextContent("Hello back");
    });
  });

  it("shows loading indicator while awaiting response", async () => {
    let resolve: (v: { response: string; board_updates: never[] }) => void = () => {};
    mockedSendChat.mockImplementation(
      () => new Promise((r) => { resolve = r; })
    );
    render(<AiSidebar open onToggle={() => {}} onBoardChanged={() => {}} />);
    await userEvent.type(screen.getByLabelText("Chat message"), "hi");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    expect(screen.getByTestId("ai-loading")).toBeInTheDocument();
    resolve({ response: "done", board_updates: [] });
    await waitFor(() => {
      expect(screen.queryByTestId("ai-loading")).toBeNull();
    });
  });

  it("calls onBoardChanged when reply has board_updates", async () => {
    mockedSendChat.mockResolvedValue({
      response: "Added",
      board_updates: [{ action: "create_card" }],
    });
    const onBoardChanged = vi.fn();
    render(<AiSidebar open onToggle={() => {}} onBoardChanged={onBoardChanged} />);
    await userEvent.type(screen.getByLabelText("Chat message"), "add a card");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    await waitFor(() => expect(onBoardChanged).toHaveBeenCalled());
  });

  it("does not call onBoardChanged for text-only replies", async () => {
    mockedSendChat.mockResolvedValue({ response: "hi", board_updates: [] });
    const onBoardChanged = vi.fn();
    render(<AiSidebar open onToggle={() => {}} onBoardChanged={onBoardChanged} />);
    await userEvent.type(screen.getByLabelText("Chat message"), "hi");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    await waitFor(() => {
      expect(screen.getByTestId("ai-msg-assistant")).toBeInTheDocument();
    });
    expect(onBoardChanged).not.toHaveBeenCalled();
  });

  it("shows error on failure", async () => {
    mockedSendChat.mockRejectedValue(new Error("boom"));
    render(<AiSidebar open onToggle={() => {}} onBoardChanged={() => {}} />);
    await userEvent.type(screen.getByLabelText("Chat message"), "hi");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    await waitFor(() => {
      expect(screen.getByText(/AI request failed/i)).toBeInTheDocument();
    });
  });
});
