import { expect, test } from "@playwright/test";
import fs from "node:fs/promises";

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
  await page.getByRole("button", { name: "Retry comparison" }).click();
  await expect(page.getByTestId("one-stop-total")).toHaveText("1113.850 s");
  await page.getByLabel(pit, { exact: true }).fill("41");
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "within each illustrative range",
  );
  await expect(page.getByTestId("lab-results")).toHaveCount(0);
  await page.getByRole("button", { name: "Reset assumptions" }).click();
  await expect(page.getByTestId("one-stop-total")).toHaveText("1113.850 s");
});
