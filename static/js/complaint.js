(() => {
  "use strict";
  const form = document.getElementById("complaint-form");
  const submit = document.getElementById("complaint-submit");
  if (!form || !submit) return;
  let sending = false;
  form.addEventListener("submit", (event) => {
    if (sending) {
      event.preventDefault();
      return;
    }
    if (!form.checkValidity()) {
      event.preventDefault();
      form.reportValidity();
      return;
    }
    sending = true;
    form.setAttribute("aria-busy", "true");
    submit.disabled = true;
    submit.classList.add("is-loading");
    submit.textContent = submit.dataset.sending;
  });
})();
