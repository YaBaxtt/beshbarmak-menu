const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const fs = require("fs");
const path = require("path");

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  });
  const results = [];
  const artifactDir = path.join(__dirname, "..", "artifacts");
  fs.mkdirSync(artifactDir, { recursive: true });

  for (const width of [320, 360, 375, 390, 430]) {
    const page = await browser.newPage({ viewport: { width, height: 844 }, deviceScaleFactor: 1 });
    const errors = [];
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    page.on("pageerror", (error) => errors.push(error.message));

    await page.goto("http://127.0.0.1:8000/", { waitUntil: "networkidle" });
    const dimensions = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      scroll: document.documentElement.scrollWidth,
      cards: document.querySelectorAll(".dish-card").length,
      touchTargets: [...document.querySelectorAll(".lang-button, .category-chip, .footer-links a")].map((element) => {
        const rect = element.getBoundingClientRect();
        return {
          label: (element.textContent || "").trim(),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        };
      }),
    }));

    if (dimensions.scroll > dimensions.viewport) {
      throw new Error(`Horizontal overflow at ${width}px: ${dimensions.scroll} > ${dimensions.viewport}`);
    }
    if (dimensions.cards !== 15) throw new Error(`Expected 15 cards, found ${dimensions.cards}`);
    const smallTarget = dimensions.touchTargets.find((target) => target.width < 40 || target.height < 40);
    if (smallTarget) {
      throw new Error(`Touch target is too small at ${width}px: ${smallTarget.label} (${smallTarget.width}x${smallTarget.height}px)`);
    }

    if (width === 390) {
      await page.screenshot({ path: path.join(artifactDir, "menu-mobile-390-home.png"), fullPage: false });
      await page.locator('[data-lang="ru"]').click();
      const placeholder = await page.locator("#dish-search").getAttribute("placeholder");
      if (placeholder !== "Найти блюдо...") throw new Error("RU language switch failed");

      await page.locator('[data-lang="uz"]').click();
      await page.locator("#dish-search").fill("Manti");
      const searchVisible = await page.locator(".dish-card:visible").count();
      if (searchVisible !== 1) throw new Error(`Search returned ${searchVisible} dishes instead of 1`);
      await page.locator(".search-clear").click();

      await page.locator('.category-chip[data-category="shorvalar"]').click();
      const soupVisible = await page.locator(".dish-card:visible").count();
      if (soupVisible !== 3) throw new Error(`Soup filter returned ${soupVisible} dishes instead of 3`);
      await page.locator('.category-chip[data-category="all"]').click();

      await page.locator('.dish-card[data-dish-id="1"]').click();
      await page.locator(".dish-sheet.open").waitFor();
      const title = await page.locator("#sheet-title").textContent();
      if (title !== "Beshbarmak") throw new Error(`Bottom sheet title mismatch: ${title}`);
      await page.screenshot({ path: path.join(artifactDir, "menu-mobile-390.png"), fullPage: false });
      await page.locator(".sheet-close").click();
      await page.locator(".dish-sheet:not(.open)").waitFor();
    }

    const unexpectedErrors = errors.filter((message) => !message.includes("ERR_NETWORK_ACCESS_DENIED"));
    if (unexpectedErrors.length) throw new Error(`Browser errors at ${width}px: ${unexpectedErrors.join(" | ")}`);
    results.push({ width, ...dimensions, consoleErrors: errors });
    await page.close();
  }

  const desktop = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await desktop.goto("http://127.0.0.1:8000/", { waitUntil: "networkidle" });
  await desktop.screenshot({ path: path.join(artifactDir, "menu-desktop-1440.png"), fullPage: false });
  const shellWidth = await desktop.locator(".app-shell").evaluate((node) => Math.round(node.getBoundingClientRect().width));
  if (shellWidth !== 620) throw new Error(`Desktop app shell is ${shellWidth}px, expected 620px`);
  await desktop.close();

  await browser.close();
  console.log(JSON.stringify({ results, shellWidth }, null, 2));
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
