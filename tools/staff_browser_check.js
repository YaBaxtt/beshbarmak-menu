const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const fs = require("fs");
const path = require("path");

(async () => {
  const username = process.env.QA_STAFF_USERNAME;
  const password = process.env.QA_STAFF_PASSWORD;
  if (!username || !password) throw new Error("Set QA_STAFF_USERNAME and QA_STAFF_PASSWORD");
  const browser = await chromium.launch({ headless: true, executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("http://127.0.0.1:8000/staff/login/", { waitUntil: "networkidle" });
  await page.locator("#id_username").fill(username);
  await page.locator("#id_password").fill(password);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL("**/staff/");
  await page.getByText("Сегодня", { exact: true }).first().waitFor();
  const dashboardOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  if (dashboardOverflow) throw new Error("Staff dashboard has horizontal overflow");
  const artifactDir = path.join(__dirname, "..", "artifacts");
  fs.mkdirSync(artifactDir, { recursive: true });
  await page.screenshot({ path: path.join(artifactDir, "staff-mobile-390-dashboard.png"), fullPage: true });
  await page.goto("http://127.0.0.1:8000/staff/analytics/?days=7", { waitUntil: "networkidle" });
  if ((await page.locator(".analytics-story .story-card").count()) !== 3) throw new Error("Visual analytics story is missing");
  if (!(await page.getByText("Просмотры, заявки и гости", { exact: true }).count())) throw new Error("Traffic chart is missing");
  const analyticsOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  if (analyticsOverflow) throw new Error("Analytics has horizontal overflow");
  await page.screenshot({ path: path.join(artifactDir, "staff-mobile-390-analytics.png"), fullPage: true });
  await page.goto("http://127.0.0.1:8000/staff/reservations/?tab=new", { waitUntil: "networkidle" });
  const firstReservation = page.locator(".reservation-card .staff-button").first();
  if (await firstReservation.count()) {
    await firstReservation.click();
    for (const label of ["Подтвердить", "Другое время", "Отклонить"]) {
      if (!(await page.getByText(label, { exact: true }).count())) throw new Error(`Staff action is missing: ${label}`);
    }
    const detailOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    if (detailOverflow) throw new Error("Staff reservation detail has horizontal overflow");
    await page.screenshot({ path: path.join(artifactDir, "staff-mobile-390-reservation.png"), fullPage: true });
    await page.getByText("Другое время", { exact: true }).click();
    await page.getByText("Предложить другое время", { exact: true }).waitFor();
  }
  const unexpected = errors.filter((message) => !message.includes("ERR_NETWORK_ACCESS_DENIED"));
  if (unexpected.length) throw new Error(`Staff console errors: ${unexpected.join(" | ")}`);
  await browser.close();
  console.log(JSON.stringify({ staffMobile: "passed", checkedActions: true }, null, 2));
})().catch((error) => { console.error(error); process.exit(1); });
