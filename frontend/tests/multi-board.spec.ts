import { expect, test, type Page } from "@playwright/test";

/**
 * Full-flow tests for the multi-board, multi-user features.
 *
 * These tests register fresh accounts so they don't collide with the seed
 * "user" account or with each other across retries.
 */

const uniqueSuffix = () =>
  `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;

async function registerNew(page: Page, username: string, password = "password123") {
  await page.goto("/");
  await page.getByRole("button", { name: /need an account/i }).click();
  await page.getByLabel("Username").fill(username);
  await page.getByLabel(/display name/i).fill(`Display ${username}`);
  await page.getByLabel(/^password/i).fill(password);
  await page.getByRole("button", { name: /create account/i }).click();
  await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
}

test.describe("multi-board", () => {
  test("register -> create second board -> switch between them", async ({ page }) => {
    const username = `multi_${uniqueSuffix()}`;
    await registerNew(page, username);

    const switcher = page.getByTestId("board-switcher");
    await expect(switcher).toBeVisible();
    await expect(switcher).toContainText("My Board");

    await switcher.getByRole("button", { name: /switch board/i }).click();
    await page.getByRole("button", { name: /new board/i }).click();
    await page.getByLabel(/new board name/i).fill("Side Project");
    await page.getByRole("button", { name: /^add$/i }).click();

    await expect(switcher).toContainText("Side Project");
    // Fresh board still has the default 5 columns seeded on the backend.
    await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);

    await switcher.getByRole("button", { name: /switch board/i }).click();
    await page.getByRole("button", { name: "My Board" }).click();
    await expect(switcher).toContainText("My Board");
  });

  test("edit profile updates header display name", async ({ page }) => {
    const username = `profile_${uniqueSuffix()}`;
    await registerNew(page, username);

    await page.getByRole("button", { name: /edit profile/i }).click();
    const modal = page.getByTestId("profile-modal");
    await modal.getByLabel(/display name/i).fill("Renamed User");
    await modal.getByRole("button", { name: /^save$/i }).click();

    await expect(modal.getByRole("status")).toContainText(/updated/i);
    await modal.getByRole("button", { name: /close/i }).click();

    await expect(page.getByRole("button", { name: /edit profile/i })).toContainText(
      "Renamed User"
    );
  });

  test("users cannot see each other's boards", async ({ page, context }) => {
    const alice = `alice_${uniqueSuffix()}`;
    await registerNew(page, alice);
    await page.getByTestId("board-switcher").getByRole("button", { name: /switch board/i }).click();
    await page.getByRole("button", { name: /new board/i }).click();
    await page.getByLabel(/new board name/i).fill("Alice Only");
    await page.getByRole("button", { name: /^add$/i }).click();
    await expect(page.getByTestId("board-switcher")).toContainText("Alice Only");

    // Switch identity: log alice out, register a second user.
    await page.getByRole("button", { name: /sign out/i }).click();
    await context.clearCookies();

    const bob = `bob_${uniqueSuffix()}`;
    await registerNew(page, bob);
    const switcher = page.getByTestId("board-switcher");
    await switcher.getByRole("button", { name: /switch board/i }).click();
    const list = page.getByTestId("board-list");
    await expect(list).not.toContainText("Alice Only");
  });
});
