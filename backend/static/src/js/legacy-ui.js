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
    document.dispatchEvent(
      new CustomEvent("kalunga:modal-open", { detail: { modal: modal } })
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
    document.dispatchEvent(
      new CustomEvent("kalunga:modal-close", { detail: { modal: modal } })
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

  /* ---------- Boîtes de dialogue (remplace window.confirm) ---------- */

  var DIALOG_ANIM_MS = 160;

  function styleDialogBtn(btn, primary, danger) {
    btn.type = "button";
    btn.style.borderRadius = "6px";
    btn.style.padding = "0.45rem 0.85rem";
    btn.style.fontSize = "0.85rem";
    btn.style.cursor = "pointer";
    btn.style.border = "1px solid var(--color-border, #2b3940)";
    btn.style.background = primary
      ? danger
        ? "var(--color-danger, #d15b5b)"
        : "var(--color-primary, #1f6f4a)"
      : "var(--color-surface, #152028)";
    btn.style.color = "var(--color-text-primary, #f4f7f5)";
  }

  function confirmDialog(message, options) {
    options = options || {};
    var title = options.title || "Confirmation";
    var confirmLabel = options.confirmLabel || "Confirmer";
    var cancelLabel = options.cancelLabel || "Annuler";
    var danger = !!options.danger;

    return new Promise(function (resolve) {
      var overlay = document.createElement("div");
      overlay.className = "kalunga-dialog-overlay";
      overlay.style.cssText =
        "position:fixed;inset:0;z-index:10000;display:flex;align-items:center;" +
        "justify-content:center;padding:1rem;background:var(--color-overlay,rgba(11,17,22,0.72));" +
        "opacity:0;transition:opacity " +
        DIALOG_ANIM_MS +
        "ms ease";

      var panel = document.createElement("div");
      panel.className = "kalunga-dialog";
      panel.setAttribute("role", "alertdialog");
      panel.setAttribute("aria-modal", "true");
      panel.style.cssText =
        "width:min(24rem,100%);border-radius:6px;border:1px solid var(--color-border,#2b3940);" +
        "background:var(--color-surface-elevated,#1a2730);color:var(--color-text-primary,#f4f7f5);" +
        "padding:1.1rem 1.15rem;box-shadow:0 8px 24px rgba(0,0,0,0.35);transform:scale(0.98);" +
        "transition:transform " +
        DIALOG_ANIM_MS +
        "ms ease";

      var titleEl = document.createElement("h2");
      titleEl.textContent = title;
      titleEl.style.cssText = "margin:0 0 0.5rem;font-size:1rem;font-weight:600";

      var msgEl = document.createElement("p");
      msgEl.textContent = message;
      msgEl.style.cssText =
        "margin:0 0 1rem;font-size:0.875rem;color:var(--color-text-secondary,#a2aea8);line-height:1.45";

      var actions = document.createElement("div");
      actions.style.cssText = "display:flex;justify-content:flex-end;gap:0.5rem";

      var cancelBtn = document.createElement("button");
      cancelBtn.textContent = cancelLabel;
      styleDialogBtn(cancelBtn, false, false);

      var confirmBtn = document.createElement("button");
      confirmBtn.textContent = confirmLabel;
      styleDialogBtn(confirmBtn, true, danger);

      function finish(value) {
        overlay.style.opacity = "0";
        panel.style.transform = "scale(0.98)";
        window.setTimeout(function () {
          overlay.remove();
          document.removeEventListener("keydown", onKey);
          resolve(value);
        }, DIALOG_ANIM_MS);
      }

      function onKey(e) {
        if (e.key === "Escape") {
          e.preventDefault();
          finish(false);
        }
      }

      cancelBtn.addEventListener("click", function () {
        finish(false);
      });
      confirmBtn.addEventListener("click", function () {
        finish(true);
      });
      overlay.addEventListener("click", function (e) {
        if (e.target === overlay) finish(false);
      });

      actions.appendChild(cancelBtn);
      actions.appendChild(confirmBtn);
      panel.appendChild(titleEl);
      panel.appendChild(msgEl);
      panel.appendChild(actions);
      overlay.appendChild(panel);
      document.body.appendChild(overlay);
      document.addEventListener("keydown", onKey);

      window.requestAnimationFrame(function () {
        overlay.style.opacity = "1";
        panel.style.transform = "scale(1)";
        confirmBtn.focus();
      });
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
        event.preventDefault();
        var message =
          form.getAttribute("data-confirm-form") || "Confirmer cette opération ?";
        var danger = form.hasAttribute("data-confirm-danger");
        confirmDialog(message, {
          confirmLabel: "Confirmer",
          cancelLabel: "Annuler",
          danger: danger,
        }).then(function (ok) {
          if (!ok) return;
          form.dataset.confirmAccepted = "1";
          if (typeof form.requestSubmit === "function") form.requestSubmit();
          else form.submit();
        });
      });
    });

    root.querySelectorAll("[data-confirm][data-confirm-submit]").forEach(function (btn) {
      if (btn.dataset.confirmBound) return;
      btn.dataset.confirmBound = "1";
      btn.addEventListener("click", function (event) {
        event.preventDefault();
        var message = btn.getAttribute("data-confirm") || "Confirmer cette opération ?";
        confirmDialog(message, {
          confirmLabel: "Confirmer",
          cancelLabel: "Annuler",
          danger: btn.hasAttribute("data-confirm-danger"),
        }).then(function (ok) {
          if (!ok) return;
          var form = btn.closest("form");
          if (!form) return;
          form.dataset.confirmAccepted = "1";
          if (typeof form.requestSubmit === "function") form.requestSubmit();
          else form.submit();
        });
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
        confirmDialog(
          "Voulez-vous vraiment vous déconnecter de votre espace ?",
          {
            title: "Confirmer la déconnexion",
            confirmLabel: "Se déconnecter",
            cancelLabel: "Rester connecté",
            danger: true,
          }
        ).then(function (ok) {
          if (!ok) return;
          form.dataset.logoutConfirmed = "1";
          if (typeof form.requestSubmit === "function") form.requestSubmit();
          else form.submit();
        });
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

  /* ---------- Comptabilité : formulaire paiement ---------- */

  function initFinancePaymentForm(root) {
    var page = root.querySelector('[data-page="finance-payments"]');
    if (!page || page.dataset.paymentFeesBound === "1") return;
    page.dataset.paymentFeesBound = "1";

    var dataEl = page.querySelector("#payment-fee-groups-data");
    var groupSelect = page.querySelector("[data-payment-fee-group]");
    var periodSelect = page.querySelector("[data-payment-period]");
    var hint = page.querySelector("[data-payment-period-hint]");
    var matriculeInput = page.querySelector("[data-payment-matricule]");
    var studentHint = page.querySelector("[data-payment-student-hint]");
    var emptyFees = page.querySelector("[data-payment-fees-empty]");
    var submitBtn = page.querySelector("[data-payment-submit]");
    var lookupUrl = page.dataset.matriculeLookupUrl || "";
    var stem = page.dataset.matriculeStem || "";
    var classe = page.dataset.classe || "";
    if (!dataEl || !groupSelect || !periodSelect) return;

    var groups = [];
    try {
      groups = JSON.parse(dataEl.textContent || "[]");
    } catch (_) {
      groups = [];
    }
    var initialGroups = groups.slice();
    var byKey = {};
    var preferredGroup = groupSelect.value;
    var preferredPeriod = periodSelect.value;
    var lookupTimer = null;
    var lookupSeq = 0;

    function fillEmpty(select, label) {
      select.innerHTML = "";
      var empty = document.createElement("option");
      empty.value = "";
      empty.textContent = label || "Choisir…";
      select.appendChild(empty);
    }

    function setStudentHint(message, tone) {
      if (!studentHint) return;
      if (!message) {
        studentHint.hidden = true;
        studentHint.textContent = "";
        studentHint.classList.remove("is-ok", "is-error");
        return;
      }
      studentHint.hidden = false;
      studentHint.textContent = message;
      studentHint.classList.toggle("is-ok", tone === "ok");
      studentHint.classList.toggle("is-error", tone === "error");
    }

    function rebuildByKey() {
      byKey = {};
      groups.forEach(function (g) {
        byKey[g.key] = g;
      });
    }

    function applyGroups(nextGroups, resetSelection) {
      groups = nextGroups || [];
      dataEl.textContent = JSON.stringify(groups);
      rebuildByKey();

      var previousGroup = resetSelection ? "" : preferredGroup || groupSelect.value;
      fillEmpty(groupSelect);
      groups.forEach(function (group) {
        var opt = document.createElement("option");
        opt.value = group.key;
        opt.textContent = group.label;
        groupSelect.appendChild(opt);
      });

      var hasFees = groups.length > 0;
      groupSelect.disabled = !hasFees;
      if (submitBtn) submitBtn.disabled = !hasFees;
      if (emptyFees) emptyFees.hidden = hasFees;

      if (previousGroup && byKey[previousGroup]) {
        groupSelect.value = previousGroup;
      } else {
        groupSelect.value = "";
        preferredPeriod = "";
      }
      syncPeriod();
    }

    function syncPeriod() {
      var group = byKey[groupSelect.value];
      fillEmpty(periodSelect);

      if (!group) {
        periodSelect.disabled = true;
        if (hint) hint.textContent = "Choisissez d'abord un frais.";
        return;
      }

      if (group.schedule_mode === "UNE_FOIS") {
        periodSelect.disabled = true;
        if (hint) {
          hint.textContent =
            "Ce frais se paie en une seule fois — mois et tranches non applicables.";
        }
        return;
      }

      periodSelect.disabled = false;
      (group.periods || []).forEach(function (period) {
        var opt = document.createElement("option");
        opt.value = String(period.id);
        opt.textContent = period.label;
        periodSelect.appendChild(opt);
      });

      if (
        preferredPeriod &&
        Array.prototype.some.call(periodSelect.options, function (o) {
          return o.value === preferredPeriod;
        })
      ) {
        periodSelect.value = preferredPeriod;
      }

      if (hint) {
        hint.textContent =
          group.schedule_mode === "MOIS"
            ? "Seuls les mois impayés ou partiellement payés sont proposés."
            : "Seules les tranches impayées ou partiellement payées sont proposées.";
      }
    }

    function lookupMatricule() {
      if (!lookupUrl || !matriculeInput) return;
      var suffix = (matriculeInput.value || "").trim();
      if (!suffix) {
        setStudentHint("", null);
        preferredGroup = "";
        preferredPeriod = "";
        applyGroups(classe ? initialGroups : [], true);
        return;
      }

      var seq = ++lookupSeq;
      var params = new URLSearchParams({ suffix: suffix, stem: stem });
      if (classe) params.set("classe", classe);

      fetch(lookupUrl + "?" + params.toString(), {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      })
        .then(function (response) {
          return response.json().catch(function () {
            return {};
          }).then(function (payload) {
            return { response: response, payload: payload };
          });
        })
        .then(function (result) {
          if (seq !== lookupSeq) return;
          if (!result.response.ok || !result.payload.ok) {
            setStudentHint(
              result.payload.error || "Aucun élève trouvé pour ce matricule.",
              "error"
            );
            preferredGroup = "";
            preferredPeriod = "";
            applyGroups([], true);
            return;
          }

          var student = result.payload.student || {};
          var name = student.name || "Élève";
          var className = student.class_name || "";
          var matricule = student.matricule || "";
          setStudentHint(
            className
              ? name + " — Classe : " + className + (matricule ? " (" + matricule + ")" : "")
              : name + (matricule ? " (" + matricule + ")" : ""),
            "ok"
          );
          preferredGroup = "";
          preferredPeriod = "";
          applyGroups(result.payload.fee_groups || [], true);
        })
        .catch(function () {
          if (seq !== lookupSeq) return;
          setStudentHint("Impossible de vérifier le matricule pour le moment.", "error");
        });
    }

    function scheduleLookup() {
      if (lookupTimer) window.clearTimeout(lookupTimer);
      lookupTimer = window.setTimeout(lookupMatricule, 350);
    }

    groupSelect.addEventListener("change", function () {
      preferredGroup = groupSelect.value;
      preferredPeriod = "";
      syncPeriod();
    });

    if (matriculeInput) {
      matriculeInput.addEventListener("input", scheduleLookup);
      matriculeInput.addEventListener("blur", lookupMatricule);
    }

    rebuildByKey();
    if (groups.length) {
      applyGroups(groups, false);
    } else {
      applyGroups([], true);
    }

    if (matriculeInput && (matriculeInput.value || "").trim()) {
      lookupMatricule();
    }
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
    initFinancePaymentForm(root);
    paintIcons();
  }

  window.Kalunga = window.Kalunga || {};
  window.Kalunga.modal = { open: openModal, close: closeModal };
  window.Kalunga.confirm = confirmDialog;

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
