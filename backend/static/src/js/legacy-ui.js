/**
 * UI de secours (o2switch sans bundle Vite) : menus Actions, confirmations, mots de passe.
 */
(function () {
  if (window.__elimuLegacyUi) return;
  window.__elimuLegacyUi = true;

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function paintIcons() {
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons({ attrs: { "stroke-width": 1.75 } });
    }
  }

  function initDropdowns(root) {
    root.querySelectorAll("[data-dropdown]").forEach(function (dropdown) {
      if (dropdown.dataset.dropdownBound) return;
      dropdown.dataset.dropdownBound = "1";
      var trigger =
        dropdown.querySelector("[data-dropdown-trigger]") ||
        dropdown.querySelector("button");
      var menu = dropdown.querySelector("[data-dropdown-menu]");
      if (!trigger || !menu) return;

      trigger.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        var willOpen = menu.hasAttribute("hidden") || menu.hidden;
        closeAll();
        if (willOpen) {
          menu.hidden = false;
          menu.removeAttribute("hidden");
          dropdown.classList.add("is-open");
          trigger.setAttribute("aria-expanded", "true");
        }
      });
    });
  }

  function closeAll() {
    document.querySelectorAll("[data-dropdown].is-open").forEach(function (dropdown) {
      var trigger =
        dropdown.querySelector("[data-dropdown-trigger]") ||
        dropdown.querySelector("button");
      var menu = dropdown.querySelector("[data-dropdown-menu]");
      dropdown.classList.remove("is-open");
      if (trigger) trigger.setAttribute("aria-expanded", "false");
      if (menu) {
        menu.hidden = true;
        menu.setAttribute("hidden", "");
      }
    });
  }

  function initConfirms(root) {
    root.querySelectorAll("form[data-confirm-form]").forEach(function (form) {
      if (form.dataset.confirmBound) return;
      form.dataset.confirmBound = "1";
      form.addEventListener("submit", function (event) {
        if (form.dataset.confirmAccepted === "1") {
          form.dataset.confirmAccepted = "";
          return;
        }
        var message =
          form.getAttribute("data-confirm-form") || "Confirmer cette opération ?";
        if (!window.confirm(message)) event.preventDefault();
        else form.dataset.confirmAccepted = "1";
      });
    });
  }

  function initPasswordToggles(root) {
    root.querySelectorAll("[data-password-toggle]").forEach(function (btn) {
      if (btn.dataset.passwordBound) return;
      btn.dataset.passwordBound = "1";
      btn.addEventListener("click", function (event) {
        event.preventDefault();
        var sel = btn.getAttribute("data-password-toggle");
        var input = sel ? document.querySelector(sel) : null;
        if (!(input instanceof HTMLInputElement)) {
          input = btn.previousElementSibling;
        }
        if (!(input instanceof HTMLInputElement)) return;
        var show = input.type === "password";
        input.type = show ? "text" : "password";
        btn.setAttribute("aria-pressed", show ? "true" : "false");
      });
    });
  }

  function boot(root) {
    initDropdowns(root);
    initConfirms(root);
    initPasswordToggles(root);
    paintIcons();
  }

  ready(function () {
    boot(document);
    document.addEventListener("click", function (event) {
      if (!event.target.closest("[data-dropdown]")) closeAll();
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeAll();
    });
    document.body.addEventListener("htmx:afterSwap", function (event) {
      if (event.target instanceof Element) boot(event.target);
    });
  });
})();
