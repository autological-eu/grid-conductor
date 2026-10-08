import { chromium } from "playwright";
import assert from "node:assert/strict";
const base = process.env["SMOKE_URL"] ?? "http://127.0.0.1:4196/grid-conductor/";
const browser = await chromium.launch({ args: ["--no-sandbox"] });
try {
  for (const width of [1440, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(`${base}docs/synthetic-bids-germany-2025/`);
    await page
      .getByRole("heading", {
        name: "Germany synthetic bids and hourly clearing — 2025 diagnostic",
        exact: true,
      })
      .waitFor();
    await page.locator("article img").first().scrollIntoViewIfNeeded();
    await page.locator("article img").last().scrollIntoViewIfNeeded();
    await page.waitForFunction(
      () =>
        Array.from(document.querySelectorAll("article img")).length === 2 &&
        Array.from(document.querySelectorAll<HTMLImageElement>("article img")).every(
          (i) => i.complete && i.naturalWidth > 0,
        ),
    );
    assert.equal(errors.length, 0, errors.join("\n"));
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    const link = page.getByRole("link", { name: "Detailed implementation plan", exact: true });
    assert((await link.getAttribute("href"))?.includes("/docs/synthetic-zonal-clearing-plan"));
    await link.click();
    await page
      .getByRole("heading", {
        name: "Hourly synthetic zonal clearing — implementation plan",
        exact: true,
      })
      .waitFor();
    assert.equal(await page.locator("article h2").count(), 13);
    await page.close();
    console.log(`Report figures and plan verified at ${width}px`);
  }
} finally {
  await browser.close();
}
