import { expect, test, type Page } from "@playwright/test";

async function skipPlayback(page: Page) {
  const skip = page.getByRole("button", { name: "Skip playback", exact: true });
  const debrief = page.getByRole("heading", { name: "Debrief", exact: true });
  await expect(skip.or(debrief).first()).toBeVisible();
  if (await skip.isVisible()) await skip.click();
  await expect(debrief).toBeVisible();
}

async function submit(page: Page, label: string) {
  const response = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/v1/evaluate") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: label, exact: true }).click();
  const result = await response;
  expect(result.status()).toBe(200);
  return result.json();
}

for (const scenario of [
  { id: "closing-laps", initial: "stay_out", alternative: "pit_soft" },
  { id: "stint-choice", initial: "pit_medium", alternative: "pit_soft" },
  { id: "final-stint", initial: "pit_medium", alternative: "pit_hard" },
]) {
  test(`${scenario.id}: play, debrief, rewind, and retain independent original`, async ({
    page,
  }, testInfo) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    let submissions = 0;
    page.on("request", (request) => {
      if (request.url().endsWith("/api/v1/evaluate")) submissions++;
    });
    await page.goto("/");
    expect(await page.getByRole("heading", { level: 1 }).innerText()).toMatch(
      /Make\s+the call\./,
    );
    expect(
      await page
        .locator(".rail-intro p")
        .filter({ hasText: "One boundary." })
        .innerText(),
    ).toMatch(/One decision\.\s+Find/);
    await page.getByTestId(`challenge-${scenario.id}`).click();
    await expect(page.getByTestId(`action-${scenario.initial}`)).toBeEnabled();
    await expect(page.getByTestId("score")).toHaveCount(0);
    expect(submissions).toBe(0);
    if (scenario.id === "final-stint") {
      await expect(page.getByTestId("action-stay_out")).toBeDisabled();
      await expect(page.getByTestId("action-pit_soft")).toBeDisabled();
    }
    await page.screenshot({
      path: testInfo.outputPath("briefing.png"),
      fullPage: true,
      animations: "disabled",
    });
    await page.getByTestId(`action-${scenario.initial}`).click();
    const original = await submit(page, "Commit pit call");
    expect(original.selected_action).toBe(scenario.initial);
    expect(original.selected.legal).toBe(true);
    await skipPlayback(page);
    await expect(page.getByTestId("score").first()).toContainText(
      original.score_s.toFixed(3),
    );
    await page
      .getByRole("button", { name: "Replay result", exact: true })
      .click();
    await skipPlayback(page);
    await page
      .getByRole("button", { name: "Rewind this call", exact: true })
      .click();
    await page.getByTestId(`action-${scenario.alternative}`).click();
    const branch = await submit(page, "Compare alternative");
    expect(branch.comparison.original_action).toBe(scenario.initial);
    expect(branch.comparison.alternative_action).toBe(scenario.alternative);
    expect(branch.comparison.delta_remaining_s).toBeCloseTo(
      branch.selected.remaining_elapsed_s -
        original.selected.remaining_elapsed_s,
      10,
    );
    await skipPlayback(page);
    await expect(page.getByTestId("original-result")).toContainText(
      original.selected.remaining_elapsed_s.toFixed(3),
    );
    await expect(page.getByTestId("alternative-result")).toContainText(
      branch.selected.remaining_elapsed_s.toFixed(3),
    );
    await expect(page.getByTestId("gap-chart")).toBeVisible();
    await expect(page.getByTestId("history-entry")).toHaveCount(2);
    await page.screenshot({
      path: testInfo.outputPath("comparison.png"),
      fullPage: true,
      animations: "disabled",
    });
    expect(submissions).toBe(2);
    expect(errors).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.reload();
    await page.getByTestId(`challenge-${scenario.id}`).click();
    await expect(page.getByTestId("history-entry")).toHaveCount(2);
  });
}

test("keyboard call controls have visible focus and submit without a mouse", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByTestId("challenge-final-stint").focus();
  await page.keyboard.press("Enter");
  const medium = page.getByTestId("action-pit_medium");
  await expect(medium).toBeEnabled();
  await medium.focus();
  await expect(medium).toBeFocused();
  expect(
    await medium.evaluate((element) => {
      const style = getComputedStyle(element);
      return style.outlineStyle !== "none" || style.boxShadow !== "none";
    }),
  ).toBe(true);
  await page.keyboard.press("Space");
  const commit = page.getByRole("button", {
    name: "Commit pit call",
    exact: true,
  });
  await expect(commit).toBeEnabled();
  await commit.focus();
  await page.keyboard.press("Enter");
  await skipPlayback(page);
});

test("failed submission retries the selected call and duplicate clicks submit once", async ({
  page,
}) => {
  let requests = 0;
  await page.route("**/api/v1/evaluate", async (route) => {
    requests++;
    if (requests === 1) {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({
          detail: {
            code: "unavailable",
            message: "Practice service unavailable; retry this call.",
          },
        }),
      });
    } else {
      await new Promise((resolve) => setTimeout(resolve, 150));
      await route.continue();
    }
  });
  await page.goto("/");
  await page.getByTestId("action-stay_out").click();
  await page
    .getByRole("button", { name: "Commit pit call", exact: true })
    .click();
  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: "Your call has not been recorded" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Retry", exact: true }).dblclick();
  await skipPlayback(page);
  expect(requests).toBe(2);
  await expect(page.getByTestId("history-entry")).toHaveCount(1);
});

test("challenge loading failure offers a working retry", async ({ page }) => {
  let failed = false;
  await page.route("**/api/v1/challenges", async (route) => {
    if (!failed) {
      failed = true;
      await route.abort("failed");
    } else await route.continue();
  });
  await page.goto("/");
  await expect(
    page.getByRole("alert").filter({ hasText: "The pit wall is unavailable" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.getByTestId("action-stay_out")).toBeEnabled();
});

test("blocked local storage does not prevent practice", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "localStorage", {
      get() {
        throw new DOMException("Blocked", "SecurityError");
      },
    });
  });
  await page.goto("/");
  await page.getByTestId("action-stay_out").click();
  await submit(page, "Commit pit call");
  await skipPlayback(page);
  await expect(page.getByTestId("score")).toBeVisible();
});

test("malformed history and a different challenge version are not shown as current practice", async ({
  page,
}) => {
  await page.addInitScript(() => {
    localStorage.setItem("pitwall.practice.v1:closing-laps:1", "{bad JSON");
    localStorage.setItem(
      "pitwall.practice.v1:closing-laps:0",
      JSON.stringify([
        {
          action: "stay_out",
          score_s: 999,
          remaining_s: 999,
          recorded_at: "2026-10-03T00:00:00.000Z",
          fork: false,
        },
      ]),
    );
  });
  await page.goto("/");
  await expect(page.getByTestId("action-stay_out")).toBeEnabled();
  await expect(page.getByTestId("history-entry")).toHaveCount(0);
  await page.getByTestId("action-stay_out").click();
  await submit(page, "Commit pit call");
  await skipPlayback(page);
  await expect(page.getByTestId("history-entry")).toHaveCount(1);
});

test("late challenge response cannot replace the current challenge", async ({
  page,
}) => {
  await page.route(
    "**/api/v1/challenges/stint-choice?version=1",
    async (route) => {
      const response = await route.fetch();
      await new Promise((resolve) => setTimeout(resolve, 350));
      await route.fulfill({ response });
    },
  );
  await page.goto("/");
  await page.getByTestId("challenge-stint-choice").click();
  await page.getByTestId("challenge-final-stint").click();
  await expect(page.getByTestId("action-stay_out")).toBeDisabled();
  await expect(page.getByTestId("action-pit_soft")).toBeDisabled();
  await page.waitForTimeout(500);
  await expect(page.getByTestId("action-stay_out")).toBeDisabled();
  await expect(page.getByTestId("action-pit_medium")).toBeEnabled();
});
