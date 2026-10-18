import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";
import { execFileSync } from "node:child_process";

type Trace = {
  trace_version: number;
  strategy: { name: string; stops: { after_lap: number; compound: string }[] };
  configuration: { pit_loss_s: number; laps: number };
  actions: unknown[];
  result: { stints: unknown[]; total_elapsed_s: number };
};
type Entry = {
  rank: number;
  schedule: Trace["strategy"];
  stints: unknown[];
  total_elapsed_s: number;
  trace: Trace;
};
type Record = {
  search: { ranked: Entry[] };
  scenario: { configuration: Trace["configuration"] };
  trace: Trace;
};
const pit = "Incremental pit loss (s/stop)";
const action = "Find best legal strategy";

function assertRankTrace(trace: Trace, entry: Entry, scenario: Record["scenario"]) {
  // CLI validity alone cannot detect a legal trace exported from the wrong rank.
  expect(trace.strategy).toEqual(entry.schedule);
  expect(trace.result.stints).toEqual(entry.stints);
  expect(trace.result.total_elapsed_s).toBe(entry.total_elapsed_s);
  expect(trace.configuration).toEqual(scenario.configuration);
  expect(trace.trace_version).toBe(1);
  expect(trace.actions).toHaveLength(scenario.configuration.laps);
  expect(trace.actions).toEqual(entry.trace.actions);
  expect(trace).toEqual(entry.trace);
}

async function search(page: Page): Promise<Record> {
  const [response] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/api/v1/lab/optimize")),
    page.getByRole("button", { name: action, exact: true }).press("Enter"),
  ]);
  expect(response.ok()).toBeTruthy();
  await expect(page.locator(".lab-ranked-export")).toHaveCount(3);
  return response.json();
}

test("download every retained rank, bind identity, replay and repeat without searching", async ({ page }, info) => {
  test.setTimeout(60_000);
  let searches = 0;
  page.on("request", (r) => { if (r.url().endsWith("/api/v1/lab/optimize")) searches++; });
  await page.goto("/lab");
  await expect(page.getByTestId("one-stop-total")).toHaveText("1113.850 s");
  const root = path.resolve(__dirname, "../..");
  const python = process.env.PITWALL_PYTHON ?? path.join(root, ".venv-api/bin/python");
  for (const value of ["18", "0"]) {
    await page.getByLabel(pit, { exact: true }).fill(value);
    const record = await search(page);
    const before = searches;
    const traces: Trace[] = [], files: string[] = [], bytes: string[] = [];
    for (const entry of record.search.ranked) {
      await page.keyboard.press("Tab");
      const button = page.getByRole("button", { name: "Export rank " + entry.rank + " trace", exact: true });
      await expect(button).toBeFocused();
      await expect(button).toHaveAccessibleName("Export rank " + entry.rank + " trace");
      for (const stop of entry.schedule.stops)
        await expect(button).toHaveAccessibleDescription(new RegExp("Pit after lap " + stop.after_lap + " → " + stop.compound));
      const box = await button.boundingBox();
      expect(box!.height).toBeGreaterThanOrEqual(44);
      expect(box!.width).toBeGreaterThanOrEqual(44);
      expect(await button.evaluate((el) => getComputedStyle(el).outlineStyle)).toBe("solid");
      const name = "lab-rank-" + entry.rank + "-trace.json";
      const [download] = await Promise.all([page.waitForEvent("download"), page.keyboard.press("Enter")]);
      expect(download.suggestedFilename()).toBe(name);
      const file = info.outputPath(value + "-" + name);
      await download.saveAs(file);
      const content = await fs.readFile(file, "utf8");
      const trace: Trace = JSON.parse(content);
      assertRankTrace(trace, entry, record.scenario);
      traces.push(trace); files.push(file); bytes.push(content);
      await expect(button).toBeFocused();
      const [repeat] = await Promise.all([page.waitForEvent("download"), page.keyboard.press("Space")]);
      const repeated = info.outputPath(value + "-repeat-" + name);
      await repeat.saveAs(repeated);
      expect(await fs.readFile(repeated, "utf8")).toBe(content);
      await expect(button).toBeFocused();
      expect(searches).toBe(before);
    }
    await page.keyboard.press("Tab");
    await expect(page.getByRole("button", { name: "Export optimized scenario" })).toBeFocused();
    const [scenarioDownload] = await Promise.all([page.waitForEvent("download"), page.keyboard.press("Enter")]);
    const scenarioFile = info.outputPath(value + "-lab-optimized-scenario.json");
    await scenarioDownload.saveAs(scenarioFile);
    expect(JSON.parse(await fs.readFile(scenarioFile, "utf8"))).toEqual(record.scenario);
    for (const file of files) {
      const stdout = execFileSync(python, ["-m", "pitwall", "replay", file, "--scenario", scenarioFile], { cwd: root, encoding: "utf8" });
      expect(stdout).toContain("VERIFIED trace v1");
    }
    // These real downloads are valid same-scenario traces, but swapping their rank must fail.
    expect(() => assertRankTrace(traces[0], record.search.ranked[1], record.scenario)).toThrow();
    expect(() => assertRankTrace(traces[1], record.search.ranked[0], record.scenario)).toThrow();
    if (value === "0") {
      expect(traces[0].result.total_elapsed_s).toBe(traces[1].result.total_elapsed_s);
      expect(traces[0].strategy).not.toEqual(traces[1].strategy);
      expect(traces[0].actions).not.toEqual(traces[1].actions);
      expect(traces[0].result.stints).not.toEqual(traces[1].result.stints);
    }
    await page.keyboard.press("Tab");
    await expect(page.getByRole("button", { name: "Export rank 1 winning trace", exact: true })).toBeFocused();
    const [winner] = await Promise.all([page.waitForEvent("download"), page.keyboard.press("Enter")]);
    expect(winner.suggestedFilename()).toBe("lab-winning-trace.json");
    const winnerFile = info.outputPath(value + "-lab-winning-trace.json");
    await winner.saveAs(winnerFile);
    expect(await fs.readFile(winnerFile, "utf8")).toBe(bytes[0]);
    expect(traces[0]).toEqual(record.trace);
    await page.keyboard.press("Tab");
    const [searchDownload] = await Promise.all([page.waitForEvent("download"), page.keyboard.press("Enter")]);
    const recordFile = info.outputPath(value + "-lab-search.json");
    await searchDownload.saveAs(recordFile);
    expect(JSON.parse(await fs.readFile(recordFile, "utf8"))).toEqual(record);
    expect(searches).toBe(before);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
    await page.locator(".lab-ranked").screenshot({ path: info.outputPath("exports-pit-" + value + ".png") });
  }
  expect(searches).toBe(2);
});

test("newer rank export survives late response; edits and reset remove every rank export", async ({ page }, info) => {
  let ready!: () => void, release!: () => void, done!: () => void;
  const readyPromise = new Promise<void>((r) => (ready = r));
  const releasePromise = new Promise<void>((r) => (release = r));
  const donePromise = new Promise<void>((r) => (done = r));
  let searches = 0;
  await page.route("**/api/v1/lab/optimize", async (route) => {
    searches++;
    if (searches === 1) {
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
  await expect(page.locator(".lab-ranked-export")).toHaveCount(0);
  const fresh = await search(page);
  const button = page.getByRole("button", { name: "Export rank 2 trace", exact: true });
  async function downloadRank2(filename: string) {
    const [download] = await Promise.all([page.waitForEvent("download"), button.click()]);
    const file = info.outputPath(filename);
    await download.saveAs(file);
    const bytes = await fs.readFile(file, "utf8");
    assertRankTrace(JSON.parse(bytes), fresh.search.ranked[1], fresh.scenario);
    return bytes;
  }
  const before = await downloadRank2("fresh-rank-2.json");
  release();
  await donePromise;
  expect(await downloadRank2("after-late-rank-2.json")).toBe(before);
  expect(JSON.parse(before).configuration.pit_loss_s).toBe(0);
  expect(searches).toBe(2);
  await page.getByLabel(pit, { exact: true }).fill("0.0");
  await expect(page.locator(".lab-ranked-export")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Export search record" })).toHaveCount(0);
  await page.getByRole("button", { name: "Reset assumptions" }).click();
  await expect(page.locator(".lab-ranked-export")).toHaveCount(0);
  expect(searches).toBe(2);
  await search(page);
  await page.getByRole("button", { name: "Reset assumptions" }).click();
  await expect(page.locator(".lab-ranked-export")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Export optimized scenario" })).toHaveCount(0);
  expect(searches).toBe(3);
});
