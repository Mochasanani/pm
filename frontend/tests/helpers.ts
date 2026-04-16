import type { APIRequestContext, Page } from "@playwright/test";

export async function login(page: Page) {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
}

export async function resetBoard(request: APIRequestContext) {
  const base = process.env.BASE_URL ?? "http://127.0.0.1:3000";
  const loginRes = await request.post(`${base}/api/login`, {
    data: { username: "user", password: "password" },
  });
  if (!loginRes.ok()) throw new Error(`reset: login failed (${loginRes.status()})`);
  const resetRes = await request.post(`${base}/api/board/reset`);
  if (!resetRes.ok()) {
    // DEV_MODE may not be enabled locally — that's fine for dev-only runs.
    if (resetRes.status() !== 403) {
      throw new Error(`reset: failed (${resetRes.status()})`);
    }
  }
}
