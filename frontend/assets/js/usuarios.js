(() => {
  const $ = (id) => document.getElementById(id);
  const labels = {
    diarista: 'Diarista',
    plantonista: 'Plantonista',
    coordenador_unidade: 'Coord. da unidade',
    coordenador_geral: 'Coordenação geral',
    administrador: 'Administrador',
    acesso_legado: 'Acesso legado'
  };
  const baseTypes = ['diarista', 'plantonista', 'coordenador_unidade'];
  let users = [];
  let credential = null;
  let securityMode = null;
  let securityUser = null;
  const esc = (value) => String(value).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  const isCentralType = (type) => ['coordenador_geral', 'administrador'].includes(type);

  function show(message, error = false) {
    $('feedback').textContent = message;
    $('feedback').classList.toggle('error', error);
    $('feedback').hidden = false;
  }

  function configureEmploymentTypes() {
    const allowed = [...baseTypes];
    if (['coordenador_geral', 'administrador'].includes(credential.employment_type)) allowed.push('coordenador_geral');
    if (credential.employment_type === 'administrador') allowed.push('administrador');
    $('employmentType').replaceChildren(...allowed.map((type) => new Option(labels[type], type)));
  }

  function syncScope() {
    const central = isCentralType($('employmentType').value);
    if (central) {
      if (![...$('unitGroup').options].some((option) => option.value === 'COORDENACAO')) {
        $('unitGroup').add(new Option('COORDENAÇÃO', 'COORDENACAO'));
      }
      $('unitGroup').value = 'COORDENACAO';
      $('unitGroup').disabled = true;
    } else if (credential.employment_type === 'coordenador_unidade') {
      $('unitGroup').value = credential.unit_group;
      $('unitGroup').disabled = true;
    } else {
      $('unitGroup').disabled = false;
      if ($('unitGroup').value === 'COORDENACAO') $('unitGroup').value = '';
    }
  }

  function render() {
    const query = $('userSearch').value.trim().toLocaleLowerCase('pt-BR');
    const visible = users.filter((u) => `${u.full_name} ${u.username} ${u.unit_group}`.toLocaleLowerCase('pt-BR').includes(query));
    $('userCount').textContent = `${visible.length} conta${visible.length === 1 ? '' : 's'}`;
    $('userRows').innerHTML = visible.map((u) => {
      const ownAccount = u.username === credential.username;
      const protectedAdmin = u.employment_type === 'administrador';
      const actions = [
        `<button class="action-button" data-action="password" data-id="${u.id}">Redefinir senha</button>`,
        !ownAccount && !protectedAdmin ? `<button class="action-button" data-action="replacement" data-id="${u.id}">Criar substituto</button>` : '',
        !ownAccount && !protectedAdmin ? `<button class="action-button" data-action="active" data-id="${u.id}">${u.active ? 'Desativar' : 'Ativar'}</button>` : '',
        !ownAccount && !protectedAdmin ? `<button class="action-button danger" data-action="delete" data-id="${u.id}">Excluir</button>` : ''
      ].join('');
      const statusLabel = !u.active ? 'Inativo' : u.must_change_password ? 'Senha temporária' : 'Ativo';
      const statusClass = !u.active ? 'inactive' : u.must_change_password ? 'warning' : '';
      return `<tr><td><strong>${esc(u.full_name)}</strong></td><td>${esc(u.username)}</td><td>${esc(u.unit_group)}</td><td>${labels[u.employment_type] || esc(u.employment_type)}</td><td><span class="status ${statusClass}">${statusLabel}</span></td><td>${actions}</td></tr>`;
    }).join('') || '<tr><td colspan="6">Nenhuma conta encontrada.</td></tr>';
  }

  async function loadUsers() {
    const response = await fetch('/api/users', { credentials:'same-origin' });
    if (response.status === 403) { location.href = '/dashboard'; return; }
    if (!response.ok) throw new Error('Não foi possível carregar os usuários.');
    users = await response.json();
    if (credential.employment_type !== 'administrador') {
      users = users.filter((user) => user.employment_type !== 'administrador');
    }
    render();
  }

  async function patchUser(id, payload) {
    const response = await fetch(`/api/users/${id}`, { method:'PATCH', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload) });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || 'Não foi possível atualizar a conta.');
    await loadUsers();
  }

  async function postAction(url, payload) {
    const response = await fetch(url, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || 'Não foi possível concluir a operação.');
    await loadUsers();
    await loadAudit();
  }

  async function loadAudit() {
    const response = await fetch('/api/users/audit/recent', { credentials:'same-origin' });
    if (!response.ok) return;
    const labels = {user_created:'Usuário criado', user_updated:'Conta alterada', user_deleted:'Usuário excluído', password_reset:'Senha redefinida', user_replaced:'Substituição'};
    const logs = await response.json();
    $('auditRows').innerHTML = logs.map((log) => `<tr><td>${new Date(log.created_at).toLocaleString('pt-BR')}</td><td>${esc(log.actor_username)}</td><td>${labels[log.action] || esc(log.action)}</td><td>${esc(log.target_username || '—')}</td><td>${esc(log.details || '—')}</td></tr>`).join('') || '<tr><td colspan="5">Nenhuma alteração registrada.</td></tr>';
  }

  function openSecurityDialog(mode, user) {
    securityMode = mode;
    securityUser = user;
    $('securityForm').reset();
    const replacement = mode === 'replacement';
    $('replacementFields').hidden = !replacement;
    $('replacementName').required = replacement;
    $('replacementUsername').required = replacement;
    $('securityTitle').textContent = replacement ? 'Criar substituto' : 'Redefinir senha';
    $('securityDescription').textContent = replacement
      ? `O novo usuário receberá o mesmo perfil e unidade de ${user.full_name}, sem copiar senha ou histórico.`
      : `${user.full_name} receberá uma senha temporária e deverá criar uma senha pessoal no próximo acesso.`;
    $('securityDialog').showModal();
  }

  window.addEventListener('DOMContentLoaded', async () => {
    credential = await requireAuth();
    if (!credential) return;
    const canManage = credential.employment_type === 'administrador';
    if (!canManage) {
      document.querySelector('.users-page').innerHTML = '<section class="panel permission-denied"><i class="fa-solid fa-lock"></i><h1>Usuário sem permissão</h1><p>Somente o administrador pode gerenciar usuários.</p><a href="/dashboard">Voltar ao dashboard</a></section>';
      return;
    }
    try {
      const wardsResponse = await fetch('/api/wards', { credentials:'same-origin' });
      if (!wardsResponse.ok) throw new Error('Não foi possível carregar as unidades.');
      const wards = await wardsResponse.json();
      [...new Set(wards.map((w) => w.unit_group))].sort().forEach((unit) => $('unitGroup').add(new Option(unit, unit)));
      configureEmploymentTypes();
      syncScope();
      await loadUsers();
      await loadAudit();
    } catch (error) { show(error.message, true); }

    $('employmentType').onchange = syncScope;
    $('userSearch').oninput = render;
    $('userForm').onsubmit = async (event) => {
      event.preventDefault();
      const employmentType = $('employmentType').value;
      const payload = {
        full_name:$('fullName').value,
        username:$('username').value,
        password:$('password').value,
        employment_type:employmentType,
        unit_group:isCentralType(employmentType) ? 'COORDENACAO' : $('unitGroup').value,
        role:isCentralType(employmentType) ? 'coordenador' : 'unidade'
      };
      try {
        const response = await fetch('/api/users', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || 'Não foi possível cadastrar.');
        event.target.reset();
        syncScope();
        show('Usuário cadastrado com sucesso.');
        await loadUsers();
      } catch (error) { show(error.message, true); }
    };
    $('userRows').onclick = async (event) => {
      const button = event.target.closest('button[data-id]');
      if (!button) return;
      const user = users.find((u) => u.id === Number(button.dataset.id));
      if (!user) return;
      try {
        if (button.dataset.action === 'active') await patchUser(user.id, {active:!user.active});
        else if (button.dataset.action === 'delete') {
          if (!confirm(`Excluir permanentemente a conta de ${user.full_name} (${user.username})?\n\nO histórico de movimentações será preservado.`)) return;
          const response = await fetch(`/api/users/${user.id}`, {method:'DELETE', credentials:'same-origin'});
          if (!response.ok) { const body = await response.json(); throw new Error(body.detail || 'Não foi possível excluir a conta.'); }
          show('Usuário excluído com sucesso.');
          await loadUsers();
        } else if (button.dataset.action === 'password') {
          openSecurityDialog('password', user);
        } else if (button.dataset.action === 'replacement') {
          openSecurityDialog('replacement', user);
        }
      } catch (error) { show(error.message, true); }
    };
    $('cancelSecurityDialog').onclick = () => $('securityDialog').close();
    $('securityForm').onsubmit = async (event) => {
      event.preventDefault();
      const password = $('temporaryPassword').value;
      try {
        if (securityMode === 'replacement') {
          await postAction(`/api/users/${securityUser.id}/replacement`, {
            full_name:$('replacementName').value,
            username:$('replacementUsername').value,
            temporary_password:password,
            deactivate_source:$('deactivateSource').checked
          });
          show('Substituto criado com o mesmo perfil e senha temporária.');
        } else {
          await postAction(`/api/users/${securityUser.id}/reset-password`, {temporary_password:password});
          show('Senha temporária definida. O usuário deverá trocá-la no próximo acesso.');
        }
        $('securityDialog').close();
      } catch (error) { $('securityDialog').close(); show(error.message, true); }
    };
  });
})();
