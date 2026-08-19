/**
 * UI de secours (o2switch sans bundle Vite) :
 * modales, filtres auto, menus Actions, confirmations, discipline matricule.
 */
(function () {
  if (window.__elimuLegacyUi) return;
  window.__elimuLegacyUi = true;

  var ANIM_MS = 160;
  var OPEN_MODALS = new Set();

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

  /* ---------- Modales ---------- */

  function resolveModal(target) {
    if (!target) return null;
    if (typeof target === "string") {
      return (
        document.querySelector('[data-modal="' + target + '"]') ||
        document.getElementById(target)
      );
    }
    return target;
  }

  function getFocusable(root) {
    return Array.prototype.filter.call(
      root.querySelectorAll(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
      ),
      function (el) {
        if (el.hasAttribute("disabled")) return false;
        var style = window.getComputedStyle(el);
        return style.display !== "none" && style.visibility !== "hidden";
      }
    );
  }

  function onModalKeyDown(e, modal) {
    if (e.key === "Escape") {
      e.preventDefault();
      closeModal(modal);
      return;
    }
    if (e.key !== "Tab") return;
    var focusable = getFocusable(modal);
    if (!focusable.length) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  function openModal(target) {
    var modal = resolveModal(target);
    if (!modal) {
      console.warn("[ELIMU] Modale introuvable:", target);
      return null;
    }

    modal.hidden = false;
    modal.removeAttribute("hidden");
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");

    var panel =
      modal.querySelector("[data-modal-panel]") ||
      modal.querySelector(".modal");
    if (panel) {
      panel.style.transition = "transform " + ANIM_MS + "ms ease";
      panel.style.transform = "translateY(8px)";
      window.requestAnimationFrame(function () {
        panel.style.transform = "translateY(0)";
      });
    }

    modal._elimuPrevFocus = document.activeElement;
    OPEN_MODALS.add(modal);
    document.body.classList.add("modal-open");

    window.setTimeout(function () {
      var focusable = getFocusable(modal);
      var first = focusable[0] || panel;
      if (first && typeof first.focus === "function") first.focus();
    }, 20);

    if (!modal._elimuKeyHandler) {
      modal._elimuKeyHandler = function (e) {
        onModalKeyDown(e, modal);
      };
      document.addEventListener("keydown", modal._elimuKeyHandler);
    }

    document.dispatchEvent(
      new CustomEvent("elimu:modal-open", { detail: { modal: modal } })
    );
    paintIcons();
    return modal;
  }

  function closeModal(target) {
    var modal = resolveModal(target);
    if (!modal) return;

    var panel =
      modal.querySelector("[data-modal-panel]") ||
      modal.querySelector(".modal");
    if (panel) panel.style.transform = "translateY(8px)";

    window.setTimeout(function () {
      modal.hidden = true;
      modal.setAttribute("hidden", "");
      modal.classList.remove("is-open");
      modal.setAttribute("aria-hidden", "true");
    }, ANIM_MS);

    OPEN_MODALS.delete(modal);
    if (modal._elimuKeyHandler) {
      document.removeEventListener("keydown", modal._elimuKeyHandler);
      delete modal._elimuKeyHandler;
    }
    if (OPEN_MODALS.size === 0) {
      document.body.classList.remove("modal-open");
    }

    var prev = modal._elimuPrevFocus;
    if (prev && typeof prev.focus === "function") prev.focus();

    document.dispatchEvent(
      new CustomEvent("elimu:modal-close", { detail: { modal: modal } })
    );
  }

  function initModals(root) {
    root.querySelectorAll("[data-modal-open]").forEach(function (trigger) {
      if (trigger.dataset.modalBound) return;
      trigger.dataset.modalBound = "1";
      trigger.addEventListener("click", function (e) {
        e.preventDefault();
        var id = trigger.getAttribute("data-modal-open");
        if (id) openModal(id);
      });
    });

    root.querySelectorAll("[data-modal-close]").forEach(function (btn) {
      if (btn.dataset.modalCloseBound) return;
      btn.dataset.modalCloseBound = "1";
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        var modal = btn.closest("[data-modal]");
        if (modal) closeModal(modal);
      });
    });

    root.querySelectorAll("[data-modal]").forEach(function (modal) {
      if (modal.dataset.modalOverlayBound) return;
      modal.dataset.modalOverlayBound = "1";
      modal.addEventListener("click", function (e) {
        if (e.target === modal) closeModal(modal);
      });
      if (!modal.hasAttribute("hidden")) {
        modal.classList.add("is-open");
        document.body.classList.add("modal-open");
        OPEN_MODALS.add(modal);
      }
    });
  }

  /* ---------- Filtres auto (GET) ---------- */

  var FILTER_FORM_SELECTOR = [
    "form[data-auto-filter]",
    "form.secretariat-toolbar--filters",
    "form.finance-filters",
  ].join(", ");

  function initAutoFilterForms(root) {
    root.querySelectorAll(FILTER_FORM_SELECTOR).forEach(function (form) {
      if (!(form instanceof HTMLFormElement)) return;
      if ((form.method || "get").toLowerCase() !== "get") return;
      if (
        form.hasAttribute("hx-get") ||
        form.hasAttribute("hx-post") ||
        form.hasAttribute("data-finance-filters")
      ) {
        return;
      }
      if (form.dataset.autoFilterBound === "1") return;
      form.dataset.autoFilterBound = "1";
      form.setAttribute("data-auto-filter", "1");

      var timer = null;

      function submitNow() {
        if (typeof form.requestSubmit === "function") {
          try {
            form.requestSubmit();
            return;
          } catch (_) {}
        }
        form.submit();
      }

      form.addEventListener("change", function (event) {
        var target = event.target;
        if (!(target instanceof HTMLElement)) return;
        if (!form.contains(target)) return;
        if (
          target.matches(
            'select, input[type="date"], input[type="month"], input[type="checkbox"], input[type="radio"]'
          )
        ) {
          submitNow();
        }
      });

      form.querySelectorAll('input[type="search"], input[name="q"]').forEach(
        function (input) {
          input.addEventListener("input", function () {
            if (timer) window.clearTimeout(timer);
            timer = window.setTimeout(submitNow, 350);
          });
        }
      );
    });
  }

  /* ---------- Menus déroulants Actions ---------- */

  function initDropdowns(root) {
    root.querySelectorAll("[data-dropdown]").forEach(function (dropdown) {
      if (dropdown.dataset.dropdownBound) return;
      dropdown.dataset.dropdownBound = "1";
      var trigger =
        dropdown.querySelector("[data-dropdown-trigger]") ||
        dropdown.querySelector("button");
      var menu = dropdown.querySelector("[data-dropdown-menu]");
      if (!trigger || !menu) return;

      menu.hidden = true;
      menu.setAttribute("hidden", "");

      trigger.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        var willOpen = menu.hidden || menu.hasAttribute("hidden");
        closeAllDropdowns();
        if (willOpen) {
          menu.hidden = false;
          menu.removeAttribute("hidden");
          menu.style.display = "";
          dropdown.classList.add("is-open");
          trigger.setAttribute("aria-expanded", "true");
        }
      });

      menu.querySelectorAll("[data-dropdown-item]").forEach(function (item) {
        item.addEventListener("click", function () {
          closeAllDropdowns();
        });
      });
    });
  }

  function closeAllDropdowns() {
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

  /* ---------- Sidebar (admin sans Alpine) ---------- */

  var SIDEBAR_STORAGE_KEY = "kalunga.sidebar.collapsed";

  function initSidebar(root) {
    var sidebar = root.querySelector("[data-sidebar]");
    if (!sidebar || sidebar.dataset.sidebarBound === "1") return;
    sidebar.dataset.sidebarBound = "1";

    var toggle =
      root.querySelector("[data-sidebar-toggle]") ||
      sidebar.querySelector("[data-sidebar-toggle]");

    function isCollapsed() {
      try {
        return localStorage.getItem(SIDEBAR_STORAGE_KEY) === "1";
      } catch (_) {
        return false;
      }
    }

    function applyCollapsed(collapsed) {
      var width = collapsed ? 72 : 248;
      sidebar.style.width = width + "px";
      sidebar.style.minWidth = width + "px";
      sidebar.classList.toggle("is-collapsed", collapsed);
      sidebar.setAttribute("data-collapsed", collapsed ? "true" : "false");
      sidebar.setAttribute("aria-expanded", collapsed ? "false" : "true");
      document.documentElement.style.setProperty("--sidebar-width", width + "px");
      document.documentElement.classList.toggle("sidebar-collapsed", collapsed);
    }

    function setCollapsed(collapsed) {
      try {
        localStorage.setItem(SIDEBAR_STORAGE_KEY, collapsed ? "1" : "0");
      } catch (_) {}
      applyCollapsed(collapsed);
    }

    applyCollapsed(isCollapsed());

    if (toggle) {
      toggle.addEventListener("click", function (event) {
        event.preventDefault();
        setCollapsed(!isCollapsed());
      });
    }
  }

  /* ---------- HTMX : jeton CSRF ---------- */

  function initHtmxCsrf() {
    if (!window.htmx || document.documentElement.dataset.htmxCsrfBound === "1") {
      return;
    }
    document.documentElement.dataset.htmxCsrfBound = "1";

    function readCsrfToken() {
      if (!document.cookie) return "";
      var parts = document.cookie.split(";");
      for (var i = 0; i < parts.length; i++) {
        var chunk = parts[i].trim();
        if (chunk.indexOf("csrftoken=") === 0) {
          return decodeURIComponent(chunk.slice("csrftoken=".length));
        }
      }
      var meta = document.querySelector('meta[name="csrf-token"]');
      return meta ? meta.getAttribute("content") || "" : "";
    }

    document.body.addEventListener("htmx:configRequest", function (event) {
      var token = readCsrfToken();
      if (!token) return;
      event.detail.headers["X-CSRFToken"] = token;
      if (!event.detail.headers["X-Requested-With"]) {
        event.detail.headers["X-Requested-With"] = "XMLHttpRequest";
      }
    });
  }

  /* ---------- Confirmations ---------- */

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
          form.getAttribute("data-confirm-form") ||
          "Confirmer cette opération ?";
        if (!window.confirm(message)) event.preventDefault();
        else form.dataset.confirmAccepted = "1";
      });
    });
  }

  function initLogoutConfirm(root) {
    root.querySelectorAll("[data-logout-confirm]").forEach(function (form) {
      if (form.dataset.logoutConfirmBound) return;
      form.dataset.logoutConfirmBound = "1";
      form.addEventListener("submit", function (event) {
        if (form.dataset.logoutConfirmed === "1") return;
        event.preventDefault();
        if (
          window.confirm(
            "Voulez-vous vraiment vous déconnecter de votre espace ?"
          )
        ) {
          form.dataset.logoutConfirmed = "1";
          if (typeof form.requestSubmit === "function") form.requestSubmit();
          else form.submit();
        }
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

  /* ---------- Discipline : matricule → classe ---------- */

  function bindMatriculeAutofill(form, lookupUrl) {
    var matriculeInput = form.querySelector("[data-matricule-input]");
    var classInput = form.querySelector("[data-class-input]");
    var hintEl = form.querySelector("[data-student-hint]");
    if (!matriculeInput || !classInput || !lookupUrl) return;

    var timer = null;
    var seq = 0;
    var defaultHint = hintEl ? hintEl.textContent : "";

    function setHint(text, ok) {
      if (!hintEl) return;
      hintEl.textContent = text || defaultHint;
      hintEl.style.color = ok === false ? "#b42318" : "";
    }

    function clearClass() {
      classInput.value = "";
    }

    function lookup() {
      var matricule = (matriculeInput.value || "").trim();
      if (!matricule) {
        clearClass();
        setHint(defaultHint, null);
        return;
      }
      var requestId = ++seq;
      fetch(
        lookupUrl + "?" + new URLSearchParams({ matricule: matricule }).toString(),
        { headers: { Accept: "application/json" }, credentials: "same-origin" }
      )
        .then(function (response) {
          return response.json().catch(function () {
            return {};
          }).then(function (payload) {
            return { response: response, payload: payload };
          });
        })
        .then(function (result) {
          if (requestId !== seq) return;
          if (!result.response.ok || !result.payload.ok) {
            clearClass();
            setHint(
              result.payload.error || "Élève introuvable pour ce matricule.",
              false
            );
            return;
          }
          var data = result.payload.data || {};
          classInput.value = data.class_name || "";
          var name = data.full_name || "";
          setHint(
            name
              ? name + " · " + (data.matricule || matricule)
              : defaultHint,
            true
          );
        })
        .catch(function () {
          if (requestId !== seq) return;
          clearClass();
          setHint("Impossible de vérifier le matricule.", false);
        });
    }

    function scheduleLookup() {
      if (timer) window.clearTimeout(timer);
      timer = window.setTimeout(lookup, 350);
    }

    matriculeInput.addEventListener("input", scheduleLookup);
    matriculeInput.addEventListener("blur", lookup);
    if ((matriculeInput.value || "").trim()) lookup();
  }

  function initDisciplineMatricule(root) {
    var pages = root.querySelectorAll(
      '[data-page="discipline-incidents-list"], [data-page="discipline-exits-list"], [data-page="discipline-summons-list"]'
    );
    pages.forEach(function (page) {
      var lookupUrl = page.dataset.incidentLookupUrl || "";
      page.querySelectorAll("[data-matricule-autofill-form]").forEach(
        function (form) {
          if (form.dataset.matriculeBound === "1") return;
          form.dataset.matriculeBound = "1";
          bindMatriculeAutofill(form, lookupUrl);
        }
      );
    });

    document.querySelectorAll("[data-matricule-autofill-form]").forEach(
      function (form) {
        if (form.dataset.matriculeBound === "1") return;
        var page =
          form.closest("[data-incident-lookup-url]") ||
          document.querySelector(
            '[data-page="discipline-incidents-list"], [data-page="discipline-exits-list"], [data-page="discipline-summons-list"]'
          );
        var lookupUrl = (page && page.dataset.incidentLookupUrl) || "";
        if (!lookupUrl) return;
        form.dataset.matriculeBound = "1";
        bindMatriculeAutofill(form, lookupUrl);
      }
    );
  }

  function boot(root) {
    initModals(root);
    initAutoFilterForms(root);
    initDropdowns(root);
    initConfirms(root);
    initLogoutConfirm(root);
    initPasswordToggles(root);
    initDisciplineMatricule(root);
    initSidebar(root);
    paintIcons();
  }

  window.Kalunga = window.Kalunga || {};
  window.Kalunga.modal = { open: openModal, close: closeModal };

  ready(function () {
    initHtmxCsrf();
    boot(document);
    document.addEventListener("click", function (event) {
      if (!event.target.closest("[data-dropdown]")) closeAllDropdowns();
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeAllDropdowns();
    });
    document.body.addEventListener("htmx:afterSwap", function (event) {
      if (event.target instanceof Element) boot(event.target);
    });
    document.addEventListener("elimu:modal-open", function () {
      initDisciplineMatricule(document);
    });
  });
})();
