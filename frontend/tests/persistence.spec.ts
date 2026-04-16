import { expect, test, type Page } from "@playwright/test";

async function login(page: Page) {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
}

test.describe.serial("persistence across page refresh", () => {
  test("create a card, refresh, card persists", async ({ page }) => {
    await login(page);
    const firstColumn = page.locator('[data-testid^="column-"]').first();
    await firstColumn.getByRole("button", { name: /add a card/i }).click();
    await firstColumn.getByPlaceholder("Card title").fill("Persistent card");
    await firstColumn.getByPlaceholder("Details").fill("Should survive refresh");
    await firstColumn.getByRole("button", { name: /add card/i }).click();
    await expect(firstColumn.getByText("Persistent card")).toBeVisible();

    await page.reload();
    await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
    await expect(firstColumn.getByText("Persistent card")).toBeVisible();
  });

  test("rename column, refresh, name persists", async ({ page }) => {
    await login(page);
    const firstColumn = page.locator('[data-testid^="column-"]').first();
    const input = firstColumn.getByLabel("Column title");
    const originalName = await input.inputValue();
    await input.fill("Renamed Backlog");
    // Blur to trigger the API call
    await page.keyboard.press("Tab");

    await page.reload();
    await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
    await expect(firstColumn.getByLabel("Column title")).toHaveValue("Renamed Backlog");

    // Restore original name
    await firstColumn.getByLabel("Column title").fill(originalName);
    await page.keyboard.press("Tab");
  });

  test("delete card, refresh, card is gone", async ({ page }) => {
    await login(page);
    // Delete the "Persistent card" we created earlier
    const firstColumn = page.locator('[data-testid^="column-"]').first();
    const card = firstColumn.getByText("Persistent card");
    await expect(card).toBeVisible();

    const cardArticle = card.locator("xpath=ancestor::article");
    await cardArticle.getByRole("button", { name: /delete/i }).click();

    await page.reload();
    await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
    await expect(firstColumn.getByText("Persistent card")).not.toBeVisible();
  });

  test("move card, refresh, position persists", async ({ page }) => {
    await login(page);
    const firstColumn = page.locator('[data-testid^="column-"]').first();
    const secondColumn = page.locator('[data-testid^="column-"]').nth(1);
    const card = firstColumn.locator('[data-testid^="card-"]').first();
    const cardText = await card.locator("h4").textContent();
    const initialFirstCount = await firstColumn.locator('[data-testid^="card-"]').count();

    const cardBox = await card.boundingBox();
    const colBox = await secondColumn.boundingBox();
    if (!cardBox || !colBox) throw new Error("Unable to resolve drag coordinates.");

    await page.mouse.move(cardBox.x + cardBox.width / 2, cardBox.y + cardBox.height / 2);
    await page.mouse.down();
    await page.mouse.move(colBox.x + colBox.width / 2, colBox.y + 120, { steps: 12 });
    await page.mouse.up();

    // Card should have left first column
    await expect(firstColumn.locator('[data-testid^="card-"]')).toHaveCount(initialFirstCount - 1);

    await page.reload();
    await expect(firstColumn).toBeVisible();
    // After refresh, first column should still have fewer cards
    await expect(firstColumn.locator('[data-testid^="card-"]')).toHaveCount(initialFirstCount - 1);
    // And card should be in second column
    await expect(secondColumn.locator(`text=${cardText}`)).toBeVisible();
  });
});
