async function loadComponent(id, file) {
    const response = await fetch(`./components/${file}`, { cache: "no-store" });
    document.getElementById(id).innerHTML = await response.text();
}

const PAGE_HEADERS = {
    dashboard: { eyebrow: "Visão geral", title: "Dashboard de leitos", icon: "fa-chart-pie" },
    leitos: { eyebrow: "Controle de leitos", title: "Leitos", icon: "fa-bed" },
    indicadores: { eyebrow: "Análise assistencial", title: "Indicadores", icon: "fa-chart-line" },
    pendencias: { eyebrow: "Acompanhamento operacional", title: "Pendências", icon: "fa-list-check" },
    relatorio: { eyebrow: "Visão operacional", title: "Relatórios", icon: "fa-file-lines" },
    usuarios: { eyebrow: "Controle de acesso", title: "Usuários", icon: "fa-users" },
};

function updatePageHeader() {
    const page = window.location.pathname.split("/").filter(Boolean).pop() || "dashboard";
    const header = PAGE_HEADERS[page] || PAGE_HEADERS.dashboard;
    const eyebrow = document.querySelector(".header-title > div > span");
    const title = document.querySelector(".header-title h1");
    const icon = document.querySelector(".header-icon i");

    if (eyebrow) eyebrow.textContent = header.eyebrow;
    if (title) title.textContent = header.title;
    if (icon) icon.className = `fa-solid ${header.icon}`;
}

window.addEventListener("DOMContentLoaded", async () => {
    await loadComponent("sidebar", "sidebar.html");
    await loadComponent("header", "header.html");
    await loadComponent("footer", "footer.html");

    updatePageHeader();
    atualizarDataHora();
    setInterval(atualizarDataHora, 1000);

    // Informa que o layout terminou de carregar.
    window.dispatchEvent(new Event("layoutLoaded"));
});

function atualizarDataHora() {
    const agora = new Date();
    const data = agora.toLocaleDateString("pt-BR");
    const hora = agora.toLocaleTimeString("pt-BR");
    const dataElement = document.getElementById("currentDate");
    const horaElement = document.getElementById("currentTime");

    if (dataElement) dataElement.textContent = data;
    if (horaElement) horaElement.textContent = hora;
}
