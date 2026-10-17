import { expect, test } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";
import { execFileSync } from "node:child_process";

const pit = "Incremental pit loss (s/stop)";
test("lab discovery, reversal, tie, scaling controls, reset and exports", async ({
  page,
}, info) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Sensitivity lab" }).click();
  await expect(page).toHaveURL(/\/lab$/);
  await expect(page.getByTestId("one-stop-total")).toHaveText("1113.850 s");
  await expect(page.getByTestId("two-stop-total")).toHaveText("1124.700 s");
  await expect(page.getByTestId("lab-delta")).toHaveText("Δ +10.850 s");
  await page.getByLabel(pit, { exact: true }).fill("0");
  await expect(page.getByTestId("one-stop-total")).toHaveText("1095.850 s");
  await expect(page.getByTestId("two-stop-total")).toHaveText("1088.700 s");
  await expect(page.locator(".lab-verdict")).toContainText(
    "two-stop faster among these two schedules",
  );
  await page.getByLabel(pit, { exact: true }).fill("7.15");
  await expect(page.getByTestId("one-stop-total")).toHaveText("1103.000 s");
  await expect(page.getByTestId("two-stop-total")).toHaveText("1103.000 s");
  await expect(page.locator(".lab-verdict")).toContainText("Numerical tie");
  await page.getByLabel("Degradation multiplier", { exact: true }).fill("2");
  await page.getByLabel("Warm-up multiplier", { exact: true }).fill("0");
  await expect(page.getByTestId("lab-results")).toContainText("warm-up ×0");
  await page.getByRole("button", { name: "Reset assumptions" }).click();
  await expect(page.getByTestId("one-stop-total")).toHaveText("1113.850 s");
  await expect(
    page.getByLabel("Degradation multiplier", { exact: true }),
  ).toHaveValue("1");
  await expect(
    page.getByLabel("Warm-up multiplier", { exact: true }),
  ).toHaveValue("1");
  // Equivalent numeric text still must resolve after results are invalidated.
  await page.getByLabel(pit, { exact: true }).fill("18.0");
  await expect(page.getByTestId("one-stop-total")).toHaveText("1113.850 s");
  await expect(page.locator(".lab-cell")).toHaveCount(441);
  await page.locator(".lab-cell").first().focus();
  await expect(page.locator(".lab-point")).toContainText(
    "Pit 0 s, degradation 3",
  );
  for (const label of ["Export scenario", "Export result record"]) {
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: label, exact: true }).click(),
    ]);
    const file = info.outputPath(download.suggestedFilename());
    await download.saveAs(file);
    const parsed = JSON.parse(await fs.readFile(file, "utf8"));
    if (label === "Export scenario")
      expect(parsed.configuration.pit_loss_s).toBe(18);
    else {
      expect(parsed.lab_version).toBe(1);
      expect(parsed.grid.rows.flat()).toHaveLength(441);
      expect(parsed.comparison.strategies[0].total_elapsed_s).toBe(1113.85);
    }
  }
  const root = path.resolve(__dirname, "../..");
  const python =
    process.env.PITWALL_PYTHON ?? path.join(root, ".venv-api/bin/python");
  for (const [flag, input, output] of [
    ["--scenario", "lab-scenario.json", "comparison.json"],
    ["--record", "lab-result.json", "verified.json"],
    ["--record", "lab-result.json", "verified-again.json"],
  ])
    execFileSync(
      python,
      [
        "-m",
        "pitwall.sensitivity",
        flag,
        info.outputPath(input),
        "--output",
        info.outputPath(output),
      ],
      { cwd: root },
    );
  const record = JSON.parse(
    await fs.readFile(info.outputPath("lab-result.json"), "utf8"),
  );
  expect(
    JSON.parse(await fs.readFile(info.outputPath("comparison.json"), "utf8")),
  ).toEqual(record.comparison);
  expect(
    JSON.parse(await fs.readFile(info.outputPath("verified.json"), "utf8")),
  ).toEqual(record);
  expect(await fs.readFile(info.outputPath("verified.json"), "utf8")).toEqual(
    await fs.readFile(info.outputPath("verified-again.json"), "utf8"),
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: info.outputPath("lab-full.png"),
    fullPage: true,
  });
});

test("superseded responses cannot replace newer results", async ({ page }) => {
  let ready!: () => void, release!: () => void, done!: () => void;
  const oldReady = new Promise<void>((r) => (ready = r)),
    oldRelease = new Promise<void>((r) => (release = r)),
    oldDone = new Promise<void>((r) => (done = r));
  await page.route("**/api/v1/lab", async (route) => {
    if (
      route.request().method() === "POST" &&
      route.request().postDataJSON().pit_loss_s === 40
    ) {
      const response = await route.fetch();
      ready();
      await oldRelease;
      await route.fulfill({ response }).catch(() => {});
      done();
    } else await route.continue();
  });
  await page.goto("/lab");
  await expect(page.getByTestId("one-stop-total")).toHaveText("1113.850 s");
  await page.getByLabel(pit, { exact: true }).fill("40");
  await oldReady;
  await page.getByLabel(pit, { exact: true }).fill("0");
  await expect(page.getByTestId("lab-results")).toHaveCount(0);
  await expect(page.getByTestId("one-stop-total")).toHaveText("1095.850 s");
  release();
  await oldDone;
  await expect(page.getByTestId("one-stop-total")).toHaveText("1095.850 s");
  await expect(page.getByTestId("lab-results")).toContainText(
    "Resolved: pit 0 s",
  );
});

test("errors retry and invalid input hides prior results", async ({ page }) => {
  let fail = true;
  await page.route("**/api/v1/lab", async (route) => {
    if (fail && route.request().method() === "POST") {
      fail = false;
      await route.fulfill({
        status: 503,
        json: { detail: { message: "Temporary lab failure" } },
      });
    } else await route.continue();
  });
  await page.goto("/lab");
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "Temporary lab failure",
  );
  await page.getByRole("button", { name: "Retry comparison" }).focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("button", { name: "Reset assumptions" }),
  ).toBeFocused();
  await expect(page.getByTestId("one-stop-total")).toHaveText("1113.850 s");
  await page.getByLabel(pit, { exact: true }).fill("41");
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "within each illustrative range",
  );
  await expect(page.getByTestId("lab-results")).toHaveCount(0);
  await page.getByRole("button", { name: "Reset assumptions" }).click();
  await expect(page.getByTestId("one-stop-total")).toHaveText("1113.850 s");
});

test("map keyboard navigation has one entry and predictable exit and refresh", async ({
  page,
}) => {
  test.setTimeout(60_000);
  await page.goto("/lab");
  const grid = page.getByRole("grid", { name: "Where the preference changes" });
  await expect(grid).toBeVisible();
  const cells = grid.getByRole("button");
  const reset = page.getByRole("button", { name: "Reset assumptions" });
  const exportScenario = page.getByRole("button", {
    name: "Export scenario",
    exact: true,
  });
  await expect(cells).toHaveCount(441);
  await expect(grid.locator('button[tabindex="0"]')).toHaveCount(1);
  await reset.focus();
  await page.keyboard.press("Tab");
  await expect(cells.first()).toBeFocused();
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("ArrowUp");
  await expect(cells.first()).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await expect(cells.nth(1)).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(cells.nth(22)).toBeFocused();
  await page.keyboard.press("Home");
  await expect(cells.nth(21)).toBeFocused();
  await page.keyboard.press("End");
  await expect(cells.nth(41)).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await expect(cells.nth(41)).toBeFocused();
  await page.keyboard.press("Control+End");
  await expect(cells.last()).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(cells.last()).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(exportScenario).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(cells.last()).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(reset).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(cells.last()).toBeFocused();
  await page.keyboard.press("Control+Home");
  await expect(cells.first()).toBeFocused();
  // Every sample is reachable through directional navigation, not just DOM focus.
  await page.evaluate(() => {
    document.querySelectorAll(".lab-cell").forEach((el) => {
      el.addEventListener("focus", () =>
        el.setAttribute("data-visited", "yes"),
      );
    });
  });
  await cells.last().click();
  await expect(grid.locator('button[tabindex="0"]')).toHaveCount(1);
  await page.keyboard.press("Control+Home");
  for (let row = 0; row < 21; row++) {
    for (let col = 1; col < 21; col++) await page.keyboard.press("ArrowRight");
    if (row < 20) {
      await page.keyboard.press("ArrowDown");
      await page.keyboard.press("Home");
    }
  }
  await expect(grid.locator('[data-visited="yes"]')).toHaveCount(441);
  const view = await cells.last().evaluate((el) => {
    const cell = el.getBoundingClientRect(),
      header = el.closest("tr")!.querySelector("th")!.getBoundingClientRect();
    const container = el.closest(".lab-map-scroll")!.getBoundingClientRect();
    const columnHeader = el
      .closest("table")!
      .querySelector("thead th:last-child")!
      .getBoundingClientRect();
    return {
      width: cell.width,
      height: cell.height,
      visible: cell.left >= header.right && cell.right <= container.right + 1,
      headerVisible:
        header.left >= container.left && header.right <= container.right,
      columnVisible:
        columnHeader.top >= container.top && columnHeader.bottom <= cell.top,
      cellWithinViewport: cell.bottom <= container.bottom + 1,
      outline: getComputedStyle(el).outlineStyle,
    };
  });
  expect(view.width).toBeGreaterThanOrEqual(44);
  expect(view.height).toBeGreaterThanOrEqual(44);
  expect(view.visible).toBeTruthy();
  expect(view.headerVisible).toBeTruthy();
  expect(view.columnVisible).toBeTruthy();
  expect(view.cellWithinViewport).toBeTruthy();
  expect(view.outline).toBe("solid");
  await page.getByLabel(pit, { exact: true }).fill("0");
  await expect(page.getByTestId("one-stop-total")).toHaveText("1095.850 s");
  await expect(page.getByLabel(pit, { exact: true })).toBeFocused();
  await expect(grid.locator('button[tabindex="0"]')).toHaveCount(1);
  await expect(cells.first()).toHaveAttribute("tabindex", "0");
  await reset.click();
  await expect(page.getByTestId("one-stop-total")).toHaveText("1113.850 s");
  await expect(reset).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(cells.first()).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(exportScenario).toBeFocused();
});

test("setup retry keeps keyboard focus on a persistent target", async ({
  page,
}) => {
  let fail = true;
  await page.route("**/api/v1/lab", async (route) => {
    if (fail && route.request().method() === "GET") {
      fail = false;
      await route.fulfill({
        status: 503,
        json: { detail: { message: "Temporary setup failure" } },
      });
    } else await route.continue();
  });
  await page.goto("/lab");
  await page.getByRole("button", { name: "Retry lab setup" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
  await expect(page.getByTestId("one-stop-total")).toHaveText("1113.850 s");
  await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel(pit, { exact: true })).toBeFocused();
});
