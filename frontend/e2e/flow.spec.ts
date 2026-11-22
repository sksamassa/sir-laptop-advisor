import { expect, test } from "@playwright/test";

test.describe("SIR laptop selection", () => {
  test("a guest receives a ranked, explained shortlist", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Ноутбук/ })).toBeVisible();
    const nav = page.getByRole("navigation", { name: "Основная навигация" });
    await expect(nav.getByRole("link", { name: "Подбор", exact: true })).toHaveAttribute(
      "aria-current",
      "page",
    );

    await page.getByRole("button", { name: "Подобрать ноутбук" }).click();
    await expect(page.getByText(/Найдено моделей/)).toBeVisible({ timeout: 25_000 });

    const cards = page.locator("ol > li");
    await expect(cards.first()).toBeVisible();
    expect(await cards.count()).toBeGreaterThan(3);

    await cards.first().getByRole("button", { name: "Почему так?" }).click();
    await expect(cards.first().getByText("ВКЛАД В ОЦЕНКУ")).toBeVisible();
    await expect(cards.first().getByText("Φ+", { exact: true })).toBeVisible();
  });

  test("three models can be compared from the ranking", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Подобрать ноутбук" }).click();
    await expect(page.getByText(/Найдено моделей/)).toBeVisible({ timeout: 25_000 });

    const chips = page.locator("li").getByRole("button", { name: "Сравнить", exact: true });
    for (let index = 0; index < 3; index += 1) {
      await chips.first().click();
    }

    await page.getByRole("button", { name: "Сравнить 3" }).click();
    const dialog = page.getByRole("dialog", { name: "Сравнение моделей" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText("Итог SIR")).toBeVisible();
    await expect(dialog.getByText("Цена", { exact: false })).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
  });

  test("catalog lists models and filters by operating system", async ({ page }) => {
    await page.goto("/catalog");
    await expect(page.getByRole("heading", { name: /Каталог моделей/ })).toBeVisible();
    const nav = page.getByRole("navigation", { name: "Основная навигация" });
    await expect(nav.getByRole("link", { name: "Каталог", exact: true })).toHaveAttribute(
      "aria-current",
      "page",
    );
    await expect(page.getByText(/Источник:/)).toBeVisible({ timeout: 20_000 });

    const cards = page.locator("article");
    await expect(cards.first()).toBeVisible({ timeout: 25_000 });
    const before = await cards.count();

    await page.getByRole("button", { name: "macOS" }).click();
    await expect(page.getByText(/Найдено:/)).toBeVisible();
    await expect(cards.first()).toBeVisible();
    expect(await cards.count()).toBeLessThanOrEqual(before);
    await expect(cards.first().getByText("macOS")).toBeVisible();
  });

  test("a guest reaches login through the header link", async ({ page }) => {
    await page.goto("/");
    const loginLink = page.getByRole("link", { name: "Войти" });
    await expect(loginLink).toBeVisible({ timeout: 15_000 });
    await loginLink.click();

    await expect(page).toHaveURL(/\/profile$/);
    await expect(page.getByRole("button", { name: "Войти" })).toBeVisible();
    await expect(page.getByLabel("Электронная почта")).toBeVisible();
    await expect(page.getByLabel("Пароль")).toBeVisible();
  });
});
