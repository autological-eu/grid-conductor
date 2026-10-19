import { chromium } from "playwright";
import assert from "node:assert/strict";

// Check real publications, including bundled KaTeX fonts and mobile overflow.
const base = process.env["SMOKE_URL"] ?? "http://127.0.0.1:4173/grid-conductor/";
const browser = await chromium.launch({ args: ["--no-sandbox"] });
try {
  for (const width of [1440, 390, 320]) {
    for (const article of [
      { path: "docs/daily-fuel-dispatch-2025/", display: true },
      { path: "docs/european-physical-synthetic-clearing-2025/", display: false },
    ]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      const failures: string[] = [];
      page.on("pageerror", (error) => failures.push(error.message));
      page.on("response", (response) => {
        if (response.status() >= 400) failures.push(`${response.status()} ${response.url()}`);
      });
      await page.goto(`${base}${article.path}`);
      await page.locator(".katex").first().waitFor();
      await page.evaluate(() => document.fonts.ready);
      if (article.display) assert((await page.locator(".katex-display").count()) >= 1);
      assert((await page.locator(".katex").count()) > 1, "Inline maths also renders");
      assert.equal(await page.locator(".katex-error").count(), 0);
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      assert.deepEqual(failures, []);
      console.log(`Math publication verified at ${width}px: ${article.path}`);
      await page.close();
    }
  }
} finally {
  await browser.close();
}
