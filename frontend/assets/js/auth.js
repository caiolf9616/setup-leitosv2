/**
 * Inclui esse script nas paginas que exigem login (index.html, registro.html,
 * relatorio.html, indicadores.html) e chama requireAuth() assim que a pagina
 * carregar. Se nao houver sessao valida, manda pro login antes do usuario
 * ver qualquer conteudo.
 *
 * Uso no HTML da pagina protegida:
 *   <script src="/assets/js/auth.js"></script>
 *   <script>
 *     requireAuth().then((credencial) => {
 *       // credencial.unit_group, credencial.display_name, credencial.role
 *     });
 *   </script>
 */
function applyCredentialToLayout(credencial) {
    if (!credencial) return;
    const isGeneralCoordinator = credencial.role === 'coordenador';
    const name = credencial.display_name;
    const roleLabels = {
        diarista: 'Diarista',
        plantonista: 'Plantonista',
        coordenador_unidade: 'Coordenação da unidade',
        coordenador_geral: 'Coordenação geral',
        administrador: 'Administrador do sistema',
        acesso_legado: 'Acesso da unidade',
    };
    const role = roleLabels[credencial.employment_type] || (isGeneralCoordinator ? 'Coordenação geral' : 'Acesso da unidade');
    const initial = name.trim().charAt(0).toUpperCase() || 'U';

    const setText = (id, value) => {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    };

    setText('headerUserAvatar', initial);
    setText('headerUserName', name);
    setText('headerUserRole', role);
    setText('sidebarUserName', name);
    setText('sidebarUserRole', role);

    const headerUser = document.getElementById('headerUser');
    if (headerUser) headerUser.title = `${name} — ${role}`;
    const canManageUsers = credencial.employment_type === 'administrador';
    document.querySelectorAll('[data-user-manager-only]').forEach((element) => {
        element.hidden = !canManageUsers;
    });
    document.querySelectorAll('[data-coordinator-only]').forEach((element) => {
        element.hidden = !isGeneralCoordinator;
    });
}

function storedCredential() {
    const unit_group = sessionStorage.getItem('unit_group');
    const display_name = sessionStorage.getItem('display_name');
    const role = sessionStorage.getItem('role');
    const employment_type = sessionStorage.getItem('employment_type');
    return unit_group && display_name && role ? { unit_group, display_name, role, employment_type } : null;
}

window.addEventListener('layoutLoaded', () => applyCredentialToLayout(storedCredential()));

async function fetchCurrentCredential(maxAttempts = 3) {
    let lastError;

    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
        try {
            const response = await fetch('/api/auth/me', {
                credentials: 'same-origin',
                cache: 'no-store',
            });

            // Somente uma resposta de autenticação encerra a sessão local.
            if (response.status === 401 || response.status === 403) return response;
            if (response.ok) return response;
            lastError = new Error(`Falha temporária ao validar a sessão (${response.status})`);
        } catch (error) {
            lastError = error;
        }

        if (attempt < maxAttempts) {
            await new Promise((resolve) => setTimeout(resolve, attempt * 700));
        }
    }

    throw lastError || new Error('Não foi possível validar a sessão');
}

async function requireAuth() {
    try {
        const response = await fetchCurrentCredential();
        if (response.status === 401 || response.status === 403) {
            sessionStorage.clear();
            window.location.href = '/login';
            return null;
        }
        const credencial = await response.json();
        if (credencial.must_change_password && window.location.pathname !== '/alterar-senha') {
            window.location.href = '/alterar-senha';
            return null;
        }
        sessionStorage.setItem('unit_group', credencial.unit_group);
        sessionStorage.setItem('display_name', credencial.display_name);
        sessionStorage.setItem('role', credencial.role);
        sessionStorage.setItem('employment_type', credencial.employment_type);
        applyCredentialToLayout(credencial);
        return credencial;
    } catch (erro) {
        console.error('Erro ao checar sessao:', erro);
        // Uma queda breve de rede não significa que a sessão expirou. Mantemos
        // a tela atual para que o usuário possa tentar novamente ao reconectar.
        return null;
    }
}

async function fazerLogout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' });
    } finally {
        sessionStorage.clear();
        window.location.href = '/login';
    }
}
