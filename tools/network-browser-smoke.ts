import { chromium } from "playwright";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const base = process.env["SMOKE_URL"] ?? "http://127.0.0.1:4173/grid-conductor/";
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
try {
  for (const viewport of [
    { width: 1440, height: 1000 },
    { width: 390, height: 844 },
  ]) {
    const context = await browser.newContext({ viewport }),
      page = await context.newPage(),
      failures: string[] = [];
    page.on("pageerror", (e) => failures.push(e.message));
    page.on("response", (r) => {
      if (r.status() >= 400) failures.push(`${r.status()} ${r.url()}`);
    });
    assert.equal((await page.goto(`${base}network/`))?.status(), 200);
    await page.getByTestId("network-input").setInputFiles({
      name: "analytical-test-only.json",
      mimeType: "application/json",
      buffer: await readFile("tests/fixtures/network.json"),
    });
    await page.getByLabel("Additional MW", { exact: true }).fill("50");
    await page.getByRole("button", { name: "Set capacity addition" }).click();
    await page.getByTestId("network-run").click();
    await page.getByTestId("network-result").waitFor({ timeout: 30000 });
    assert.match(await page.getByTestId("network-result").innerText(), /€9,000/);
    await page.getByTestId("network-run").click();
    await page.getByText(/baseline cached/).waitFor();
    await page.reload();
    await page.getByText("AB: +50 MW in both directions").waitFor();
    await page.getByTestId("network-run").click();
    await page.getByTestId("network-result").waitFor();
    assert.match(await page.getByTestId("network-result").innerText(), /€9,000/);
    await page.getByRole("button", { name: "Remove", exact: true }).click();
    await page.getByTestId("network-result").waitFor({ state: "detached" });
    await page.getByRole("button", { name: "Add 100 MW / 400 MWh battery", exact: true }).click();
    await page.getByTestId("network-run").click();
    await page.getByTestId("network-result").waitFor();
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
    await page.getByRole("button", { name: "Load real-data benchmark", exact: true }).click();
    await page.getByLabel("Additional MW", { exact: true }).fill("500");
    await page.getByRole("button", { name: "Set capacity addition" }).click();
    await page.getByTestId("network-run").click();
    await page.getByTestId("network-result").waitFor({ timeout: 30000 });
    assert.match(await page.getByTestId("network-result").innerText(), /1,392,863/);
    await page.reload();
    await page.getByText("dc:14823: +500 MW in both directions").waitFor();
    await page.getByTestId("network-run").click();
    await page.getByTestId("network-result").waitFor({ timeout: 30000 });
    assert.match(await page.getByTestId("network-result").innerText(), /1,392,863/);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
    if (viewport.width > 1000) {
      // Make cancellation observable using a full-period TEST input, never public research.
      const testInput = JSON.parse(await readFile("tests/fixtures/network.json", "utf8"));
      const H = 8760;
      testInput.timestamps = Array.from({ length: H }, (_, t) =>
        new Date(Date.UTC(2025, 0, 1) + t * 3600000).toISOString(),
      );
      for (const mapping of [testInput.load_mw, testInput.external_net_import_mw])
        for (const key of Object.keys(mapping)) mapping[key] = Array(H).fill(mapping[key][0]);
      for (const generator of testInput.generators)
        generator.max_mw = Array(H).fill(generator.max_mw[0]);
      for (const edge of testInput.edges)
        for (const key of ["ab_mw", "ba_mw"]) edge[key] = Array(H).fill(edge[key][0]);
      await page.getByTestId("network-input").setInputFiles({
        name: "cancellation-test-only.json",
        mimeType: "application/json",
        buffer: Buffer.from(JSON.stringify(testInput)),
      });
      await page
        .getByText("Input parsed. Source declaration is not independent validation.")
        .waitFor();
      await page.getByTestId("network-run").click();
      await page.getByRole("button", { name: "Cancel", exact: true }).click();
      await page.getByText("Cancelled. No result retained.").waitFor();
      assert.equal(await page.getByTestId("network-result").count(), 0);
    }
    assert.deepEqual(failures, []);
    if (process.env["SMOKE_SCREENSHOTS"])
      await page.screenshot({ path: `/tmp/grid-network-${viewport.width}.png`, fullPage: true });
    await context.close();
    console.log(
      `Network worker, WASM, exact benefit, cache, storage, persistence: ${viewport.width}px passed`,
    );
  }
} finally {
  await browser.close();
}
