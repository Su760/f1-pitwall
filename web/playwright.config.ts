import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const python =
  process.env.PITWALL_PYTHON ?? path.join(root, ".venv-api/bin/python");

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "desktop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 1000 },
      },
    },
    {
      name: "mobile",
      use: { ...devices["iPhone 13"], defaultBrowserType: "chromium" },
    },
  ],
  webServer: [
    {
      command: `"${python}" -m uvicorn apps.api.app:app --host 127.0.0.1 --port 8000`,
      cwd: root,
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: "npm run start -- --hostname 127.0.0.1 --port 3000",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: false,
      timeout: 60_000,
      env: { NEXT_TELEMETRY_DISABLED: "1" },
    },
  ],
});
