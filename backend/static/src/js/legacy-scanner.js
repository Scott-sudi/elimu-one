/**
 * Scanners QR (mode secours o2switch sans bundle Vite) — Discipline + Finance.
 * Nécessite html5-qrcode (CDN) chargé avant ce script.
 */
(function () {
  if (window.__elimuLegacyScanner) return;
  window.__elimuLegacyScanner = true;

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function readCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.getAttribute("content")) return meta.getAttribute("content");
    if (!document.cookie) return "";
    var parts = document.cookie.split(";");
    for (var i = 0; i < parts.length; i++) {
      var chunk = parts[i].trim();
      if (chunk.indexOf("csrftoken=") === 0) {
        return decodeURIComponent(chunk.slice("csrftoken=".length));
      }
    }
    return "";
  }

  function csrfHeaders(extra) {
    var headers = extra || {};
    var token = readCsrfToken();
    if (token) headers["X-CSRFToken"] = token;
    if (!headers["X-Requested-With"]) headers["X-Requested-With"] = "XMLHttpRequest";
    return headers;
  }

  function isCameraSecureContext() {
    return typeof window !== "undefined" && window.isSecureContext === true;
  }

  function cameraBlockedMessage(err) {
    var host = window.location.host || "";
    if (!isCameraSecureContext()) {
      return (
        "Caméra indisponible en HTTP (connexion non sécurisée). " +
        "Utilisez HTTPS ou la saisie manuelle du matricule / QR ci-dessous."
      );
    }
    var name = err && err.name ? err.name : "";
    if (name === "NotAllowedError" || name === "PermissionDeniedError") {
      return "Accès caméra refusé. Autorisez la caméra pour ce site, ou utilisez la saisie manuelle.";
    }
    if (name === "NotFoundError" || name === "DevicesNotFoundError") {
      return "Aucune caméra détectée. Utilisez la saisie manuelle.";
    }
    if (name === "NotReadableError" || name === "TrackStartError") {
      return "Caméra occupée par une autre application. Fermez-la ou utilisez la saisie manuelle.";
    }
    return "Caméra indisponible" + (host ? " sur " + host : "") + ". Utilisez la saisie manuelle.";
  }

  function isLikelyMobile() {
    return /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || "");
  }

  function startHtml5QrWithFallback(instance, config, onSuccess, onFailure) {
    onFailure = onFailure || function () {};
    if (!isCameraSecureContext()) {
      var insecure = new Error("INSECURE_CONTEXT");
      insecure.name = "InsecureContextError";
      return Promise.reject(insecure);
    }

    var attempts = [];
    var mobile = isLikelyMobile();
    var Html5Qrcode = window.Html5Qrcode;

    return Html5Qrcode.getCameras()
      .then(function (cameras) {
        if (cameras && cameras.length) {
          cameras.forEach(function (cam) {
            if (cam && cam.id) attempts.push(cam.id);
          });
        }
      })
      .catch(function () {})
      .then(function () {
        if (mobile) {
          attempts.push(
            { facingMode: "environment" },
            { facingMode: { ideal: "environment" } },
            { facingMode: "user" }
          );
        } else {
          attempts.push(
            { facingMode: "user" },
            { facingMode: { ideal: "user" } },
            true,
            { facingMode: "environment" }
          );
        }
        if (!attempts.length) attempts.push({ facingMode: "user" }, true);

        var lastError = null;
        function tryNext(index) {
          if (index >= attempts.length) {
            return Promise.reject(lastError || new Error("CAMERA_START_FAILED"));
          }
          return instance
            .start(attempts[index], config, onSuccess, onFailure)
            .catch(function (err) {
              lastError = err;
              return instance
                .stop()
                .catch(function () {})
                .then(function () {
                  return tryNext(index + 1);
                });
            });
        }
        return tryNext(0);
      });
  }

  function createQrScanner(options) {
    var modal = options.modal;
    var readerId = options.readerId;
    var scanner = null;
    var cameraRunning = false;
    var resolving = false;
    var startLock = null;
    var wasOpen = false;
    var lastResolvedValue = "";
    var lastResolvedAt = 0;
    var DUPLICATE_MS = 2500;

    function isOpen() {
      return modal.classList.contains("is-open") && !modal.hidden;
    }

    function setStatus(message, tone) {
      var el = modal.querySelector(options.statusSelector);
      if (!el) return;
      el.textContent = message || "";
      el.classList.toggle("is-error", tone === "error");
      el.classList.toggle("is-ok", tone === "ok");
    }

    function stopScanner() {
      var current = scanner;
      scanner = null;
      cameraRunning = false;
      if (!current) return Promise.resolve();
      return current
        .stop()
        .catch(function () {})
        .then(function () {
          return current.clear().catch(function () {});
        });
    }

    function resolveIdentifier(raw, source) {
      if (resolving) return Promise.resolve();
      var value = String(raw || "").trim();
      if (!value) return Promise.resolve();
      var now = Date.now();
      if (value === lastResolvedValue && now - lastResolvedAt < DUPLICATE_MS) {
        return Promise.resolve();
      }
      resolving = true;
      lastResolvedValue = value;
      lastResolvedAt = now;
      return Promise.resolve(options.onResolve({ raw: value, source: source || "manual", setStatus: setStatus }))
        .catch(function (err) {
          console.warn("[legacy-scanner]", err);
          setStatus("Erreur lors du traitement.", "error");
        })
        .then(function () {
          resolving = false;
          var input = modal.querySelector(options.manualInputSelector);
          if (input && typeof input.focus === "function") input.focus();
        });
    }

    function startScanner() {
      if (startLock) return startLock;
      if (cameraRunning && scanner) return Promise.resolve();
      if (!window.Html5Qrcode) {
        setStatus("Scanner QR non chargé. Utilisez la saisie manuelle.", "error");
        return Promise.resolve();
      }

      var reader = document.getElementById(readerId);
      if (!reader) return Promise.resolve();

      startLock = stopScanner()
        .then(function () {
          reader.innerHTML = "";
          if (!isCameraSecureContext()) {
            setStatus(cameraBlockedMessage(), "error");
            return;
          }
          setStatus("Autorisez la caméra puis présentez la carte élève…");
          var instance = new window.Html5Qrcode(readerId, { verbose: false });
          scanner = instance;
          return startHtml5QrWithFallback(
            instance,
            { fps: 8, qrbox: { width: 220, height: 220 }, aspectRatio: 1.333 },
            function (decoded) {
              if (decoded) resolveIdentifier(decoded, "camera");
            },
            function () {}
          )
            .then(function () {
              if (scanner === instance) cameraRunning = true;
            })
            .catch(function (err) {
              if (scanner === instance) {
                scanner = null;
                cameraRunning = false;
              }
              console.warn("[legacy-scanner]", err);
              setStatus(cameraBlockedMessage(err), "error");
            });
        })
        .finally(function () {
          startLock = null;
        });

      return startLock;
    }

    function bindManual() {
      var submit = modal.querySelector(options.manualSubmitSelector);
      var input = modal.querySelector(options.manualInputSelector);
      if (submit && submit.dataset.legacyScannerBound !== "1") {
        submit.dataset.legacyScannerBound = "1";
        submit.addEventListener("click", function () {
          var value = input ? (input.value || "").trim() : "";
          if (!value) {
            setStatus("Saisissez un identifiant (QR ou matricule).", "error");
            return;
          }
          resolveIdentifier(value, "manual");
        });
      }
      if (input && input.dataset.legacyScannerBound !== "1") {
        input.dataset.legacyScannerBound = "1";
        input.addEventListener("keydown", function (e) {
          if (e.key === "Enter") {
            e.preventDefault();
            if (submit) submit.click();
          }
        });
      }
    }

    function onModalToggle(open) {
      if (open === wasOpen) return;
      wasOpen = open;
      if (open) {
        window.setTimeout(function () {
          startScanner();
        }, 280);
      } else {
        stopScanner();
      }
    }

    function observe() {
      if (modal.dataset.legacyScannerObserved === "1") return;
      modal.dataset.legacyScannerObserved = "1";
      wasOpen = isOpen();
      var observer = new MutationObserver(function () {
        onModalToggle(isOpen());
      });
      observer.observe(modal, { attributes: true, attributeFilter: ["class", "hidden"] });

      function handleOpen(event) {
        if (event.detail && event.detail.modal === modal) onModalToggle(true);
      }
      function handleClose(event) {
        if (event.detail && event.detail.modal === modal) onModalToggle(false);
      }
      document.addEventListener("elimu:modal-open", handleOpen);
      document.addEventListener("kalunga:modal-open", handleOpen);
      document.addEventListener("elimu:modal-close", handleClose);
      document.addEventListener("kalunga:modal-close", handleClose);
    }

    bindManual();
    observe();

    return {
      setStatus: setStatus,
      startScanner: startScanner,
      stopScanner: stopScanner,
      resolveIdentifier: resolveIdentifier,
    };
  }

  /* ---------- Discipline ---------- */

  function initDisciplineScanner() {
    var modal = document.querySelector("[data-discipline-qr-scan-modal]");
    if (!modal || modal.dataset.disciplineScannerBound === "1") return;
    modal.dataset.disciplineScannerBound = "1";

    var activeMode = "attendance";
    var resultEl = modal.querySelector("[data-discipline-scan-result]");
    var hintEl = modal.querySelector("[data-discipline-scan-hint]");

    function modeText(mode) {
      return mode === "conduct"
        ? "Scannez la carte ou saisissez le matricule pour consulter le dossier disciplinaire."
        : "Scannez la carte ou saisissez le matricule pour enregistrer la présence (entrée).";
    }

    function applyMode(mode) {
      activeMode = mode || "attendance";
      modal.querySelectorAll("[data-scan-mode]").forEach(function (btn) {
        var isActive = btn.getAttribute("data-scan-mode") === activeMode;
        btn.classList.toggle("btn--primary", isActive);
        btn.classList.toggle("btn--secondary", !isActive);
      });
      if (hintEl) hintEl.textContent = modeText(activeMode);
      if (resultEl) resultEl.textContent = "En attente de scan…";
    }

    var scanner = createQrScanner({
      modal: modal,
      readerId: "discipline-qr-reader",
      manualInputSelector: "[data-discipline-qr-manual]",
      manualSubmitSelector: "[data-discipline-qr-manual-submit]",
      statusSelector: "[data-discipline-qr-status]",
      onResolve: function (ctx) {
        var resolveUrl = modal.getAttribute("data-resolve-url");
        var attendanceUrl = modal.getAttribute("data-attendance-url");
        var identifier = (ctx.raw || "").trim();
        if (!identifier) {
          ctx.setStatus("Identifiant vide.", "error");
          return;
        }
        ctx.setStatus("Identification de l'élève…");
        return fetch(resolveUrl, {
          method: "POST",
          credentials: "same-origin",
          headers: csrfHeaders({ Accept: "application/json", "Content-Type": "application/json" }),
          body: JSON.stringify({ identifier: identifier, mode: activeMode }),
        })
          .then(function (response) {
            return response.json().catch(function () {
              return {};
            }).then(function (payload) {
              return { response: response, payload: payload };
            });
          })
          .then(function (result) {
            if (!result.response.ok || !result.payload.ok) {
              var msg = result.payload.error || "Identification impossible.";
              ctx.setStatus(msg, "error");
              return;
            }
            var identity = result.payload.data || {};
            if (activeMode === "conduct") {
              if (!identity.dossier_url) {
                ctx.setStatus("URL du dossier disciplinaire manquante.", "error");
                return;
              }
              ctx.setStatus("Ouverture du dossier disciplinaire…", "ok");
              window.location.href = identity.dossier_url;
              return;
            }
            return fetch(attendanceUrl, {
              method: "POST",
              credentials: "same-origin",
              headers: csrfHeaders({ Accept: "application/json", "Content-Type": "application/json" }),
              body: JSON.stringify({
                identifier: identifier,
                identifier_type: identity.identifier_type,
                class_public_id: modal.getAttribute("data-class-public-id") || "",
                sheet_date: modal.getAttribute("data-sheet-date") || "",
              }),
            })
              .then(function (response) {
                return response.json().catch(function () {
                  return {};
                }).then(function (payload) {
                  return { response: response, payload: payload };
                });
              })
              .then(function (att) {
                if (!att.response.ok || !att.payload.ok) {
                  var err = att.payload.error || "Pointage échoué.";
                  ctx.setStatus(err, "error");
                  return;
                }
                var data = att.payload.data || {};
                if (resultEl) {
                  resultEl.textContent =
                    (data.student_name || "") +
                    " (" +
                    (data.matricule || "") +
                    ") · " +
                    (data.class_name || "") +
                    " · " +
                    (data.operation_label || "") +
                    " · " +
                    (data.attendance_status || "") +
                    (data.late_minutes ? " · Retard: " + data.late_minutes + " min" : "");
                }
                ctx.setStatus(att.payload.message || "Pointage enregistré.", "ok");
              });
          });
      },
    });

    modal.querySelectorAll("[data-scan-mode]").forEach(function (button) {
      if (button.dataset.scanModeBound === "1") return;
      button.dataset.scanModeBound = "1";
      button.addEventListener("click", function () {
        applyMode(button.getAttribute("data-scan-mode") || "attendance");
        scanner.setStatus("");
        var input = modal.querySelector("[data-discipline-qr-manual]");
        if (input) input.value = "";
        if (isOpenModal(modal)) scanner.startScanner();
      });
    });

    document.querySelectorAll("[data-discipline-open-scanner]").forEach(function (button) {
      if (button.dataset.scanOpenBound === "1") return;
      button.dataset.scanOpenBound = "1";
      button.addEventListener("click", function () {
        var mode = button.getAttribute("data-default-mode") || "attendance";
        applyMode(mode);
        modal.setAttribute("data-class-public-id", button.getAttribute("data-class-public-id") || "");
        modal.setAttribute("data-sheet-date", button.getAttribute("data-sheet-date") || "");
        scanner.setStatus("");
      });
    });

    var page =
      document.querySelector('[data-page="discipline-attendance-daily"]') ||
      document.querySelector('[data-page="discipline-attendance-scan"]') ||
      document.querySelector('[data-page="discipline-attendance-sheet"]');
    if (page) {
      applyMode(page.getAttribute("data-default-scanner-mode") || "attendance");
      if (page.getAttribute("data-auto-open-scanner") === "1") {
        window.setTimeout(function () {
          var openBtn = page.querySelector("[data-discipline-open-scanner]");
          if (openBtn) openBtn.click();
        }, 200);
      }
    } else {
      applyMode("attendance");
    }
  }

  function isOpenModal(modal) {
    return modal.classList.contains("is-open") && !modal.hidden;
  }

  /* ---------- Finance ---------- */

  function initFinanceScanner() {
    var modal = document.querySelector("[data-finance-qr-scan-modal]");
    if (!modal || modal.dataset.financeScannerBound === "1") return;
    modal.dataset.financeScannerBound = "1";

    createQrScanner({
      modal: modal,
      readerId: "finance-qr-reader",
      manualInputSelector: "[data-finance-qr-manual]",
      manualSubmitSelector: "[data-finance-qr-manual-submit]",
      statusSelector: "[data-finance-qr-status]",
      onResolve: function (ctx) {
        var url = modal.getAttribute("data-resolve-url");
        if (!url) {
          ctx.setStatus("URL de résolution manquante.", "error");
          return;
        }
        ctx.setStatus("Carte reconnue, ouverture…", "ok");
        return fetch(url, {
          method: "POST",
          credentials: "same-origin",
          headers: csrfHeaders({ Accept: "application/json", "Content-Type": "application/json" }),
          body: JSON.stringify({ qr: ctx.raw }),
        })
          .then(function (response) {
            return response.json().catch(function () {
              return {};
            }).then(function (payload) {
              return { response: response, payload: payload };
            });
          })
          .then(function (result) {
            if (!result.response.ok || !result.payload.ok) {
              ctx.setStatus(result.payload.error || "QR non reconnu.", "error");
              return;
            }
            var redirectUrl =
              (result.payload.data && result.payload.data.redirect_url) ||
              result.payload.redirect_url;
            if (!redirectUrl) {
              ctx.setStatus("Redirection impossible.", "error");
              return;
            }
            window.location.href = redirectUrl;
          });
      },
    });
  }

  ready(function () {
    initDisciplineScanner();
    initFinanceScanner();
  });
})();
