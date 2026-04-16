import { expect, test } from "@playwright/test";

test.describe("authentication", () => {
  test("shows login page when not authenticated", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
    await expect(page.getByLabel("Username")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
  });

  test("full login flow: login -> see board -> logout -> see login", async ({ page }) => {
    await page.goto("/");

    // Fill in credentials and submit
    await page.getByLabel("Username").fill("user");
    await page.getByLabel("Password").fill("password");
    await page.getByRole("button", { name: "Sign in" }).click();

    // Should see the board
    await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();

    // Logout
    await page.getByRole("button", { name: "Sign out" }).click();

    // Should be back at login
    await expect(page.getByLabel("Username")).toBeVisible();
  });

  test("invalid credentials show error", async ({ page }) => {
    await page.goto("/");
    await page.getByLabel("Username").fill("user");
    await page.getByLabel("Password").fill("wrong");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.getByText("Invalid credentials")).toBeVisible();
    // Should still be on login page
    await expect(page.getByLabel("Username")).toBeVisible();
  });
});
