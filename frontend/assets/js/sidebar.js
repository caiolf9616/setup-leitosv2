function initializeSidebar() {
    const sidebar = document.querySelector(".sidebar");
    const toggle = document.querySelector(".toggle-sidebar");
    const logoutButton = document.querySelector(".logout-btn");
    const mobileToggle = document.querySelector(".mobile-nav-toggle");

    if (!sidebar || !toggle) return;

    const backdrop = document.createElement("button");
    backdrop.className = "sidebar-backdrop";
    backdrop.type = "button";
    backdrop.setAttribute("aria-label", "Fechar menu");
    document.body.append(backdrop);

    const closeMobileMenu = () => {
        sidebar.classList.remove("mobile-open");
        backdrop.classList.remove("visible");
        document.body.classList.remove("sidebar-open");
        mobileToggle?.setAttribute("aria-expanded", "false");
    };

    const openMobileMenu = () => {
        sidebar.classList.remove("closed");
        sidebar.classList.add("mobile-open");
        backdrop.classList.add("visible");
        document.body.classList.add("sidebar-open");
        mobileToggle?.setAttribute("aria-expanded", "true");
    };

    toggle.addEventListener("click", () => {
        if (window.matchMedia("(max-width: 768px)").matches) {
            closeMobileMenu();
            return;
        }
        sidebar.classList.toggle("closed");

        const icon = toggle.querySelector("i");
        if (sidebar.classList.contains("closed")) {
            icon.className = "fa-solid fa-chevron-right";
            toggle.setAttribute("aria-label", "Expandir menu");
            toggle.setAttribute("title", "Expandir menu");
        } else {
            icon.className = "fa-solid fa-chevron-left";
            toggle.setAttribute("aria-label", "Recolher menu");
            toggle.setAttribute("title", "Recolher menu");
        }
    });

    mobileToggle?.addEventListener("click", () => {
        sidebar.classList.contains("mobile-open") ? closeMobileMenu() : openMobileMenu();
    });
    backdrop.addEventListener("click", closeMobileMenu);
    document.querySelectorAll(".sidebar-menu a").forEach((item) => item.addEventListener("click", closeMobileMenu));
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeMobileMenu();
    });
    window.addEventListener("resize", () => {
        if (!window.matchMedia("(max-width: 768px)").matches) closeMobileMenu();
    });

    const currentPage = window.location.pathname.split("/").filter(Boolean).pop() || "dashboard";
    document.querySelectorAll(".sidebar-menu .menu-item").forEach((item) => {
        const targetPage = new URL(item.href, window.location.origin).pathname
            .split("/")
            .filter(Boolean)
            .pop();
        const isCurrentPage = targetPage === currentPage;
        item.classList.toggle("active", isCurrentPage);
        if (isCurrentPage) item.setAttribute("aria-current", "page");
    });

    logoutButton?.addEventListener("click", async () => {
        try {
            await fetch("/api/auth/logout", {
                method: "POST",
                credentials: "same-origin",
            });
        } finally {
            sessionStorage.clear();
            window.location.href = "/login";
        }
    });
}

window.addEventListener("layoutLoaded", initializeSidebar, { once: true });
