const form = document.getElementById('changePasswordForm');
const message = document.getElementById('passwordMessage');

async function ensureTemporarySession() {
  const response = await fetch('/api/auth/me', { credentials: 'same-origin' });
  if (!response.ok) return location.replace('/login');
  const credential = await response.json();
  if (!credential.must_change_password) location.replace('/dashboard');
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const newPassword = document.getElementById('newPassword').value;
  const confirmation = document.getElementById('confirmPassword').value;
  message.hidden = true;
  if (newPassword !== confirmation) {
    message.textContent = 'As senhas não coincidem.';
    message.hidden = false;
    return;
  }
  const response = await fetch('/api/auth/change-password', {
    method: 'POST', credentials: 'same-origin',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({new_password: newPassword}),
  });
  const body = await response.json();
  if (!response.ok) {
    message.textContent = body.detail || 'Não foi possível alterar a senha.';
    message.hidden = false;
    return;
  }
  sessionStorage.clear();
  location.replace('/login?password_changed=1');
});

ensureTemporarySession();
