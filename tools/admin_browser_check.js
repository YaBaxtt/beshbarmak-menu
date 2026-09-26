const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const fs = require("fs");
const path = require("path");

(async () => {
  const baseUrl = process.env.QA_BASE_URL || "http://127.0.0.1:8000";
  const username = process.env.QA_ADMIN_USERNAME;
  const password = process.env.QA_ADMIN_PASSWORD;
  if (!username || !password) throw new Error("QA admin credentials are required through environment variables");

  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  const errors = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", (error) => errors.push(error.message));

  await page.goto(`${baseUrl}/admin/login/?next=/admin/`, { waitUntil: "networkidle" });
  await page.locator("#id_username").fill(username);
  await page.locator("#id_password").fill(password);
  await page.locator('button[type="submit"], input[type="submit"]').click();
  await page.waitForURL(/\/admin\/$/);
  for (const label of ["Restoran boshqaruv markazi", "Menyu va sayt", "Bronlar va boshqaruv", "Mehmon fikrlari", "Taom yoqtirishlari"]) {
    if (!(await page.getByText(label, { exact: true }).count())) throw new Error(`Admin label is missing: ${label}`);
  }

  const artifactDir = path.join(__dirname, "..", "artifacts");
  fs.mkdirSync(artifactDir, { recursive: true });
  await page.screenshot({ path: path.join(artifactDir, "admin-dashboard-uz.png"), fullPage: true });

  await page.goto(`${baseUrl}/admin/menu/restaurantsettings/1/change/`, { waitUntil: "networkidle" });
  if (!(await page.getByText("YouTube havolasi", { exact: false }).count())) throw new Error("YouTube setting is missing in admin");
  if (!(await page.getByText("Bron qilish sozlamalari", { exact: false }).count())) throw new Error("Uzbek reservation settings are missing in admin");
  await page.screenshot({ path: path.join(artifactDir, "admin-settings-uz.png"), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${baseUrl}/admin/`, { waitUntil: "networkidle" });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  if (overflow) {
    const offenders = await page.evaluate(() => [...document.querySelectorAll("body *")]
      .map((node) => ({ tag: node.tagName, id: node.id || "", className: node.className || "", parent: node.parentElement?.id || node.parentElement?.className || "", width: node.scrollWidth, right: Math.round(node.getBoundingClientRect().right) }))
      .filter((item) => item.width > document.documentElement.clientWidth || item.right > document.documentElement.clientWidth + 1)
      .slice(0, 12));
    throw new Error(`Admin dashboard has horizontal overflow at 390px: ${JSON.stringify(offenders)}`);
  }
  await page.screenshot({ path: path.join(artifactDir, "admin-mobile-390-uz.png"), fullPage: true });

  if (errors.length) throw new Error(`Admin browser errors: ${errors.join(" | ")}`);
  await browser.close();
  console.log(JSON.stringify({ login: "ok", language: "uz", youtubeSetting: "ok", mobileOverflow: false }));
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
