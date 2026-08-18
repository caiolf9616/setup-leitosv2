const form = document.getElementById('login-form');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const errorBox = document.getElementById('login-error');
const button = document.getElementById('login-button');
const buttonText = document.getElementById('login-button-text');

function mostrarErro(mensagem) {
    errorBox.textContent = mensagem;
    errorBox.hidden = false;
}

function esconderErro() {
    errorBox.hidden = true;
    errorBox.textContent = '';
}

function definirCarregando(carregando) {
    button.disabled = carregando;
    buttonText.textContent = carregando ? 'Entrando...' : 'Entrar';
}

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    esconderErro();
    definirCarregando(true);

    const username = usernameInput.value.trim();
    const password = passwordInput.value;

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            // 'same-origin' garante que o cookie de sessao criado na resposta
            // seja aceito -- login.html e a API rodam na mesma origem (mesmo
            // processo FastAPI), entao isso ja e o comportamento padrao do
            // fetch, mas deixamos explicito por clareza.
            credentials: 'same-origin',
            body: JSON.stringify({ username, password }),
        });

        if (response.status === 401) {
            mostrarErro('Login ou senha inválidos. Confira e tente de novo.');
            return;
        }

        if (response.status === 429) {
            const retryAfterSeconds = Number(response.headers.get('Retry-After')) || 300;
            const retryAfterMinutes = Math.max(1, Math.ceil(retryAfterSeconds / 60));
            mostrarErro(`Muitas tentativas de login. Aguarde ${retryAfterMinutes} minutos e tente novamente.`);
            return;
        }

        if (!response.ok) {
            mostrarErro('Não foi possível entrar agora. Tenta de novo em instantes.');
            return;
        }

        const credencial = await response.json();

        // Guarda so pra a proxima pagina poder mostrar "Unidade: X" sem
        // precisar chamar /api/auth/me de novo imediatamente. Nao e usado
        // pra autenticacao -- quem autentica de fato e o cookie httponly,
        // que o JS nem consegue ler.
        sessionStorage.setItem('username', credencial.username);
        sessionStorage.setItem('unit_group', credencial.unit_group);
        sessionStorage.setItem('display_name', credencial.display_name);
        sessionStorage.setItem('role', credencial.role);
        sessionStorage.setItem('employment_type', credencial.employment_type);

        window.location.href = credencial.must_change_password ? '/alterar-senha' : '/dashboard';
    } catch (erro) {
        console.error('Erro ao fazer login:', erro);
        mostrarErro('Sem conexão com o servidor. Confira sua rede e tente de novo.');
    } finally {
        definirCarregando(false);
    }
});

const forgotDialog = document.getElementById('forgotDialog');
document.getElementById('forgotPassword').onclick = () => forgotDialog.showModal();
document.getElementById('closeForgotDialog').onclick = () => forgotDialog.close();
