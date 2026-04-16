import { expect, test, type Page } from "@playwright/test";

async function login(page: Page) {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
}

test("loads the kanban board with 5 columns and 8 cards", async ({ page }) => {
  await login(page);
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
  await expect(page.locator('[data-testid^="card-"]')).toHaveCount(8);
});

test("adds a card to a column", async ({ page }) => {
  await login(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Playwright card");
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText("Playwright card")).toBeVisible();
});

test("moves a card between columns", async ({ page }) => {
  await login(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  const secondColumn = page.locator('[data-testid^="column-"]').nth(1);
  const card = firstColumn.locator('[data-testid^="card-"]').first();
  const cardTitle = await card.locator("h4").textContent();
  const initialFirstCount = await firstColumn.locator('[data-testid^="card-"]').count();

  const cardBox = await card.boundingBox();
  const colBox = await secondColumn.boundingBox();
  if (!cardBox || !colBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  await page.mouse.move(cardBox.x + cardBox.width / 2, cardBox.y + cardBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(colBox.x + colBox.width / 2, colBox.y + 120, { steps: 12 });
  await page.mouse.up();

  await expect(firstColumn.locator('[data-testid^="card-"]')).toHaveCount(initialFirstCount - 1);
  await expect(secondColumn.locator(`text=${cardTitle}`)).toBeVisible();
});

test("renames a column", async ({ page }) => {
  await login(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  const input = firstColumn.getByLabel("Column title");
  await input.fill("Renamed Column");
  await expect(input).toHaveValue("Renamed Column");
});

test("removes a card", async ({ page }) => {
  await login(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  const card = firstColumn.locator('[data-testid^="card-"]').first();
  const initialCount = await page.locator('[data-testid^="card-"]').count();
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: /delete/i }).click();
  await expect(page.locator('[data-testid^="card-"]')).toHaveCount(initialCount - 1);
});
