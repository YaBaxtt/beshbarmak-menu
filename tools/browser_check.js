const { chromium } = require("C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const fs = require("fs");
const path = require("path");

(async () => {
  const baseUrl = process.env.QA_BASE_URL || "http://127.0.0.1:8000";
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  });
  const results = [];
  const artifactDir = path.join(__dirname, "..", "artifacts");
  fs.mkdirSync(artifactDir, { recursive: true });

  for (const width of [360, 375, 390, 430, 768, 1024, 1440]) {
    const page = await browser.newPage({ viewport: { width, height: 844 }, deviceScaleFactor: 1 });
    const errors = [];
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    page.on("pageerror", (error) => errors.push(error.message));

    await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" });
    const dimensions = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      scroll: document.documentElement.scrollWidth,
      cards: document.querySelectorAll(".dish-card").length,
      reservationCtas: document.querySelectorAll('a[href^="/reservation/"]').length,
      touchTargets: [...document.querySelectorAll(".lang-button, .category-chip")].map((element) => {
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
    if (dimensions.cards < 20) throw new Error(`Expected the expanded menu, found only ${dimensions.cards} cards`);
    if (!(await page.locator("#promotions .promotion-card").count())) throw new Error("Promotions section is missing");
    if (await page.locator(".available-status").count()) throw new Error("Artificial availability badges are still visible");
    if (dimensions.reservationCtas < 2) throw new Error(`Expected reservation CTAs, found ${dimensions.reservationCtas}`);
    const smallTarget = dimensions.touchTargets.find((target) => target.width < 40 || target.height < 40);
    if (smallTarget) {
      throw new Error(`Touch target is too small at ${width}px: ${smallTarget.label} (${smallTarget.width}x${smallTarget.height}px)`);
    }

    const reservation = await browser.newPage({ viewport: { width, height: width < 700 ? 844 : 1000 }, deviceScaleFactor: 1 });
    const reservationErrors = [];
    reservation.on("console", (message) => { if (message.type() === "error") reservationErrors.push(message.text()); });
    reservation.on("pageerror", (error) => reservationErrors.push(error.message));
    await reservation.goto(`${baseUrl}/reservation/?lang=uz`, { waitUntil: "networkidle" });
    const reservationDimensions = await reservation.evaluate(() => ({ viewport: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
    if (reservationDimensions.scroll > reservationDimensions.viewport) throw new Error(`Reservation overflow at ${width}px: ${reservationDimensions.scroll} > ${reservationDimensions.viewport}`);

    if (width === 390) {
      if (!(await reservation.getByText("Stolingiz sizni kutmoqda", { exact: true }).count())) throw new Error("UZ reservation page did not load");
      const promotionLayout = await page.locator("[data-promotion-track]").evaluate((track) => ({
        cards: track.querySelectorAll("[data-promotion-card]").length,
        scrollable: track.scrollWidth > track.clientWidth,
        topSpread: Math.max(...[...track.querySelectorAll("[data-promotion-card]")].map((card) => card.offsetTop)) - Math.min(...[...track.querySelectorAll("[data-promotion-card]")].map((card) => card.offsetTop)),
      }));
      if (promotionLayout.cards < 3 || !promotionLayout.scrollable || promotionLayout.topSpread > 2) throw new Error(`Promotion carousel layout is invalid: ${JSON.stringify(promotionLayout)}`);
      await page.locator("[data-promotion-next]").click();
      await page.waitForTimeout(450);
      if ((await page.locator('[data-promotion-dot][aria-current="true"]').getAttribute("data-promotion-dot")) !== "1") throw new Error("Promotion next control did not activate the second slide");
      await page.screenshot({ path: path.join(artifactDir, "menu-mobile-390-home.png"), fullPage: false });
      await page.locator('[data-lang="ru"]').click();
      await page.locator("[data-nav-open]").first().click();
      await page.locator(".nav-drawer.open").waitFor();
      await page.waitForTimeout(380);
      for (const label of ["Акции", "О ресторане", "Частые вопросы", "Контакты", "Написать в поддержку"]) {
        if (!(await page.getByText(label, { exact: true }).count())) throw new Error(`Drawer item is missing: ${label}`);
      }
      const routeHref = await page.locator(".drawer-place > a").getAttribute("href");
      if (!routeHref?.includes("yandex")) throw new Error("Yandex route link is missing");
      await page.screenshot({ path: path.join(artifactDir, "menu-mobile-390-drawer.png"), fullPage: false });
      await page.locator(".nav-drawer-close").click();
      await page.locator(".nav-drawer:not(.open)").waitFor();
      await page.locator('[data-lang="ru"]').click();
      const placeholder = await page.locator("#dish-search").getAttribute("placeholder");
      if (placeholder !== "Найти блюдо...") throw new Error("RU language switch failed");
      const russianReservationHref = await page.locator(".top-reservation").getAttribute("href");
      if (!russianReservationHref?.includes("lang=ru")) throw new Error("Reservation link did not inherit RU language");

      await page.locator('[data-lang="uz"]').click();
      const uzbekReservationHref = await page.locator(".top-reservation").getAttribute("href");
      if (!uzbekReservationHref?.includes("lang=uz")) throw new Error("Reservation link did not inherit UZ language");
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
      await page.locator(".sheet-gallery img").first().click();
      await page.locator(".photo-lightbox.open").waitFor();
      const lightboxFit = await page.locator(".photo-lightbox img").evaluate((node) => getComputedStyle(node).objectFit);
      if (lightboxFit !== "contain") throw new Error(`Full photo uses ${lightboxFit} instead of contain`);
      await page.locator(".photo-lightbox-close").click();
      await page.screenshot({ path: path.join(artifactDir, "menu-mobile-390.png"), fullPage: false });
      await page.locator(".sheet-close").click();
      await page.locator(".dish-sheet:not(.open)").waitFor();

      const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
      await reservation.locator("#id_date").fill(tomorrow);
      await reservation.locator("#id_time option:not([value=''])").first().waitFor({ state: "attached" });
      await reservation.locator("#id_time").selectOption({ index: 1 });
      await reservation.locator("#id_guests_count").fill("6");
      await reservation.locator('[data-next="2"]').click();
      await reservation.locator(".space-card:not([disabled])").first().waitFor();
      await reservation.locator(".space-card:not([disabled])").first().click();
      await reservation.locator('[data-next="3"]').click();
      await reservation.locator("#id_customer_name").fill("Браузер QA");
      await reservation.locator("#id_phone").fill("+998 90 000 00 01");
      await reservation.locator("#id_customer_comment").fill("Мобильная проверка");
      await reservation.locator("#preview-button").click();
      await reservation.screenshot({ path: path.join(artifactDir, "reservation-mobile-390-preview.png"), fullPage: true });
      await reservation.locator("#submit-button").click();
      await reservation.waitForURL(/\/reservation\/status\//);
      if (!(await reservation.locator("text=Ariza ko‘rib chiqilmoqda").count())) throw new Error("UZ reservation status page did not load");
      if (await reservation.locator("text=+998 90 000 00 01").count()) throw new Error("Customer phone leaked on public status page");
      await reservation.screenshot({ path: path.join(artifactDir, "reservation-mobile-390-status.png"), fullPage: true });
      await reservation.goto(`${baseUrl}/`, { waitUntil: "networkidle" });
      if (!(await reservation.locator(".last-booking-card:visible").count())) throw new Error("Last booking link was not restored on the menu");
    }

    const unexpectedErrors = errors.filter((message) => !message.includes("ERR_NETWORK_ACCESS_DENIED"));
    if (unexpectedErrors.length) throw new Error(`Browser errors at ${width}px: ${unexpectedErrors.join(" | ")}`);
    results.push({ width, ...dimensions, consoleErrors: errors });
    const unexpectedReservationErrors = reservationErrors.filter((message) => !message.includes("ERR_NETWORK_ACCESS_DENIED"));
    if (unexpectedReservationErrors.length) throw new Error(`Reservation browser errors at ${width}px: ${unexpectedReservationErrors.join(" | ")}`);
    await reservation.close();
    await page.close();
  }

  const info = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await info.goto(`${baseUrl}/about/`, { waitUntil: "networkidle" });
  const infoOverflow = await info.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  if (infoOverflow) throw new Error("Information page has horizontal overflow at 390px");
  if (!(await info.getByText("Частые вопросы", { exact: true }).count())) throw new Error("FAQ section is missing");
  await info.screenshot({ path: path.join(artifactDir, "info-mobile-390.png"), fullPage: true });
  await info.close();

  const desktop = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await desktop.goto(`${baseUrl}/`, { waitUntil: "networkidle" });
  await desktop.screenshot({ path: path.join(artifactDir, "menu-desktop-1440.png"), fullPage: false });
  const shellWidth = await desktop.locator(".app-shell").evaluate((node) => Math.round(node.getBoundingClientRect().width));
  if (shellWidth !== 620) throw new Error(`Desktop app container should be 620px, found ${shellWidth}px`);
  await desktop.close();

  await browser.close();
  console.log(JSON.stringify({ results, shellWidth }, null, 2));
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
