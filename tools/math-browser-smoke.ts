import { chromium } from "playwright";
import assert from "node:assert/strict";

// Check the real publication, including bundled KaTeX fonts and mobile overflow.
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
    await page.goto(`${base}docs/monthly-inventory-coordination/`);
    await page.locator(".katex-display").first().waitFor();
    await page.evaluate(() => document.fonts.ready);
    assert((await page.locator(".katex-display").count()) >= 6);
    assert((await page.locator(".katex").count()) > 6, "Inline maths also renders");
    assert.equal(await page.locator(".katex-error").count(), 0);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert.deepEqual(failures, []);
    console.log(`Math publication verified at ${width}px`);
    await page.close();
  }
} finally {
  await browser.close();
}
