import { chromium } from "playwright";
import assert from "node:assert/strict";

// Verify the retained research publication renders on desktop and small phones.
const base = process.env["SMOKE_URL"] ?? "http://127.0.0.1:4173/grid-conductor/";
const browser = await chromium.launch({ args: ["--no-sandbox"] });
try {
  for (const width of [1440, 390, 320]) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    const failures: string[] = [];
    page.on("pageerror", (error) => failures.push(error.message));
    page.on("response", (response) => {
      if (response.status() >= 400) failures.push(`${response.status()} ${response.url()}`);
    });
    const response = await page.goto(`${base}docs/research-baselines-2025/`);
    assert.equal(response?.status(), 200);
    await page
      .getByRole("heading", { name: "2025 European dispatch research baselines" })
      .waitFor();
    assert((await page.locator("article").innerText()).includes("25.051 EUR/MWh"));
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert.deepEqual(failures, []);
    await page.close();
  }
} finally {
  await browser.close();
}
