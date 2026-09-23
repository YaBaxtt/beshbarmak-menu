(() => {
  "use strict";
  const drawer = document.querySelector(".nav-drawer");
  const overlay = document.querySelector(".nav-drawer-overlay");
  const openers = [...document.querySelectorAll("[data-nav-open]")];
  const closers = [...document.querySelectorAll("[data-nav-close]")];
  if (!drawer || !overlay || !openers.length) return;
  let previousFocus = null;
  const focusable = () => [...drawer.querySelectorAll('a[href],button:not([disabled])')];
  function open() {
    previousFocus = document.activeElement;
    document.body.classList.add("nav-open");
    drawer.classList.add("open"); overlay.classList.add("open");
    drawer.setAttribute("aria-hidden", "false"); overlay.setAttribute("aria-hidden", "false");
    openers.forEach((item) => item.setAttribute("aria-expanded", "true"));
    window.setTimeout(() => focusable()[0]?.focus(), 220);
  }
  function close() {
    document.body.classList.remove("nav-open");
    drawer.classList.remove("open"); overlay.classList.remove("open");
    drawer.setAttribute("aria-hidden", "true"); overlay.setAttribute("aria-hidden", "true");
    openers.forEach((item) => item.setAttribute("aria-expanded", "false"));
    previousFocus?.focus();
  }
  openers.forEach((item) => item.addEventListener("click", open));
  closers.forEach((item) => item.addEventListener("click", close));
  drawer.querySelectorAll("a").forEach((item) => item.addEventListener("click", close));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && drawer.classList.contains("open")) close();
    if (event.key !== "Tab" || !drawer.classList.contains("open")) return;
    const items = focusable(); const first = items[0]; const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
})();
