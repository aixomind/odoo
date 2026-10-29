/** @odoo-module **/
(function () {
    "use strict";

    const DASHBOARD_ROOTS = [
        ".l4e-dashboard-container",
        ".crm_dashboard_wrapper",
        ".o_sdash_page",
        ".l4e_dashboard_wrapper",
        ".o_financial_dashboard",
        ".amc_dashboard",
    ];
    const DARK_CLASSES = ["o_dark", "o_dark_mode", "o_dark_user", "o_is_dark"];
    const LIGHT_CLASSES = ["o_light", "o_light_mode"];
    const listeners = new Set();
    let lastTheme = null;

    function readCookie(name) {
        const prefix = `${name}=`;
        const item = document.cookie.split("; ").find((cookie) => cookie.startsWith(prefix));
        return item ? decodeURIComponent(item.slice(prefix.length)) : "";
    }

    function hasClass(element, classes) {
        return Boolean(element && classes.some((className) => element.classList.contains(className)));
    }

    function attrTheme(element) {
        if (!element) {
            return "";
        }
        for (const name of ["data-color-scheme", "data-bs-theme", "data-theme", "color-scheme"]) {
            const value = (element.getAttribute(name) || "").toLowerCase();
            if (value === "dark" || value === "light") {
                return value;
            }
        }
        return "";
    }

    function isDarkMode() {
        const cookieScheme = (readCookie("color_scheme") || readCookie("theme") || "").toLowerCase();
        if (cookieScheme === "dark") return true;
        if (cookieScheme === "light") return false;

        const candidates = [
            document.documentElement,
            document.body,
            document.querySelector(".o_web_client"),
            document.querySelector(".o_action_manager"),
        ];
        for (const element of candidates) {
            const theme = attrTheme(element);
            if (theme === "dark") return true;
            if (theme === "light") return false;
            if (hasClass(element, DARK_CLASSES)) return true;
            if (hasClass(element, LIGHT_CLASSES)) return false;
        }
        return Boolean(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
    }

    function applyTheme() {
        const dark = isDarkMode();
        const theme = dark ? "dark" : "light";
        document.documentElement.classList.toggle("l4e-theme-dark", dark);
        document.documentElement.classList.toggle("l4e-theme-light", !dark);
        document.querySelectorAll(DASHBOARD_ROOTS.join(",")).forEach((element) => {
            if (element.getAttribute("data-theme") !== theme) {
                element.setAttribute("data-theme", theme);
            }
        });
        if (theme !== lastTheme) {
            lastTheme = theme;
            listeners.forEach((callback) => callback(theme));
        }
        return theme;
    }

    function scheduleApply() {
        window.requestAnimationFrame(applyTheme);
    }

    window.l4eDashboardTheme = {
        isDark: isDarkMode,
        apply: applyTheme,
        subscribe(callback) {
            listeners.add(callback);
            callback(applyTheme());
            return () => listeners.delete(callback);
        },
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", scheduleApply, { once: true });
    } else {
        scheduleApply();
    }

    const observer = new MutationObserver(scheduleApply);
    observer.observe(document.documentElement, {
        attributes: true,
        childList: true,
        subtree: true,
        attributeFilter: ["class", "data-color-scheme", "data-bs-theme", "data-theme", "color-scheme"],
    });

    if (window.matchMedia) {
        const media = window.matchMedia("(prefers-color-scheme: dark)");
        if (media.addEventListener) {
            media.addEventListener("change", scheduleApply);
        } else if (media.addListener) {
            media.addListener(scheduleApply);
        }
    }

    window.addEventListener("focus", scheduleApply);
    setInterval(scheduleApply, 1500);
})();
