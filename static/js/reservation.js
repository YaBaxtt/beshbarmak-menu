(() => {
  "use strict";
  const shell = document.querySelector(".booking-shell");
  const form = document.getElementById("reservation-form");
  if (!shell || !form) return;
  const language = shell.dataset.language === "ru" ? "ru" : "uz";
  const copy = language === "uz" ? {
    loading: "Yuklanmoqda…", chooseTime: "Vaqtni tanlang", searching: "Mos joylarni izlayapmiz…",
    cozy: "Restoranning shinam joyi", from: "Dan", upTo: "Gacha", guests: "mehmon",
    choose: "Tanlash", unavailable: "Mavjud emas", selectDate: "Sanani tanlang.",
    selectTime: "Vaqtni tanlang.", enterGuests: "Mehmonlar sonini kiriting.",
    enterName: "Ismingizni kiriting.", checkPhone: "Telefon raqamini tekshiring.", selected: "Tanlandi", sending: "Yuborilmoqda…",
  } : {
    loading: "Загрузка…", chooseTime: "Выберите время", searching: "Ищем подходящие места…",
    cozy: "Уютное пространство ресторана", from: "От", upTo: "До", guests: "гостей",
    choose: "Выбрать", unavailable: "Недоступно", selectDate: "Выберите дату.",
    selectTime: "Выберите время.", enterGuests: "Укажите количество гостей.",
    enterName: "Введите имя.", checkPhone: "Проверьте номер телефона.", selected: "Выбрано", sending: "Отправляем…",
  };

  const fields = {
    date: document.getElementById("id_date"), time: document.getElementById("id_time"),
    guests: document.getElementById("id_guests_count"), space: document.getElementById("selected-space"),
    name: document.getElementById("id_customer_name"), phone: document.getElementById("id_phone"),
    comment: document.getElementById("id_customer_comment"),
  };
  const spaceList = document.getElementById("space-list");
  const empty = document.getElementById("spaces-empty");
  const preview = document.getElementById("booking-preview");
  const previewButton = document.getElementById("preview-button");
  const submitButton = document.getElementById("submit-button");
  let spaceNames = {};
  let submitting = false;
  const escapeHTML = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);

  function showStep(number) {
    document.querySelectorAll(".form-step").forEach((step) => step.classList.toggle("active", Number(step.dataset.step) === number));
    document.querySelectorAll("[data-step-indicator]").forEach((item) => item.classList.toggle("active", Number(item.dataset.stepIndicator) <= number));
    shell.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function markInvalid(input, message) {
    input?.setAttribute("aria-invalid", "true");
    input?.focus();
    const target = input?.closest(".field")?.querySelector("small");
    if (target) target.textContent = message;
    return false;
  }

  async function loadSlots() {
    const previousValue = fields.time.value;
    fields.time.innerHTML = `<option value="">${copy.loading}</option>`;
    if (!fields.date.value) return;
    const response = await fetch(`${shell.dataset.slotsUrl}?date=${encodeURIComponent(fields.date.value)}&lang=${language}`);
    const data = await response.json();
    fields.time.innerHTML = `<option value="">${copy.chooseTime}</option>` + (data.slots || []).map((slot) => `<option value="${slot}">${slot}</option>`).join("");
    if ((data.slots || []).includes(previousValue)) fields.time.value = previousValue;
    document.getElementById("slots-message").textContent = data.message || data.error || "";
  }

  async function loadSpaces() {
    spaceList.innerHTML = `<div class="loading-card">${copy.searching}</div>`;
    empty.hidden = true;
    const params = new URLSearchParams({ date: fields.date.value, time: fields.time.value, guests: fields.guests.value, lang: language });
    const response = await fetch(`${shell.dataset.spacesUrl}?${params}`);
    const data = await response.json();
    const spaces = data.spaces || [];
    spaceNames = Object.fromEntries(spaces.map((space) => [String(space.id), space.name]));
    spaceList.innerHTML = spaces.map((space) => `
      <button type="button" class="space-card${space.selectable ? "" : " disabled"}" data-space-id="${space.id}" ${space.selectable ? "" : "disabled"}>
        <span class="space-photo">${space.image ? `<img src="${escapeHTML(space.image)}" alt="">` : "<i>BH</i>"}</span>
        <span class="space-copy"><small>${escapeHTML(space.type)}</small><b>${escapeHTML(space.name)}</b><span>${escapeHTML(space.description || copy.cozy)}</span><em>${language === "uz" ? (space.capacity_min ? `${space.capacity_min} dan ${space.capacity_max} gacha ${copy.guests}` : `${space.capacity_max} gacha ${copy.guests}`) : (space.capacity_min ? `${copy.from} ${space.capacity_min} до ${space.capacity_max} ${copy.guests}` : `${copy.upTo} ${space.capacity_max} ${copy.guests}`)}</em>${space.reason ? `<strong>${escapeHTML(space.reason)}</strong>` : ""}</span>
        <span class="space-select">${space.selectable ? copy.choose : copy.unavailable}</span>
      </button>`).join("");
    empty.hidden = spaces.some((space) => space.selectable);
    spaceList.querySelectorAll("[data-space-id]").forEach((button) => button.addEventListener("click", () => {
      fields.space.value = button.dataset.spaceId;
      spaceList.querySelectorAll(".space-card").forEach((card) => card.classList.toggle("selected", card === button));
    }));
    const existing = spaceList.querySelector(`[data-space-id="${fields.space.value}"]`);
    if (existing && !existing.disabled) existing.classList.add("selected");
  }

  fields.date?.addEventListener("change", loadSlots);
  document.querySelectorAll("[data-guest-action]").forEach((button) => button.addEventListener("click", () => {
    const delta = button.dataset.guestAction === "plus" ? 1 : -1;
    const min = Number(fields.guests.min || 1);
    const max = Number(fields.guests.max || 30);
    fields.guests.value = Math.min(max, Math.max(min, Number(fields.guests.value || min) + delta));
  }));

  document.querySelectorAll("[data-back]").forEach((button) => button.addEventListener("click", () => showStep(Number(button.dataset.back))));
  document.querySelector('[data-next="2"]')?.addEventListener("click", async () => {
    if (!fields.date.value) return markInvalid(fields.date, copy.selectDate);
    if (!fields.time.value) return markInvalid(fields.time, copy.selectTime);
    if (!fields.guests.value || Number(fields.guests.value) < 1) return markInvalid(fields.guests, copy.enterGuests);
    await loadSpaces(); showStep(2);
  });
  document.querySelector('[data-next="3"]')?.addEventListener("click", () => {
    if (!fields.space.value) { spaceList.scrollIntoView({ behavior: "smooth" }); return; }
    showStep(3);
  });

  previewButton?.addEventListener("click", () => {
    if (!fields.name.value.trim()) return markInvalid(fields.name, copy.enterName);
    if (fields.phone.value.replace(/\D/g, "").length < 7) return markInvalid(fields.phone, copy.checkPhone);
    const values = {
      date: new Intl.DateTimeFormat(language === "uz" ? "uz-UZ" : "ru-RU", { day: "numeric", month: "long", year: "numeric" }).format(new Date(`${fields.date.value}T12:00:00`)),
      time: fields.time.value, guests: fields.guests.value, space: spaceNames[fields.space.value] || copy.selected,
      name: fields.name.value, phone: fields.phone.value, comment: fields.comment.value || "—",
    };
    Object.entries(values).forEach(([key, value]) => { const node = preview.querySelector(`[data-preview="${key}"]`); if (node) node.textContent = value; });
    preview.hidden = false; previewButton.hidden = true; submitButton.hidden = false;
    preview.scrollIntoView({ behavior: "smooth", block: "start" });
  });
  [fields.name, fields.phone, fields.comment].forEach((field) => field?.addEventListener("input", () => {
    preview.hidden = true; previewButton.hidden = false; submitButton.hidden = true; field.removeAttribute("aria-invalid");
  }));

  form.addEventListener("submit", (event) => {
    if (submitting) {
      event.preventDefault();
      return;
    }
    submitting = true;
    form.setAttribute("aria-busy", "true");
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.classList.add("is-loading");
      submitButton.textContent = copy.sending;
    }
  });

  if (fields.date.value) loadSlots();
  if (form.querySelector(".errorlist")) showStep(fields.space.value ? 3 : 1);
})();
