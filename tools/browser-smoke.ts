import { chromium } from "playwright";
import assert from "node:assert/strict";

// Run against `bun run preview` or a deployed static origin. Fresh contexts
// isolate smoke scenarios from a developer's real browser data.
const base = process.env["SMOKE_URL"] ?? "http://127.0.0.1:4173/grid-conductor/";
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
try {
  for (const viewport of [
    { width: 1440, height: 1000 },
    { width: 390, height: 844 },
  ]) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    const failures: string[] = [];
    page.on("pageerror", (error) => failures.push(error.message));
    page.on("response", (response) => {
      if (response.status() >= 400) failures.push(`${response.status()} ${response.url()}`);
    });
    await page.goto(base);
    await page.getByRole("combobox", { name: "Choose a bottleneck" }).waitFor();
    assert(
      (await page
        .locator('svg[aria-label="Map of European bidding zones and congested borders"] path')
        .count()) > 20,
    );
    if (viewport.width > 1000) {
      await page.locator('g[aria-label="Select FR to IT-North bottleneck"]').click();
    } else {
      await page.getByRole("combobox", { name: "Choose a bottleneck" }).selectOption("FR>IT-North");
    }
    await page.getByRole("button", { name: "New", exact: true }).click();
    await page.getByRole("button", { name: "Run scenario" }).waitFor();
    await page.getByRole("button", { name: "Transmission line", exact: true }).click();
    await page.getByRole("button", { name: "Battery storage", exact: true }).click();
    await page.waitForFunction(
      () => document.querySelectorAll('[aria-label="Remove unit"]').length === 2,
    );
    await page.getByRole("button", { name: "Run scenario" }).click();
    await page.getByRole("button", { name: "Report", exact: true }).waitFor();
    assert(await page.getByText("Screening data availability", { exact: true }).isVisible());
    await page.reload();
    await page.getByRole("combobox", { name: "Choose a bottleneck" }).selectOption("FR>IT-North");
    await page.getByRole("button", { name: "Run scenario" }).waitFor();
    await page.getByText("Scenario 1", { exact: true }).click();
    await page.getByRole("button", { name: "Report", exact: true }).waitFor();
    assert.equal(await page.getByRole("button", { name: "Remove unit" }).count(), 2);
    await page.getByRole("button", { name: "Remove unit" }).first().click();
    await page.waitForFunction(
      () => document.querySelectorAll('[aria-label="Remove unit"]').length === 1,
    );
    await page.getByRole("button", { name: "Report", exact: true }).waitFor({ state: "detached" });
    await page.getByRole("button", { name: "Run scenario" }).click();
    await page.getByRole("button", { name: "Report", exact: true }).waitFor();
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
    if (process.env["SMOKE_SCREENSHOTS"])
      await page.screenshot({ path: `/tmp/grid-conductor-${viewport.width}.png`, fullPage: true });
    for (const route of ["docs/", "docs/fast-entsoe-screening/", "targets/"]) {
      const response = await page.goto(`${base}${route}`);
      assert.equal(response?.status(), 200, `Direct navigation to ${route}`);
      await page.getByRole("heading", { level: 1 }).first().waitFor();
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
    }
    assert(
      await page.getByText("Inspect recurring price differences", { exact: false }).isVisible(),
    );
    await page.getByRole("link", { name: "Workbench", exact: true }).click();
    await page.getByRole("combobox", { name: "Choose a bottleneck" }).waitFor();
    assert.deepEqual(failures, [], `Browser/asset errors at ${viewport.width}px`);
    console.log(
      `Browser smoke passed at ${viewport.width}px: map, selection, scenarios, interventions, evaluation, reload persistence, removal, direct research/targets routes, asset paths and overflow.`,
    );
    await context.close();
  }
} finally {
  await browser.close();
}
