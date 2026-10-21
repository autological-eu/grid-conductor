import { chromium } from "playwright";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const base = process.env["SMOKE_URL"] ?? "http://127.0.0.1:4173/grid-conductor/";
const browser = await chromium.launch({ args: ["--no-sandbox"] });
try {
  for (const width of [1440, 390, 320]) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    const errors: string[] = [];
    const loadedCountries = new Set<string>();
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("response", (r) => {
      if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`);
      const match = r.url().match(/country-explorer-2025\/([A-Z]{2})\.json\.gz/);
      if (match?.[1]) loadedCountries.add(match[1]);
    });
    await page.goto(base + "countries/");
    await page.getByRole("heading", { name: "1. Germany: generation mix", exact: true }).waitFor();
    const selector = page.getByRole("combobox", { name: "Country", exact: true });
    assert.equal(await selector.locator("option").count(), 34);
    assert.deepEqual(
      [...loadedCountries],
      ["DE"],
      "Only the selected country's hourly data is downloaded",
    );
    assert(await page.getByText(/full-year Europe MAE €27.49/).isVisible());
    assert.equal(await page.locator("[data-price-zone]").count(), 1);
    await page.getByText("Original IRENA capacity records", { exact: false }).click();
    await page.getByRole("columnheader", { name: "End 2025 MW", exact: true }).waitFor();
    await selector.selectOption("NO");
    await page.getByRole("heading", { name: "1. Norway: generation mix", exact: true }).waitFor();
    assert.equal(await page.locator("[data-price-zone]").count(), 5);
    assert(await page.getByText(/Missing constituent areas: NO5/).isVisible());
    const generationDownload = page.waitForEvent("download");
    await page
      .getByRole("button", { name: "Download full-year generation comparison", exact: true })
      .click();
    const generation = await generationDownload;
    const genRows = (await readFile((await generation.path())!, "utf8")).trimEnd().split("\n");
    assert.equal(genRows.length, 8761);
    const firstGeneration = genRows[1]!.split(",");
    assert.equal(
      firstGeneration[2],
      "",
      "NO country observed generation remains unknown with NO5 missing",
    );
    assert(firstGeneration[3] !== "", "Modeled generation remains available");
    await page
      .getByRole("combobox", { name: "Generation area", exact: true })
      .selectOption("zone:NO1");
    await page.getByText("Source area(s): NO1.", { exact: false }).waitFor();
    const priceDownload = page.waitForEvent("download");
    await page
      .getByRole("button", { name: "Download full-year hourly prices", exact: true })
      .click();
    const prices = await priceDownload;
    const priceRows = (await readFile((await prices.path())!, "utf8")).trimEnd().split("\n");
    assert.equal(priceRows.length, 8761);
    assert(
      priceRows[0]?.includes("NO1_observed_eur_mwh") && priceRows[0]?.includes("NO5_model_eur_mwh"),
    );
    assert(priceRows.at(-1)?.startsWith("2025-12-31T23:00:00.000Z"));
    await page.getByRole("combobox", { name: "Chart detail", exact: true }).selectOption("daily");
    await page.getByLabel("From (UTC)", { exact: true }).fill("2025-03-30");
    await page.getByLabel("Through (UTC)", { exact: true }).fill("2025-03-30");
    await page.waitForFunction(() => !document.querySelector('[role="alert"]'));
    assert(page.url().includes("country=NO") && page.url().includes("resolution=daily"));
    if (width === 1440) {
      await selector.selectOption("IT");
      await page.getByRole("heading", { name: "1. Italy: generation mix", exact: true }).waitFor();
      assert.equal(await page.locator("[data-price-zone]").count(), 7);
      assert.equal(await page.locator('[data-price-zone="IT-CALA"]').count(), 1);
      assert.equal(await page.locator('[data-price-zone="IT-SICI"]').count(), 1);
      await selector.selectOption("LU");
      await page
        .getByRole("heading", { name: "1. Luxembourg: generation mix", exact: true })
        .waitFor();
      assert.equal(await page.locator('[data-price-zone="DE-LU"]').count(), 1);
      assert(
        await page.getByText("Shared Germany–Luxembourg price area", { exact: true }).isVisible(),
      );
    }
    await page.reload();
    await page.locator("[data-price-zone]").first().waitFor();
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert((await page.locator(".recharts-line-curve, .recharts-line-dot").count()) > 0);
    assert.deepEqual(errors, []);
    console.log(
      `Country explorer verified at ${width}px: lazy loading, coverage gaps, zones, dates, full-year CSVs, reload and overflow`,
    );
    await page.close();
  }
} finally {
  await browser.close();
}
