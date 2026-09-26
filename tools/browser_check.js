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
      dishGridColumns: getComputedStyle(document.querySelector(".dish-grid")).gridTemplateColumns.split(" ").filter(Boolean).length,
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
    if (width <= 430 && dimensions.dishGridColumns !== 2) throw new Error(`Expected two mobile dish columns at ${width}px, found ${dimensions.dishGridColumns}`);
    if (!(await page.getByText("Kategoriyalar", { exact: true }).count())) throw new Error("Category selector heading is missing");
    if (!(await page.getByText("+998 94 636 11 44", { exact: true }).count())) throw new Error("Updated restaurant phone is missing");
    if (await page.locator(".complaint-entry").count()) throw new Error("Complaint button must only be inside the mobile drawer");
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
      const quickActionLayout = await page.locator(".quick-actions").evaluate((container) => {
        const reservationAction = container.querySelector(".reservation-action").getBoundingClientRect();
        const socialActions = [...container.querySelectorAll(".telegram-action, .instagram-action, .youtube-action")];
        return {
          containerWidth: Math.round(container.getBoundingClientRect().width),
          reservationWidth: Math.round(reservationAction.width),
          socialCount: socialActions.length,
        };
      });
      if (quickActionLayout.socialCount !== 3) throw new Error(`Expected Telegram, Instagram and YouTube actions: ${JSON.stringify(quickActionLayout)}`);
      if (quickActionLayout.reservationWidth < quickActionLayout.containerWidth - 2) throw new Error(`Reservation action is not full-width: ${JSON.stringify(quickActionLayout)}`);
      const youtubeHref = await page.locator(".youtube-action").getAttribute("href");
      if (!youtubeHref?.includes("youtube.com")) throw new Error("YouTube action URL is missing");
      await page.screenshot({ path: path.join(artifactDir, "menu-mobile-390-actions.png"), fullPage: false });
      await page.screenshot({ path: path.join(artifactDir, "menu-mobile-390-home.png"), fullPage: false });
      await page.locator('[data-lang="ru"]').click();
      await page.locator("[data-nav-open]").first().click();
      await page.locator(".nav-drawer.open").waitFor();
      await page.waitForTimeout(380);
      for (const label of ["О ресторане", "Частые вопросы", "Контакты", "Написать отзыв", "Отправить жалобу", "Написать в поддержку"]) {
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
      await page.locator("#dish-search").fill("Beshbarmoq");
      const searchVisible = await page.locator(".dish-card:visible").count();
      if (searchVisible !== 1) throw new Error(`Search returned ${searchVisible} dishes instead of 1`);
      await page.locator(".search-clear").click();

      await page.locator('.category-chip[data-category="salatlar"]').click();
      const saladVisible = await page.locator(".dish-card:visible").count();
      if (saladVisible !== 8) throw new Error(`Salad filter returned ${saladVisible} dishes instead of 8`);
      await page.locator('.category-chip[data-category="all"]').click();
      await page.locator('[data-menu-section="beshbarmoq"]').scrollIntoViewIfNeeded();
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(artifactDir, "menu-mobile-390-catalog.png"), fullPage: false });

      const firstDish = page.locator(".dish-card").first();
      const cardLayout = await firstDish.evaluate((card) => {
        const title = card.querySelector("h3").getBoundingClientRect();
        const description = card.querySelector("p").getBoundingClientRect();
        const like = card.querySelector(".dish-like-button").getBoundingClientRect();
        return { titleBottom: title.bottom, descriptionBottom: description.bottom, likeTop: like.top };
      });
      if (cardLayout.likeTop < cardLayout.descriptionBottom - 1) throw new Error(`Dish like is not below the description: ${JSON.stringify(cardLayout)}`);
      const dishId = await firstDish.getAttribute("data-dish-id");
      const likeButton = firstDish.locator(".dish-like-button");
      const likesBefore = Number(await likeButton.locator("[data-like-count]").textContent());
      await Promise.all([
        page.waitForResponse((response) => response.url().includes(`/dish/${dishId}/like/`) && response.request().method() === "POST"),
        likeButton.click(),
      ]);
      if (!(await likeButton.getAttribute("class")).includes("liked")) throw new Error("Dish like did not become active");
      if (Number(await likeButton.locator("[data-like-count]").textContent()) !== likesBefore + 1) throw new Error("Dish like counter did not increase");
      await Promise.all([
        page.waitForResponse((response) => response.url().includes(`/dish/${dishId}/like/`) && response.request().method() === "POST"),
        likeButton.click(),
      ]);
      if ((await likeButton.getAttribute("class")).includes("liked")) throw new Error("Second like click did not remove the like");

      await firstDish.click();
      await page.locator(".dish-sheet.open").waitFor();
      await page.waitForTimeout(420);
      const title = await page.locator("#sheet-title").textContent();
      if (title !== "Beshbarmoq") throw new Error(`Bottom sheet title mismatch: ${title}`);
      if (await page.locator(".sheet-price:visible").count()) throw new Error("Price is displayed for Beshbarmoq even though none was supplied");
      if (await page.locator(".sheet-details:visible").count()) throw new Error("Empty portion or badge details are visible");
      if (!(await page.locator(".sheet-description:visible").count())) throw new Error("Dish description is missing");
      if ((await page.locator(".sheet-actions > *:visible").count()) !== 3) throw new Error("Dish actions are incomplete");
      await page.screenshot({ path: path.join(artifactDir, "menu-mobile-390.png"), fullPage: false });
      await page.locator(".sheet-close").click();
      await page.locator(".dish-sheet:not(.open)").waitFor();
      await page.waitForTimeout(400);

      await page.locator("#reviews").scrollIntoViewIfNeeded();
      await page.locator('label[for="rating-5"]').click();
      await page.locator('#review-form input[name="guest_name"]').fill("Browser QA");
      await page.locator('#review-form textarea[name="text"]').fill("Saytdagi fikr yuborish shakli mobil qurilmada tekshirildi.");
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(artifactDir, "reviews-mobile-390.png"), fullPage: false });
      await Promise.all([
        page.waitForURL(/review=sent/),
        page.locator("#review-form .review-submit").click(),
      ]);
      if (!(await page.locator(".review-message.success").count())) throw new Error("Review confirmation is missing");

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
  if (!(await info.getByText("Ko‘p beriladigan savollar", { exact: true }).count())) throw new Error("Default UZ FAQ section is missing");
  await info.screenshot({ path: path.join(artifactDir, "info-mobile-390-uz.png"), fullPage: true });
  await info.goto(`${baseUrl}/about/?lang=ru`, { waitUntil: "networkidle" });
  if (!(await info.getByText("Частые вопросы", { exact: true }).count())) throw new Error("RU FAQ section is missing");
  await info.close();

  const complaint = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await complaint.goto(`${baseUrl}/complaint/`, { waitUntil: "networkidle" });
  const complaintOverflow = await complaint.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  if (complaintOverflow) throw new Error("Complaint page has horizontal overflow at 390px");
  if (!(await complaint.getByText("Muammo haqida anonim xabar bering", { exact: true }).count())) throw new Error("Default UZ complaint page is missing");
  if ((await complaint.locator('input[name="reason"]').count()) !== 8) throw new Error("Complaint reasons are incomplete");
  const options = await complaint.locator('#id_space option').allTextContents();
  for (const expected of ["Stol-stulli zal", "Katta zal", "Oddiy xona", "Tapchan"]) {
    if (!options.some((label) => label.includes(expected))) throw new Error(`Complaint space option is missing: ${expected}`);
  }
  await complaint.locator('input[name="reason"]').first().check();
  await complaint.locator('#id_space').selectOption({ label: options.find((label) => label.includes("Tapchan")) });
  await complaint.locator('#id_place_details').fill("QA tapchan");
  await complaint.locator('#id_description').fill("Mobil shakl orqali anonim shikoyat tekshiruvi.");
  await complaint.screenshot({ path: path.join(artifactDir, "complaint-mobile-390.png"), fullPage: true });
  await complaint.locator('#complaint-submit').click();
  await complaint.waitForURL(/\/complaint\/\?lang=uz&sent=1/);
  if (!(await complaint.getByText("Xabaringiz qabul qilindi", { exact: true }).count())) throw new Error("Complaint success state is missing");
  await complaint.close();

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
