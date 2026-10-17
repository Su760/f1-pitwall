import { expect, test } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";
import { execFileSync } from "node:child_process";

const pit = "Incremental pit loss (s/stop)";
const action = "Find best legal strategy";

test("explicit search acceptance, keyboard focus and downloaded CLI replay", async ({ page }, info) => {
  let calls = 0;
  page.on("request", (req) => { if (req.url().endsWith("/api/v1/lab/optimize")) calls++; });
  await page.goto("/lab");
  await expect(page.getByTestId("one-stop-total")).toHaveText("1113.850 s");
  expect(calls).toBe(0);
  const button = page.getByRole("button", { name: action, exact: true });
  await page.getByRole("button", { name: "Export result record", exact: true }).focus();
  await page.keyboard.press("Tab");
  await expect(button).toBeFocused();
  expect(await button.evaluate((el) => getComputedStyle(el).outlineStyle)).toBe("solid");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("optimized-total")).toHaveText("1113.550 s");
  await expect(button).toBeFocused();
  await expect(page.getByTestId("gain-one-stop")).toHaveText("0.300 s");
  await expect(page.getByTestId("gain-two-stop")).toHaveText("11.150 s");
  await expect(page.getByTestId("optimization-result")).toContainText("529 candidates · 462 legal");
  await expect(page.getByTestId("optimization-result")).toContainText("Pit after lap 5 → medium");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Export optimized scenario" })).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(button).toBeFocused();
  for (const label of ["Export optimized scenario", "Export winning trace", "Export search record"]) {
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: label, exact: true }).click(),
    ]);
    await download.saveAs(info.outputPath(download.suggestedFilename()));
  }
  const root = path.resolve(__dirname, "../..");
  const python = process.env.PITWALL_PYTHON ?? path.join(root, ".venv-api/bin/python");
  const record = JSON.parse(await fs.readFile(info.outputPath("lab-search.json"), "utf8"));
  const scenario = info.outputPath("lab-optimized-scenario.json");
  const trace = JSON.parse(await fs.readFile(info.outputPath("lab-winning-trace.json"), "utf8"));
  expect(record.trace).toEqual(trace);
  expect(record.scenario).toEqual(JSON.parse(await fs.readFile(scenario, "utf8")));
  execFileSync(python, ["-m", "pitwall", "replay", info.outputPath("lab-winning-trace.json"), "--scenario", scenario], { cwd: root });
  for (const file of ["recomputed.json", "recomputed-again.json"]) {
    const stdout = execFileSync(python, ["-m", "pitwall", "optimize", scenario,
      "--top", String(record.search.top_k),
      "--max-candidates", String(record.search.limits.max_candidates),
      "--max-lap-evaluations", String(record.search.limits.max_lap_evaluations),
      "--output", info.outputPath(file)], { cwd: root, encoding: "utf8" });
    expect(stdout).toContain("529 candidates; 462 legal");
    expect(JSON.parse(await fs.readFile(info.outputPath(file), "utf8"))).toEqual(trace);
  }
  expect(await fs.readFile(info.outputPath("recomputed.json"), "utf8"))
    .toEqual(await fs.readFile(info.outputPath("recomputed-again.json"), "utf8"));
  for (const [value, expected] of [["7.15", "1102.700 s"], ["0", "1088.700 s"]]) {
    const before = calls;
    await page.getByLabel(pit, { exact: true }).fill(value);
    await expect(page.getByTestId("optimization-result")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Export winning trace" })).toHaveCount(0);
    await expect(page.getByTestId("one-stop-total")).toHaveText(value === "0" ? "1095.850 s" : "1103.000 s");
    expect(calls).toBe(before);
    await button.click();
    await expect(page.getByTestId("optimized-total")).toHaveText(expected);
  }
  await expect(page.getByTestId("optimization-result")).toContainText("Pit after lap 4 → soft");
  await expect(page.getByTestId("optimization-result")).toContainText("Pit after lap 8 → medium");
  expect(calls).toBe(3);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  expect(await button.evaluate((el) => el.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44);
  await page.locator(".lab-optimization").screenshot({ path: info.outputPath("optimization.png") });
  await page.getByRole("button", { name: "Reset assumptions" }).click();
  await expect(page.getByTestId("optimization-result")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Reset assumptions" })).toBeFocused();
  await expect(page.getByTestId("one-stop-total")).toHaveText("1113.850 s");
  expect(calls).toBe(3);
});

test("in-flight duplicates and stale responses cannot restore reset or edited results", async ({ page }) => {
  let calls = 0;
  let ready!: () => void, release!: () => void, done!: () => void;
  const oldReady = new Promise<void>((r) => (ready = r));
  const oldRelease = new Promise<void>((r) => (release = r));
  const oldDone = new Promise<void>((r) => (done = r));
  await page.route("**/api/v1/lab/optimize", async (route) => {
    calls++;
    if (calls === 1) {
      const response = await route.fetch();
      ready();
      await oldRelease;
      await route.fulfill({ response }).catch(() => {});
      done();
    } else await route.continue();
  });
  await page.goto("/lab");
  const button = page.locator(".lab-search-button");
  await expect(button).toBeVisible();
  // Synchronous duplicate activations exercise the ref before React renders disabled state.
  await button.evaluate((el) => { (el as HTMLButtonElement).click(); (el as HTMLButtonElement).click(); });
  await oldReady;
  expect(calls).toBe(1);
  await expect(button).toHaveAttribute("aria-disabled", "true");
  await button.focus();
  await page.keyboard.press("Enter");
  await page.keyboard.press("Space");
  expect(calls).toBe(1);
  await page.getByLabel(pit, { exact: true }).fill("0");
  await page.getByLabel(pit, { exact: true }).fill("18.0");
  await page.getByRole("button", { name: "Reset assumptions" }).click();
  release();
  await oldDone;
  await expect(page.getByTestId("optimization-result")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Export winning trace" })).toHaveCount(0);
  expect(calls).toBe(1);
  await button.click();
  await expect(page.getByTestId("optimized-total")).toHaveText("1113.550 s");
  await page.getByLabel(pit, { exact: true }).fill("18.0");
  await expect(page.getByTestId("optimization-result")).toHaveCount(0);
  await expect(page.getByTestId("one-stop-total")).toHaveText("1113.850 s");
  expect(calls).toBe(2);
  await button.click();
  await expect(page.getByTestId("optimized-total")).toHaveText("1113.550 s");
  await page.getByLabel("Degradation multiplier", { exact: true }).fill("2");
  await expect(page.getByTestId("optimization-result")).toHaveCount(0);
  await button.click();
  await expect(page.getByTestId("optimization-result")).toContainText("degradation ×2");
  await page.getByLabel("Warm-up multiplier", { exact: true }).fill("0");
  await expect(page.getByTestId("optimization-result")).toHaveCount(0);
  await button.click();
  await expect(page.getByTestId("optimization-result")).toContainText("warm-up ×0");
  await page.getByRole("button", { name: "Reset assumptions" }).click();
  await expect(page.getByTestId("optimization-result")).toHaveCount(0);
  await page.getByLabel(pit, { exact: true }).fill("41");
  await button.focus();
  await page.keyboard.press("Enter");
  await expect(button).toHaveAttribute("aria-disabled", "true");
  expect(calls).toBe(5);
});

test("failure, incomplete response and retry preserve keyboard focus", async ({ page }) => {
  let calls = 0;
  await page.route("**/api/v1/lab/optimize", async (route) => {
    calls++;
    if (calls === 1) await route.fulfill({ status: 503, json: { detail: { message: "Search temporarily unavailable" } } });
    else if (calls === 2) {
      const response = await route.fetch();
      const json = await response.json();
      json.search.search_complete = false;
      await route.fulfill({ json });
    } else await route.continue();
  });
  await page.goto("/lab");
  const button = page.locator(".lab-search-button");
  await button.focus();
  await page.keyboard.press("Space");
  await expect(page.locator(".lab-optimization").getByRole("alert")).toContainText("Search temporarily unavailable");
  await expect(button).toBeFocused();
  await expect(button).toHaveText("Retry strategy search");
  await page.keyboard.press("Enter");
  await expect(page.locator(".lab-optimization").getByRole("alert")).toContainText("No complete result for these assumptions");
  await expect(page.getByTestId("optimization-result")).toHaveCount(0);
  await expect(button).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("optimized-total")).toHaveText("1113.550 s");
  await expect(button).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Export optimized scenario" })).toBeFocused();
  expect(calls).toBe(3);
});

test("a late old search cannot replace a newer winner or its export", async ({ page }, info) => {
  let ready!: () => void, release!: () => void, done!: () => void;
  const readyPromise = new Promise<void>((r) => (ready = r));
  const releasePromise = new Promise<void>((r) => (release = r));
  const donePromise = new Promise<void>((r) => (done = r));
  let first = true;
  await page.route("**/api/v1/lab/optimize", async (route) => {
    if (first) {
      first = false;
      const response = await route.fetch();
      ready();
      await releasePromise;
      await route.fulfill({ response }).catch(() => {});
      done();
    } else await route.continue();
  });
  await page.goto("/lab");
  await page.getByRole("button", { name: action, exact: true }).click();
  await readyPromise;
  await page.getByLabel(pit, { exact: true }).fill("0");
  await page.getByRole("button", { name: action, exact: true }).click();
  await expect(page.getByTestId("optimized-total")).toHaveText("1088.700 s");
  release();
  await donePromise;
  await expect(page.getByTestId("optimized-total")).toHaveText("1088.700 s");
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Export search record" }).click(),
  ]);
  const file = info.outputPath("latest-search.json");
  await download.saveAs(file);
  const record = JSON.parse(await fs.readFile(file, "utf8"));
  expect(record.controls.pit_loss_s).toBe(0);
  expect(record.scenario.configuration.pit_loss_s).toBe(0);
  expect(record.trace.result.total_elapsed_s).toBe(1088.7);
  // Reset clears results even when controls already equal their defaults.
  await page.getByRole("button", { name: "Reset assumptions" }).click();
  await page.getByRole("button", { name: action, exact: true }).click();
  await expect(page.getByTestId("optimized-total")).toHaveText("1113.550 s");
  await page.getByRole("button", { name: "Reset assumptions" }).click();
  await expect(page.getByTestId("optimization-result")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Export search record" })).toHaveCount(0);
});
