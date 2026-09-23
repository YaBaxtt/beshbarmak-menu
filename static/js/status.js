(() => {
  "use strict";
  const shell = document.querySelector(".status-shell");
  const toast = document.querySelector(".status-toast");
  if (!shell) return;
  const language = shell.dataset.language === "ru" ? "ru" : "uz";
  localStorage.setItem("last-reservation-url", shell.dataset.publicUrl);
  localStorage.setItem("last-reservation-number", shell.dataset.publicNumber);
  let status = shell.dataset.currentStatus;
  const messages = language === "uz"
    ? { ACCEPTED: "Bron tasdiqlandi!", CHANGE_PROPOSED: "Restoran boshqa vaqtni taklif qildi.", REJECTED: "Ariza rad etildi.", CANCELLED: "Bron bekor qilindi." }
    : { ACCEPTED: "Бронирование подтверждено!", CHANGE_PROPOSED: "Ресторан предложил другое время.", REJECTED: "Заявка отклонена.", CANCELLED: "Бронирование отменено." };
  async function check() {
    if (["REJECTED", "CANCELLED", "COMPLETED", "NO_SHOW"].includes(status)) return;
    try {
      const response = await fetch(shell.dataset.statusUrl, { headers: { "X-Requested-With": "XMLHttpRequest" }, cache: "no-store" });
      if (!response.ok) return;
      const data = await response.json();
      if (data.status !== status) {
        status = data.status;
        toast.textContent = messages[status] || (language === "uz" ? `Holat o‘zgardi: ${data.status_label}` : `Статус изменён: ${data.status_label}`);
        toast.classList.add("show");
        window.setTimeout(() => window.location.reload(), 1400);
      }
    } catch (_) { /* network interruptions are retried quietly */ }
  }
  window.setInterval(check, 7000);
})();
