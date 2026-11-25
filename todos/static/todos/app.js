(function () {
  "use strict";

  var THEME_KEY = "taskpilot-theme";
  var root = document.documentElement;
  var media =
    window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function readStoredTheme() {
    try {
      return window.localStorage.getItem(THEME_KEY);
    } catch (error) {
      return null;
    }
  }

  function storeTheme(theme) {
    try {
      window.localStorage.setItem(THEME_KEY, theme);
    } catch (error) {
      /* Sin persistencia: el tema sigue funcionando en esta página. */
    }
  }

  function syncThemeControls() {
    var isDark = root.classList.contains("dark");
    root.style.colorScheme = isDark ? "dark" : "light";
    document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
      var label = isDark ? "Cambiar a modo claro" : "Cambiar a modo oscuro";
      button.setAttribute("aria-pressed", isDark ? "true" : "false");
      button.setAttribute("aria-label", label);
      button.setAttribute("title", label);
    });
  }

  function applyTheme(isDark, persist) {
    root.classList.toggle("dark", isDark);
    if (persist) storeTheme(isDark ? "dark" : "light");
    syncThemeControls();
  }

  document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
    button.addEventListener("click", function () {
      applyTheme(!root.classList.contains("dark"), true);
    });
  });

  if (media) {
    var onSystemChange = function (event) {
      if (!readStoredTheme()) applyTheme(event.matches, false);
    };
    if (media.addEventListener) {
      media.addEventListener("change", onSystemChange);
    } else if (media.addListener) {
      media.addListener(onSystemChange);
    }
  }

  syncThemeControls();

  var container = document.getElementById("app-messages");
  if (!container) return;

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  function removeToast(toast) {
    if (toast.parentNode) toast.parentNode.removeChild(toast);
    if (container && !container.querySelector("[data-app-message]")) {
      container.remove();
    }
  }

  container.querySelectorAll("[data-app-message]").forEach(function (toast) {
    var remaining = parseInt(toast.getAttribute("data-autohide"), 10) || 0;
    var timer = null;
    var startedAt = 0;
    var closed = false;

    function dismiss() {
      if (closed) return;
      closed = true;
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }

      if (reduceMotion.matches) {
        removeToast(toast);
        return;
      }

      toast.classList.add("is-hiding");
      var removed = false;
      function finish() {
        if (removed) return;
        removed = true;
        removeToast(toast);
      }

      toast.addEventListener("animationend", finish, { once: true });
      window.setTimeout(finish, 260);
    }

    function startTimer() {
      if (closed || remaining <= 0) return;
      startedAt = Date.now();
      timer = window.setTimeout(dismiss, remaining);
    }

    function pauseTimer() {
      if (closed || !timer) return;
      clearTimeout(timer);
      timer = null;
      remaining -= Date.now() - startedAt;
      if (remaining < 0) remaining = 0;
    }

    function resumeTimer() {
      if (closed || timer || remaining <= 0) return;
      startTimer();
    }

    var closeButton = toast.querySelector("[data-message-close]");
    if (closeButton) closeButton.addEventListener("click", dismiss);

    toast.addEventListener("mouseenter", pauseTimer);
    toast.addEventListener("mouseleave", resumeTimer);
    toast.addEventListener("focusin", pauseTimer);
    toast.addEventListener("focusout", function (event) {
      if (!toast.contains(event.relatedTarget)) resumeTimer();
    });

    startTimer();
  });
})();
