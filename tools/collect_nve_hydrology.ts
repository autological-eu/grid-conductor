// Download NVE's public table through its documented Export data action.
// The website's embedded-report session stays inside the browser, never receipts.
import { chromium } from "playwright";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
const url =
  "https://www.nve.no/energi/analyser-og-statistikk/hydrologiske-data-til-kraftsituasjonsrapporten/";
const folder = "data/hydro-observations-2025/nve-hydrology-release";
await mkdir(folder, { recursive: true });
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
try {
  const page = await browser.newPage({
    viewport: { width: 1600, height: 1200 },
    acceptDownloads: true,
  });
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 40_000 });
  // Reject optional cookies through the site's own consent controls.
  const decline = page.locator("#CybotCookiebotDialogBodyButtonDecline");
  if (await decline.isVisible()) await decline.click();
  const frame = page.frameLocator('iframe[src*="reportEmbed"]');
  await frame.getByText("Tabell", { exact: true }).click({ timeout: 40_000 });
  const visual = frame
    .locator(".visualContainer")
    .filter({ has: frame.getByText("Nedbørsenergi", { exact: true }) });
  await visual.hover();
  await visual.getByRole("button", { name: "More options" }).click();
  await frame.getByText("Export data", { exact: true }).click();
  const download = page.waitForEvent("download", { timeout: 60_000 });
  void download.catch(() => {});
  if (await decline.isVisible()) await decline.click();
  await frame.getByRole("button", { name: "Export", exact: true }).click({ timeout: 10_000 });
  const file = await download;
  const path = `${folder}/table.xlsx`;
  await file.saveAs(path);
  await writeFile(
    `${folder}/receipt.json`,
    JSON.stringify(
      {
        source_url: url,
        action: "Public table / Export data / default Excel layout",
        retrieved_at: new Date().toISOString(),
        sha256: createHash("sha256")
          .update(await readFile(path))
          .digest("hex"),
        producer_sha256: createHash("sha256")
          .update(await readFile(import.meta.filename))
          .digest("hex"),
        limitations:
          "Current release revises HBV history; use weather-driven HBV column, not generation/stock-derived inflow.",
      },
      null,
      2,
    ),
  );
  console.log("NVE public hydrology export saved and hashed.");
} finally {
  await browser.close();
}
