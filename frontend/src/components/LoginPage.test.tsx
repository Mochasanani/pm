import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { LoginPage } from "@/components/LoginPage";

const { loginMock, registerMock } = vi.hoisted(() => ({
  loginMock: vi.fn(),
  registerMock: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  login: loginMock,
  register: registerMock,
}));

beforeEach(() => {
  loginMock.mockReset();
  registerMock.mockReset();
});

test("sign in flow calls login and invokes onAuthenticated", async () => {
  loginMock.mockResolvedValueOnce({
    ok: true,
    user: { id: 1, username: "user", email: null, display_name: "Demo User" },
  });
  const onAuth = vi.fn();
  render(<LoginPage onAuthenticated={onAuth} />);

  await userEvent.type(screen.getByLabelText(/username/i), "user");
  await userEvent.type(screen.getByLabelText(/^password/i), "password");
  await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

  expect(loginMock).toHaveBeenCalledWith("user", "password");
  expect(onAuth).toHaveBeenCalledWith("user");
});

test("displays error on failed login", async () => {
  loginMock.mockResolvedValueOnce({ ok: false, error: "Invalid credentials" });
  render(<LoginPage onAuthenticated={vi.fn()} />);

  await userEvent.type(screen.getByLabelText(/username/i), "user");
  await userEvent.type(screen.getByLabelText(/^password/i), "wrong");
  await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Invalid credentials");
});

test("toggles into register mode and submits registration", async () => {
  registerMock.mockResolvedValueOnce({
    ok: true,
    user: { id: 2, username: "alice", email: "a@b.com", display_name: "Alice" },
  });
  const onAuth = vi.fn();
  render(<LoginPage onAuthenticated={onAuth} />);

  await userEvent.click(screen.getByRole("button", { name: /need an account/i }));
  await userEvent.type(screen.getByLabelText(/username/i), "alice");
  await userEvent.type(screen.getByLabelText(/display name/i), "Alice");
  await userEvent.type(screen.getByLabelText(/email/i), "a@b.com");
  await userEvent.type(screen.getByLabelText(/^password/i), "secretpass");
  await userEvent.click(screen.getByRole("button", { name: /create account/i }));

  expect(registerMock).toHaveBeenCalledWith({
    username: "alice",
    password: "secretpass",
    display_name: "Alice",
    email: "a@b.com",
  });
  expect(onAuth).toHaveBeenCalledWith("alice");
});

test("shows register error from API", async () => {
  registerMock.mockResolvedValueOnce({ ok: false, error: "Username already taken" });
  render(<LoginPage onAuthenticated={vi.fn()} />);

  await userEvent.click(screen.getByRole("button", { name: /need an account/i }));
  await userEvent.type(screen.getByLabelText(/username/i), "alice");
  await userEvent.type(screen.getByLabelText(/^password/i), "secretpass");
  await userEvent.click(screen.getByRole("button", { name: /create account/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Username already taken");
});
