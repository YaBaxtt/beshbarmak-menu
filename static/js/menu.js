(() => {
  "use strict";

  const dishDataNode = document.getElementById("dish-data");
  const dishes = dishDataNode ? JSON.parse(dishDataNode.textContent) : {};
  const langButtons = [...document.querySelectorAll(".lang-button")];
  const searchableCards = [...document.querySelectorAll(".dish-card")];
  const popularCards = [...document.querySelectorAll(".popular-card")];
  const sections = [...document.querySelectorAll("[data-menu-section]")];
  const categoryButtons = [...document.querySelectorAll(".category-chip")];
  const search = document.getElementById("dish-search");
  const clearSearch = document.querySelector(".search-clear");
  const emptyState = document.querySelector(".empty-state");
  const emptyButton = emptyState?.querySelector("button");
  const popularSection = document.getElementById("popular-section");

  const overlay = document.querySelector(".sheet-overlay");
  const sheet = document.querySelector(".dish-sheet");
  const sheetClose = document.querySelector(".sheet-close");
  const gallery = document.querySelector(".sheet-gallery");
  const galleryDots = document.querySelector(".gallery-dots");
  const sheetCategory = document.querySelector(".sheet-category");
  const sheetTitle = document.getElementById("sheet-title");
  const sheetPrice = document.querySelector(".sheet-price");
  const sheetStatus = document.querySelector(".sheet-status");
  const sheetWeight = document.querySelector(".sheet-weight");
  const sheetDescription = document.querySelector(".sheet-description");
  const lightbox = document.querySelector(".photo-lightbox");
  const lightboxImage = lightbox?.querySelector("img");
  const lightboxClose = lightbox?.querySelector(".photo-lightbox-close");
  const lastBookingCard = document.querySelector(".last-booking-card");
  const lastBookingNumber = document.querySelector(".last-booking-number");
  const lastBookingLink = document.querySelector("[data-last-booking-link]");
  const drawerLastBooking = document.querySelector("[data-drawer-last-booking]");
  const lastBookingDismiss = document.querySelector("[data-last-booking-dismiss]");
  const promotionCarousel = document.querySelector("[data-promotion-carousel]");
  const promotionTrack = document.querySelector("[data-promotion-track]");
  const promotionCards = [...document.querySelectorAll("[data-promotion-card]")];
  const promotionDots = [...document.querySelectorAll("[data-promotion-dot]")];
  const promotionPrevious = document.querySelector("[data-promotion-previous]");
  const promotionNext = document.querySelector("[data-promotion-next]");

  let currentLang = localStorage.getItem("menu-language") === "ru" ? "ru" : "uz";
  let currentCategory = "all";
  let openDishId = null;
  let previousFocus = null;

  const normalize = (value) => (value || "")
    .toLocaleLowerCase(currentLang === "ru" ? "ru" : "uz")
    .replace(/[‘’`ʻ]/g, "'")
    .trim();

  const formatPrice = (value) => Number(value).toLocaleString("ru-RU").replace(/\u00a0/g, " ");

  function updateLastBooking() {
    const savedUrl = localStorage.getItem("last-reservation-url") || "";
    const savedNumber = localStorage.getItem("last-reservation-number") || "";
    const valid = savedUrl.startsWith("/reservation/status/");
    if (!valid) {
      if (lastBookingCard) lastBookingCard.hidden = true;
      if (drawerLastBooking) drawerLastBooking.hidden = true;
      return;
    }
    const separator = savedUrl.includes("?") ? "&" : "?";
    const localizedUrl = `${savedUrl}${separator}lang=${currentLang}`;
    if (lastBookingNumber) lastBookingNumber.textContent = savedNumber || (currentLang === "uz" ? "Mening bronim" : "Моя бронь");
    if (lastBookingLink) lastBookingLink.href = localizedUrl;
    if (drawerLastBooking) drawerLastBooking.href = localizedUrl;
    if (lastBookingCard) lastBookingCard.hidden = false;
    if (drawerLastBooking) drawerLastBooking.hidden = false;
  }

  function applyLanguage(lang) {
    currentLang = lang;
    document.documentElement.lang = lang;
    localStorage.setItem("menu-language", lang);
    document.cookie = `site_language=${lang}; Max-Age=31536000; Path=/; SameSite=Lax`;

    document.querySelectorAll('a[href^="/reservation/"]').forEach((link) => {
      const url = new URL(link.href, window.location.origin);
      url.searchParams.set("lang", lang);
      link.href = `${url.pathname}${url.search}${url.hash}`;
    });

    document.querySelectorAll("[data-i18n]").forEach((node) => {
      const value = node.dataset[lang];
      if (value !== undefined) node.textContent = value;
    });

    if (search) search.placeholder = lang === "uz" ? search.dataset.placeholderUz : search.dataset.placeholderRu;
    langButtons.forEach((button) => {
      const active = button.dataset.lang === lang;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });

    document.title = lang === "uz"
      ? `${document.querySelector("h1")?.textContent || "Beshbarmak"} — Milliy taomlar menyusi`
      : `${document.querySelector("h1")?.textContent || "Beshbarmak"} — Меню национальной кухни`;

    if (openDishId) renderSheet(dishes[openDishId]);
    updateLastBooking();
    filterMenu();
  }

  function filterMenu() {
    const query = normalize(search?.value);
    let visibleCount = 0;

    searchableCards.forEach((card) => {
      const matchesText = !query || normalize(card.dataset.search).includes(query);
      const matchesCategory = currentCategory === "all" || card.dataset.category === currentCategory;
      const visible = matchesText && matchesCategory;
      card.hidden = !visible;
      if (visible) visibleCount += 1;
    });

    sections.forEach((section) => {
      section.hidden = !section.querySelector(".dish-card:not([hidden])");
    });

    if (popularSection) {
      let visiblePopular = 0;
      popularCards.forEach((card) => {
        const matchesText = !query || normalize(card.dataset.search).includes(query);
        const matchesCategory = currentCategory === "all" || card.dataset.category === currentCategory;
        const visible = matchesText && matchesCategory;
        card.hidden = !visible;
        if (visible) visiblePopular += 1;
      });
      popularSection.hidden = visiblePopular === 0 || Boolean(query);
    }

    if (emptyState) emptyState.hidden = visibleCount !== 0;
    clearSearch?.classList.toggle("visible", Boolean(search?.value));
  }

  function renderSheet(dish) {
    if (!dish) return;
    const images = dish.images || [];
    gallery.replaceChildren();
    galleryDots.replaceChildren();

    if (images.length) {
      images.forEach((src, index) => {
        const image = document.createElement("img");
        image.src = src;
        image.alt = dish[`name_${currentLang}`];
        image.loading = index === 0 ? "eager" : "lazy";
        gallery.appendChild(image);

        if (images.length > 1) {
          const dot = document.createElement("i");
          if (index === 0) dot.classList.add("active");
          galleryDots.appendChild(dot);
        }
      });
    } else {
      const placeholder = document.createElement("div");
      placeholder.className = "image-placeholder";
      placeholder.innerHTML = `<span>✦</span><small>${currentLang === "uz" ? "Rasm tez orada" : "Фото скоро"}</small>`;
      gallery.appendChild(placeholder);
    }

    gallery.scrollLeft = 0;
    sheetCategory.textContent = dish[`category_${currentLang}`];
    sheetTitle.textContent = dish[`name_${currentLang}`];
    sheetPrice.innerHTML = `${formatPrice(dish.price)} <small>so‘m</small>`;
    sheetDescription.textContent = dish[`description_${currentLang}`];
    sheetWeight.textContent = dish.weight || (currentLang === "uz" ? "Ko‘rsatilmagan" : "Не указано");
    sheetStatus.textContent = dish.available ? "" : (currentLang === "uz" ? "● Hozir mavjud emas" : "● Сейчас нет");
    sheetStatus.hidden = dish.available;
    sheetStatus.classList.toggle("unavailable", !dish.available);
  }

  function openLightbox(image) {
    if (!lightbox || !lightboxImage || !image?.src) return;
    lightboxImage.src = image.currentSrc || image.src;
    lightboxImage.alt = image.alt;
    lightbox.classList.add("open");
    lightbox.setAttribute("aria-hidden", "false");
    document.body.classList.add("lightbox-open");
    lightboxClose?.focus();
  }

  function closeLightbox() {
    if (!lightbox?.classList.contains("open")) return;
    lightbox.classList.remove("open");
    lightbox.setAttribute("aria-hidden", "true");
    document.body.classList.remove("lightbox-open");
  }

  function initPromotionCarousel() {
    if (!promotionTrack || promotionCards.length < 2) return;
    let currentIndex = 0;
    let timer = null;
    let scrollTimer = null;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const setActive = (index) => {
      currentIndex = (index + promotionCards.length) % promotionCards.length;
      promotionDots.forEach((dot, dotIndex) => {
        const active = dotIndex === currentIndex;
        dot.classList.toggle("active", active);
        dot.setAttribute("aria-current", active ? "true" : "false");
      });
    };

    const goTo = (index, behavior = "smooth") => {
      const normalized = (index + promotionCards.length) % promotionCards.length;
      const card = promotionCards[normalized];
      const left = card.offsetLeft - (promotionTrack.clientWidth - card.clientWidth) / 2;
      promotionTrack.scrollTo({ left, behavior });
      setActive(normalized);
    };

    const stopAuto = () => {
      if (timer) window.clearInterval(timer);
      timer = null;
    };
    const startAuto = () => {
      stopAuto();
      if (!reducedMotion && !document.hidden) timer = window.setInterval(() => goTo(currentIndex + 1), 5500);
    };

    promotionPrevious?.addEventListener("click", () => { goTo(currentIndex - 1); startAuto(); });
    promotionNext?.addEventListener("click", () => { goTo(currentIndex + 1); startAuto(); });
    promotionDots.forEach((dot) => dot.addEventListener("click", () => { goTo(Number(dot.dataset.promotionDot)); startAuto(); }));
    promotionTrack.addEventListener("scroll", () => {
      window.clearTimeout(scrollTimer);
      scrollTimer = window.setTimeout(() => {
        const center = promotionTrack.scrollLeft + promotionTrack.clientWidth / 2;
        const nearest = promotionCards.reduce((best, card, index) => {
          const distance = Math.abs(card.offsetLeft + card.clientWidth / 2 - center);
          return distance < best.distance ? { index, distance } : best;
        }, { index: 0, distance: Number.POSITIVE_INFINITY });
        setActive(nearest.index);
      }, 80);
    }, { passive: true });
    promotionCarousel?.addEventListener("pointerenter", stopAuto);
    promotionCarousel?.addEventListener("pointerleave", startAuto);
    promotionCarousel?.addEventListener("focusin", stopAuto);
    promotionCarousel?.addEventListener("focusout", startAuto);
    document.addEventListener("visibilitychange", () => document.hidden ? stopAuto() : startAuto());
    setActive(0);
    startAuto();
  }

  function openSheet(id, trigger) {
    const dish = dishes[id];
    if (!dish) return;
    openDishId = id;
    previousFocus = trigger;
    renderSheet(dish);
    document.body.classList.add("sheet-open");
    overlay.classList.add("open");
    sheet.classList.add("open");
    overlay.setAttribute("aria-hidden", "false");
    sheet.setAttribute("aria-hidden", "false");
    window.setTimeout(() => sheetClose.focus(), 260);
  }

  function closeSheet() {
    if (!sheet.classList.contains("open")) return;
    document.body.classList.remove("sheet-open");
    overlay.classList.remove("open");
    sheet.classList.remove("open");
    overlay.setAttribute("aria-hidden", "true");
    sheet.setAttribute("aria-hidden", "true");
    openDishId = null;
    window.setTimeout(() => previousFocus?.focus(), 220);
  }

  langButtons.forEach((button) => button.addEventListener("click", () => applyLanguage(button.dataset.lang)));

  categoryButtons.forEach((button) => {
    button.addEventListener("click", () => {
      currentCategory = button.dataset.category;
      categoryButtons.forEach((item) => item.classList.toggle("active", item === button));
      button.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
      filterMenu();
    });
  });

  search?.addEventListener("input", filterMenu);
  clearSearch?.addEventListener("click", () => {
    search.value = "";
    search.focus();
    filterMenu();
  });
  emptyButton?.addEventListener("click", () => {
    search.value = "";
    currentCategory = "all";
    categoryButtons.forEach((button) => button.classList.toggle("active", button.dataset.category === "all"));
    filterMenu();
    search.focus();
  });
  lastBookingDismiss?.addEventListener("click", () => {
    localStorage.removeItem("last-reservation-url");
    localStorage.removeItem("last-reservation-number");
    updateLastBooking();
  });

  document.querySelectorAll(".dish-trigger").forEach((trigger) => {
    trigger.addEventListener("click", () => openSheet(trigger.dataset.dishId, trigger));
  });

  sheetClose?.addEventListener("click", closeSheet);
  overlay?.addEventListener("click", closeSheet);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && lightbox?.classList.contains("open")) {
      closeLightbox();
      return;
    }
    if (event.key === "Escape") closeSheet();
    if (event.key === "Tab" && sheet.classList.contains("open")) {
      const focusable = [...sheet.querySelectorAll("button, [tabindex='0']")];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });

  gallery?.addEventListener("scroll", () => {
    const index = Math.round(gallery.scrollLeft / Math.max(gallery.clientWidth, 1));
    [...galleryDots.children].forEach((dot, dotIndex) => dot.classList.toggle("active", index === dotIndex));
  }, { passive: true });
  gallery?.addEventListener("click", (event) => {
    if (event.target instanceof HTMLImageElement) openLightbox(event.target);
  });
  lightboxClose?.addEventListener("click", closeLightbox);
  lightbox?.addEventListener("click", (event) => {
    if (event.target !== lightboxImage && event.target !== lightboxClose) closeLightbox();
  });

  const observer = "IntersectionObserver" in window
    ? new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.08 })
    : null;

  document.querySelectorAll(".reveal").forEach((node) => {
    if (observer) observer.observe(node);
    else node.classList.add("visible");
  });

  initPromotionCarousel();
  applyLanguage(currentLang);
})();
