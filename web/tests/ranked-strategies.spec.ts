import { expect, test, type Page } from "@playwright/test";

const pitLabel = "Incremental pit loss (s/stop)";
const action = "Find best legal strategy";

async function search(page: Page) {
  const [response] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/api/v1/lab/optimize")),
    page.getByRole("button", { name: action, exact: true }).click(),
  ]);
  expect(response.ok()).toBeTruthy();
  await expect(page.locator(".lab-ranked-card")).toHaveCount(3);
  return response.json();
}

test("top-three acceptance, exact ties, server order and shared lap geometry", async ({ page }, info) => {
  await page.goto("/lab");
  await expect(page.locator(".lab-ranked-card")).toHaveCount(0);
  const cases = [
    { pit: "18", totals: ["1113.550", "1113.850", "1114.500"], gaps: ["0.000", "0.300", "0.950"], ties: ["No exact", "No exact", "No exact"] },
    { pit: "7.15", totals: ["1102.700", "1103.000", "1103.000"], gaps: ["0.000", "0.300", "0.300"], ties: ["No exact", "Exact elapsed-time tie with rank 3.", "Exact elapsed-time tie with rank 2."] },
    { pit: "0", totals: ["1088.700", "1088.700", "1089.100"], gaps: ["0.000", "0.000", "0.400"], ties: ["Exact elapsed-time tie with rank 2.", "Exact elapsed-time tie with rank 1.", "No exact"] },
  ];
  for (const c of cases) {
    await page.getByLabel(pitLabel, { exact: true }).fill(c.pit);
    const record = await search(page);
    const cards = page.locator(".lab-ranked-card");
    const geometry = await cards.evaluateAll((items) => items.map((el) => {
      const card = el.getBoundingClientRect();
      const track = el.querySelector(".lab-ranked-track")!.getBoundingClientRect();
      return {
        card: { x: card.x, y: card.y, width: card.width, height: card.height },
        track: { x: track.x, y: track.y, width: track.width },
        segments: Array.from(el.querySelectorAll(".lab-ranked-segment")).map((s) => {
          const box = s.getBoundingClientRect();
          return { x: box.x, width: box.width };
        }),
      };
    }));
    for (let i = 0; i < 3; i++) {
      const card = cards.nth(i), entry = record.search.ranked[i];
      await expect(card.getByRole("heading")).toHaveText("Rank " + entry.rank);
      await expect(page.getByTestId("rank-" + entry.rank + "-total")).toHaveText(c.totals[i] + " s");
      await expect(page.getByTestId("rank-" + entry.rank + "-gap")).toHaveText("Gap to fastest: " + c.gaps[i] + " s");
      await expect(page.getByTestId("rank-" + entry.rank + "-tie")).toContainText(c.ties[i]);
      await expect(card.locator(".lab-ranked-axis span")).toHaveText(Array.from({ length: 12 }, (_, j) => String(j + 1)));
      for (const stop of entry.schedule.stops)
        await expect(card).toContainText("Pit after lap " + stop.after_lap + " → " + stop.compound);
      await expect(card.getByRole("img")).toHaveAccessibleName(/^Rank [123] race-lap timeline:/);
      const { track, segments } = geometry[i];
      expect(track.width).toBeCloseTo(geometry[0].track.width, 1);
      for (let j = 0; j < entry.stints.length; j++) {
        const stint = entry.stints[j];
        await expect(card.locator(".lab-ranked-stints li").nth(j)).toHaveText(stint.compound + ": laps " + stint.first_lap + "–" + stint.last_lap);
        expect(Math.abs(segments[j].x - track.x - track.width * (stint.first_lap - 1) / 12)).toBeLessThan(1);
        expect(Math.abs(segments[j].width - track.width * (stint.last_lap - stint.first_lap + 1) / 12)).toBeLessThan(1);
      }
      if ((page.viewportSize()?.width ?? 0) > 900) {
        expect(geometry[i].card.y).toBe(geometry[0].card.y);
        expect(geometry[i].track.y).toBe(geometry[0].track.y);
        if (i > 0) expect(geometry[i].card.x).toBeGreaterThan(geometry[i - 1].card.x);
      } else {
        expect(geometry[i].card.x).toBe(geometry[0].card.x);
        if (i > 0) expect(geometry[i].card.y).toBeGreaterThanOrEqual(geometry[i - 1].card.y + geometry[i - 1].card.height);
      }
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
    await page.locator(".lab-ranked").screenshot({ path: info.outputPath("top-three-pit-" + c.pit + ".png") });
  }
  const button = page.getByRole("button", { name: action, exact: true });
  await button.focus();
  for (const rank of [1, 2, 3]) {
    await page.keyboard.press("Tab");
    await expect(page.getByRole("button", { name: "Export rank " + rank + " trace", exact: true })).toBeFocused();
  }
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Export optimized scenario" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Export rank 1 winning trace", exact: true })).toBeFocused();
  for (let i = 0; i < 5; i++) await page.keyboard.press("Shift+Tab");
  await expect(button).toBeFocused();
  await page.getByRole("button", { name: "Reset assumptions" }).click();
  await expect(page.locator(".lab-ranked-card")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Export rank 1 winning trace" })).toHaveCount(0);
});

test("rounding cannot manufacture exact elapsed-time ties", async ({ page }, info) => {
  await page.goto("/lab");
  await page.getByLabel(pitLabel, { exact: true }).fill("7.1501");
  const record = await search(page);
  expect(record.search.ranked[1].total_elapsed_s).not.toBe(record.search.ranked[2].total_elapsed_s);
  for (const rank of [2, 3]) {
    await expect(page.getByTestId("rank-" + rank + "-total")).toHaveText("1103.000 s");
    await expect(page.getByTestId("rank-" + rank + "-gap")).toHaveText("Gap to fastest: 0.300 s");
    await expect(page.getByTestId("rank-" + rank + "-tie")).toHaveText("No exact elapsed-time tie among these three.");
    await expect(page.locator(".lab-ranked-card").nth(rank - 1).locator(".lab-ranked-precision"))
      .toContainText(String(record.search.ranked[rank - 1].total_elapsed_s) + " s");
  }
  await expect(page.locator(".lab-ranked")).toContainText("Equal displayed values do not establish an exact tie");
  await page.locator(".lab-ranked").screenshot({ path: info.outputPath("rounded-alike.png") });
  await page.getByLabel(pitLabel, { exact: true }).fill("7.15010");
  await expect(page.locator(".lab-ranked-card")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Export search record" })).toHaveCount(0);
});

test("one-lap stints keep their true scale and readable full labels", async ({ page }, info) => {
  await page.goto("/lab");
  await page.getByLabel("Degradation multiplier", { exact: true }).fill("0");
  await page.getByLabel("Warm-up multiplier", { exact: true }).fill("0");
  const record = await search(page);
  const first = page.locator(".lab-ranked-card").first();
  expect(record.search.ranked[0].stints).toEqual([
    { compound: "soft", first_lap: 1, last_lap: 11 },
    { compound: "medium", first_lap: 12, last_lap: 12 },
  ]);
  const track = await first.locator(".lab-ranked-track").boundingBox();
  const last = await first.locator(".lab-ranked-segment").last().boundingBox();
  expect(Math.abs(last!.width - track!.width / 12)).toBeLessThan(1);
  await expect(first.locator(".lab-ranked-stints")).toContainText("medium: laps 12–12");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.locator(".lab-ranked").screenshot({ path: info.outputPath("one-lap-stints.png") });
  if (info.project.name === "desktop") {
    for (const width of [375, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
      const resizedTrack = await first.locator(".lab-ranked-track").boundingBox();
      const resizedLast = await first.locator(".lab-ranked-segment").last().boundingBox();
      expect(Math.abs(resizedLast!.width - resizedTrack!.width / 12)).toBeLessThan(1);
      // End any scroll from the previous viewport and let resized content paint.
      await page.locator(".lab-ranked").evaluate((el) => el.scrollIntoView({ behavior: "instant", block: "start" }));
      await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
      await expect(first).toBeInViewport();
      await page.locator(".lab-ranked").screenshot({ path: info.outputPath("responsive-" + width + ".png") });
    }
  }
});
