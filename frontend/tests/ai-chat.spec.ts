import { expect, test, type Page } from "@playwright/test";
import { resetBoard } from "./helpers";

test.beforeEach(async ({ request }) => {
  await resetBoard(request);
});

async function login(page: Page) {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
}

test("opens sidebar, sends message, receives response", async ({ page }) => {
  await page.route("**/api/ai/chat", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ response: "Hello from AI", board_updates: [] }),
    });
  });
  await login(page);

  await expect(page.getByTestId("ai-sidebar")).toHaveAttribute("data-state", "expanded");

  await page.getByLabel("Chat message").fill("hi");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByTestId("ai-msg-user")).toHaveText("hi");
  await expect(page.getByTestId("ai-msg-assistant")).toContainText("Hello from AI");
});

test("AI-created card appears on board", async ({ page }) => {
  await login(page);

  const firstColumn = page.locator('[data-testid^="column-"]').first();
  const columnTestId = await firstColumn.getAttribute("data-testid");
  const columnId = columnTestId!.replace("column-", "");

  let createdCardId = 900000;
  await page.route("**/api/ai/chat", async (route) => {
    // Actually create the card via backend so refetch sees it
    const backendBase = process.env.BASE_URL ?? "http://127.0.0.1:8000";
    const createRes = await page.request.post(`${backendBase}/api/board/cards`, {
      data: { column_id: Number(columnId), title: "AI-made card", details: "from ai" },
    });
    const created = await createRes.json();
    createdCardId = created.id;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        response: "Created",
        board_updates: [{ action: "create_card", column_id: Number(columnId), title: "AI-made card" }],
      }),
    });
  });

  await page.getByLabel("Chat message").fill("add a card");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText("AI-made card")).toBeVisible();

  // Cleanup
  const backendBase = process.env.BASE_URL ?? "http://127.0.0.1:8000";
  await page.request.delete(`${backendBase}/api/board/cards/${createdCardId}`);
});

test("sidebar is open by default and can collapse/expand", async ({ page }) => {
  await login(page);
  const sidebar = page.getByTestId("ai-sidebar");
  await expect(sidebar).toHaveAttribute("data-state", "expanded");
  await page.getByRole("button", { name: "Collapse chat" }).click();
  await expect(sidebar).toHaveAttribute("data-state", "collapsed");
  await page.getByRole("button", { name: "Open chat" }).click();
  await expect(sidebar).toHaveAttribute("data-state", "expanded");
});

test("conversation history persists across multiple messages", async ({ page }) => {
  let callCount = 0;
  await page.route("**/api/ai/chat", async (route) => {
    callCount += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ response: `reply ${callCount}`, board_updates: [] }),
    });
  });
  await login(page);

  await page.getByLabel("Chat message").fill("first");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByTestId("ai-msg-assistant").nth(0)).toContainText("reply 1");

  await page.getByLabel("Chat message").fill("second");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByTestId("ai-msg-assistant").nth(1)).toContainText("reply 2");

  await expect(page.getByTestId("ai-msg-user")).toHaveCount(2);
});
