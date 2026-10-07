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
    { width: 320, height: 568 },
    { width: 667, height: 375 },
  ]) {
    const context = await browser.newContext({
      viewport,
      isMobile: viewport.width < 1024,
      hasTouch: viewport.width < 1024,
    });
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
    const corridors = await page
      .locator("g[data-corridor]")
      .evaluateAll((elements) => elements.map((element) => element.getAttribute("data-corridor")));
    assert(corridors.length > 0);
    assert.equal(new Set(corridors).size, corridors.length);
    const keyboardCorridor = page.locator('g[data-corridor="FR|IT-North"]');
    await keyboardCorridor.focus();
    assert.equal(
      await keyboardCorridor.evaluate((element) => getComputedStyle(element).outlineStyle),
      "none",
      "SVG corridors never draw a native rectangular focus outline",
    );
    await keyboardCorridor.press("Enter");
    await page.getByRole("button", { name: "Hourly price difference" }).waitFor();
    if (viewport.width > 1000) {
      await page.locator('g[data-corridor="FR|IT-North"]').click();
    } else {
      await page.getByRole("combobox", { name: "Choose a bottleneck" }).selectOption("FR>IT-North");
    }
    await page.getByRole("combobox", { name: "Choose a bottleneck" }).selectOption("FR>IT-North");
    await page
      .getByText(/classification is unverified: original ENTSO-E request receipts are unavailable/)
      .waitFor();
    const sourceAuditHref = await page
      .getByRole("link", { name: "Flow-source audit" })
      .getAttribute("href");
    assert(sourceAuditHref?.includes("docs/2025-exchange-validation"));
    // Numeric bidding-zone suffixes must still select the country polygons.
    for (const [border, countries] of [
      ["SE4>PL", ["PL", "SE"]],
      ["PL>SE4", ["PL", "SE"]],
      ["DK1>NO2", ["DK", "NO"]],
      ["FR>IT-North", ["FR", "IT"]],
    ] as const) {
      const picker = page.getByRole("combobox", { name: "Choose a bottleneck" });
      assert.equal(await picker.locator(`option[value="${border}"]`).count(), 1);
      await picker.selectOption(border);
      const focused = await page
        .locator('path[data-focused="true"]')
        .evaluateAll((elements) =>
          elements.map((element) => element.getAttribute("data-country")).sort(),
        );
      assert.deepEqual(focused, [...countries]);
    }
    await page.getByRole("button", { name: "Hourly price difference" }).click();
    await page.getByText(/Coverage: 8,759/).waitFor();
    assert.equal(await page.getByRole("dialog").locator("svg[role=img] path").count(), 3);
    const dialogBox = await page.getByRole("dialog").boundingBox();
    assert(
      dialogBox && dialogBox.y >= 0 && dialogBox.y + dialogBox.height <= viewport.height,
      "Price dialog stays inside the viewport, including landscape",
    );
    if (viewport.width < 1024) {
      const closeBox = await page.getByRole("button", { name: "Close", exact: true }).boundingBox();
      assert(closeBox && closeBox.y >= 0 && closeBox.y + closeBox.height <= viewport.height);
    }
    await page.getByRole("combobox", { name: "Price chart period" }).selectOption("0");
    await page.getByText(/Coverage: 744/).waitFor();
    await page.getByRole("button", { name: "Close", exact: true }).click();
    await page.getByText("Production carbon · price-separation hours", { exact: true }).click();
    await page.getByText(/FR: .*mapped subset only/).waitFor();
    await page.getByRole("button", { name: "New", exact: true }).click();
    await page.getByRole("button", { name: "Run scenario" }).waitFor();
    if (viewport.width > 1000) {
      await page
        .getByRole("button", { name: "Transmission line", exact: true })
        .dragTo(page.locator('g[data-corridor="FR|IT-North"]'));
      await page.waitForFunction(
        () => document.querySelectorAll('[aria-label="Remove unit"]').length === 1,
      );
    } else {
      await page.getByRole("button", { name: "Transmission line", exact: true }).click();
    }
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
    for (const route of [
      "docs/",
      "docs/worked-example-se4-pl/",
      "docs/fast-entsoe-screening/",
      "docs/pypsa-fleet-generation-comparison-2025/",
      "targets/",
    ]) {
      const response = await page.goto(`${base}${route}`);
      assert.equal(response?.status(), 200, `Direct navigation to ${route}`);
      await page.getByRole("heading", { level: 1 }).first().waitFor();
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
      if (route.startsWith("docs/network-")) {
        await page.locator("article img").scrollIntoViewIfNeeded();
        await page.waitForFunction(() =>
          Array.from(document.images).every((img) => img.complete && img.naturalWidth > 0),
        );
        assert(
          await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
        );
      }
      if (route === "docs/") {
        await page.getByRole("heading", { name: "2. What market opportunity means" }).waitFor();
        const anchorsResolve = await page
          .locator('nav[aria-label="Methods chapters"] a')
          .evaluateAll((links) =>
            links.every((link) => document.getElementById(link.getAttribute("href")!.slice(1))),
          );
        assert(anchorsResolve, "Every methods chapter links to a rendered section");
        assert(
          await page
            .getByRole("link", { name: "SE4 → PL: reproduce €229.9 million/year →" })
            .count(),
        );
      }
      if (route === "docs/worked-example-se4-pl/") {
        await page.getByRole("heading", { name: "3. Reproduce €229.9 million/year" }).waitFor();
        // Execute the exact published console example against the served artifact.
        const source = await page.locator("pre code.language-javascript").innerText();
        const values: number[] = await page.evaluate(async (code) => {
          const reproduce = new Function(
            `return (async () => {\n${code}\nreturn [bound, line(500), line(700)]; })()`,
          );
          return reproduce();
        }, source);
        assert(Math.abs(values[0]! - 229.8925178625) < 1e-9);
        assert(Math.abs(values[1]! - 154.86579666666665) < 1e-9);
        assert(Math.abs(values[2]! - 193.14912866666666) < 1e-9);
        const artifactLink = page.getByRole("link", { name: "Annual input JSON", exact: true });
        assert.equal(
          await artifactLink.getAttribute("href"),
          "/grid-conductor/research/entsoe-fast-targets.json",
        );
      }
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
