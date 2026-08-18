(() => {
  const labels = { alta: 'Alta', desocupado: 'Desocupado', apto: 'Apto', ocupado: 'Ocupado' };
  const nextStatus = { ocupado: 'alta', alta: 'desocupado', desocupado: 'apto', apto: 'ocupado' };
  let beds = [], selectedBed = null, credential = null, wardGroups = {}, wards = [];
  let pendingBlockChange = null;
  const $ = (id) => document.getElementById(id);
  const nowValue = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  const show = (message, error = false) => { const box = $('feedback'); box.textContent = message; box.classList.toggle('error', error); box.hidden = false; };

  function bedCard(bed) {
    const status = bed.last_event_type || 'sem_status';
    const canEdit = credential.role === 'coordenador' || wardGroups[bed.ward_id] === credential.unit_group;
    const wrapper = document.createElement('div');
    wrapper.className = `bed-card-wrap ${bed.blocked ? 'blocked' : ''}`;
    const el = document.createElement('button');
    el.type = 'button';
    el.className = `bed-card ${selectedBed?.id === bed.id ? 'selected' : ''}`;
    el.disabled = bed.blocked || !canEdit;
    el.title = bed.blocked ? 'Desbloqueie o leito para registrar um status.' : (!canEdit ? 'Leito de outra unidade: somente consulta.' : '');
    el.innerHTML = `<strong>${bed.number}</strong><small><span class="status-dot status-${status}"></span>${bed.blocked ? 'Bloqueado' : labels[status] || 'Sem status'}</small>${!canEdit ? '<small>Somente consulta</small>' : ''}`;
    el.onclick = () => selectBed(bed);
    wrapper.append(el);

    if (canEdit && (bed.blocked || !bed.last_event_type || ['apto', 'desocupado'].includes(bed.last_event_type))) {
      const toggle = document.createElement('button');
      toggle.type = 'button';
      toggle.className = `bed-lock-button ${bed.blocked ? 'unlock' : 'lock'}`;
      toggle.setAttribute('aria-label', `${bed.blocked ? 'Desbloquear' : 'Bloquear'} leito ${bed.number}`);
      toggle.innerHTML = `<i class="fa-solid ${bed.blocked ? 'fa-lock-open' : 'fa-lock'}"></i>${bed.blocked ? 'Desbloquear' : 'Bloquear'}`;
      toggle.onclick = () => openBlockDialog(bed, toggle);
      wrapper.append(toggle);
    }

    return wrapper;
  }

  function openBlockDialog(bed, button) {
    const action = bed.blocked ? 'desbloquear' : 'bloquear';
    pendingBlockChange = { bed, button };
    $('blockDialogEyebrow').textContent = bed.blocked ? 'Reativar leito' : 'Controle interno';
    $('blockDialogTitle').textContent = bed.blocked ? 'Desbloquear leito?' : 'Bloquear leito?';
    $('blockDialogText').textContent = bed.blocked
      ? `Deseja realmente desbloquear o leito ${bed.ward_name} · ${bed.number}? Ele voltará a aceitar atualizações e poderá aparecer no painel conforme o último status.`
      : `Deseja realmente bloquear o leito ${bed.ward_name} · ${bed.number}? Ele deixará de aparecer no painel e não aceitará novos status enquanto estiver bloqueado.`;
    $('confirmBlockChange').innerHTML = `<i class="fa-solid ${bed.blocked ? 'fa-lock-open' : 'fa-lock'}"></i> ${bed.blocked ? 'Sim, desbloquear' : 'Sim, bloquear'}`;
    $('confirmBlockChange').classList.toggle('danger', !bed.blocked);
    $('blockDialog').showModal();
  }

  function closeBlockDialog() {
    if ($('blockDialog').open) $('blockDialog').close();
    pendingBlockChange = null;
  }

  async function applyBedBlock() {
    if (!pendingBlockChange) return;
    const { bed, button } = pendingBlockChange;
    const action = bed.blocked ? 'desbloquear' : 'bloquear';
    button.disabled = true;
    $('confirmBlockChange').disabled = true;
    try {
      const response = await fetch(`/api/beds/${bed.id}/blocked`, {
        method: 'PATCH',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ blocked: !bed.blocked }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || `Não foi possível ${action} o leito.`);
      closeBlockDialog();
      show(`Leito ${bed.number} ${body.blocked ? 'bloqueado' : 'desbloqueado'} com sucesso.`);
      await loadBeds();
    } catch (error) {
      show(error.message, true);
      button.disabled = false;
    } finally {
      $('confirmBlockChange').disabled = false;
    }
  }

  function render() {
    const grid = $('bedsGrid');
    const unitGroup = $('unitSelect').value;
    const unitWards = wards.filter((ward) => ward.unit_group === unitGroup);
    $('bedCounter').textContent = beds.length
      ? `${unitWards.length} enfermaria${unitWards.length === 1 ? '' : 's'} · ${beds.length} leito${beds.length === 1 ? '' : 's'}`
      : (unitGroup ? 'Nenhum leito encontrado' : 'Selecione uma unidade');
    grid.replaceChildren();
    if (!beds.length) {
      grid.innerHTML = `<p class="empty-state">${unitGroup ? 'Nenhum leito encontrado nesta unidade.' : 'Selecione uma unidade para visualizar as enfermarias e os leitos.'}</p>`;
      return;
    }
    unitWards.forEach((ward) => {
      const wardBeds = beds.filter((bed) => bed.ward_id === ward.id);
      if (!wardBeds.length) return;
      const section = document.createElement('section');
      section.className = 'ward-section';
      section.innerHTML = `<header><div><span>Enfermaria</span><h3>${ward.display_name}</h3></div><strong>${wardBeds.length} leito${wardBeds.length === 1 ? '' : 's'}</strong></header>`;
      const cards = document.createElement('div');
      cards.className = 'ward-beds';
      wardBeds.forEach((bed) => cards.append(bedCard(bed)));
      section.append(cards);
      grid.append(section);
    });
  }

  function selectBed(bed) {
    selectedBed = bed;
    $('selectedBedText').textContent = `${bed.ward_name} · Leito ${bed.number}`;
    $('eventOptions').disabled = false;
    const allowedStatus = nextStatus[bed.last_event_type] || null;
    $('statusFlowHint').textContent = allowedStatus
      ? `Fluxo obrigatório: após ${labels[bed.last_event_type]}, selecione ${labels[allowedStatus]}.`
      : 'Leito sem histórico: selecione o status inicial.';
    document.querySelectorAll('#eventOptions .event-option').forEach((option) => {
      const input = option.querySelector('input[name="eventType"]');
      const allowed = !allowedStatus || input.value === allowedStatus;
      input.disabled = !allowed;
      option.classList.toggle('unavailable', !allowed);
      option.setAttribute('aria-disabled', String(!allowed));
      option.title = allowed ? 'Próxima etapa permitida' : `Indisponível enquanto o leito estiver ${labels[bed.last_event_type]}`;
    });
    $('saveEvent').disabled = false;
    render();
    $('eventDialog').showModal();
  }

  async function closeEventDialog(smooth = false) {
    const dialog = $('eventDialog');
    if (dialog.open && smooth) {
      dialog.classList.add('closing');
      await new Promise((resolve) => setTimeout(resolve, 180));
    }
    if (dialog.open) dialog.close();
    dialog.classList.remove('closing');
    $('eventForm').reset();
    document.querySelectorAll('#eventOptions .event-option').forEach((option) => {
      option.querySelector('input[name="eventType"]').disabled = false;
      option.classList.remove('unavailable');
      option.removeAttribute('aria-disabled');
      option.removeAttribute('title');
    });
    $('statusFlowHint').textContent = 'Selecione o novo status do leito.';
    $('useCurrentTime').checked = true;
    $('occurredAt').disabled = true;
    $('occurredAt').value = nowValue();
    selectedBed = null;
    $('eventOptions').disabled = true;
    $('saveEvent').disabled = true;
    $('selectedBedText').textContent = 'Escolha um leito para começar.';
    render();
  }

  async function loadBeds() {
    selectedBed = null;
    $('eventOptions').disabled = true;
    $('saveEvent').disabled = true;
    $('selectedBedText').textContent = 'Escolha um leito para começar.';
    const unitGroup = $('unitSelect').value;
    if (!unitGroup) { beds = []; render(); return; }
    try {
      const response = await fetch(`/api/beds?unit_group=${encodeURIComponent(unitGroup)}`, { credentials: 'same-origin' });
      if (!response.ok) throw new Error('Não foi possível carregar os leitos.');
      beds = await response.json();
      render();
    } catch (error) { beds = []; render(); show(error.message, true); }
  }

  async function start() {
    credential = await requireAuth(); if (!credential) return;
    $('registrationUser').textContent = credential.display_name;
    $('occurredAt').value = nowValue();
    $('occurredAt').disabled = true;
    $('useCurrentTime').onchange = (event) => { $('occurredAt').disabled = event.target.checked; if (event.target.checked) $('occurredAt').value = nowValue(); };
    $('closeEventDialog').onclick = closeEventDialog;
    $('eventDialog').addEventListener('click', (event) => { if (event.target === $('eventDialog')) closeEventDialog(); });
    $('eventDialog').addEventListener('cancel', (event) => { event.preventDefault(); closeEventDialog(); });
    $('cancelBlockChange').onclick = closeBlockDialog;
    $('confirmBlockChange').onclick = applyBedBlock;
    $('blockDialog').addEventListener('click', (event) => { if (event.target === $('blockDialog')) closeBlockDialog(); });
    $('blockDialog').addEventListener('cancel', (event) => { event.preventDefault(); closeBlockDialog(); });
    try {
      const response = await fetch('/api/wards', { credentials: 'same-origin' });
      if (!response.ok) throw new Error('Não foi possível carregar as enfermarias.');
      wards = await response.json();
      wards.sort((a, b) => a.display_name.localeCompare(b.display_name, 'pt-BR', { numeric: true }));
      wards.forEach((ward) => { wardGroups[ward.id] = ward.unit_group; });
      [...new Set(wards.map((ward) => ward.unit_group))]
        .sort((a, b) => a.localeCompare(b, 'pt-BR', { numeric: true }))
        .forEach((unitGroup) => $('unitSelect').add(new Option(unitGroup, unitGroup)));
      if (credential.role !== 'coordenador' && wards.some((ward) => ward.unit_group === credential.unit_group)) {
        $('unitSelect').value = credential.unit_group;
        await loadBeds();
      } else render();
    } catch (error) { show(error.message, true); }
    $('unitSelect').onchange = loadBeds;
    $('eventForm').onsubmit = async (event) => {
      event.preventDefault(); const form = event.currentTarget; const eventType = new FormData(form).get('eventType');
      if (!selectedBed || !eventType) { show('Selecione o leito e o novo status.', true); return; }
      const payload = { bed_id: selectedBed.id, event_type: eventType };
      if (!$('useCurrentTime').checked) payload.occurred_at = new Date($('occurredAt').value).toISOString();
      $('saveEvent').disabled = true;
      try {
        const response = await fetch('/api/events', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || 'Não foi possível registrar o evento.');
        show(`Evento “${labels[eventType]}” registrado para o leito ${selectedBed.number}.`);
        form.reset(); $('useCurrentTime').checked = true; $('occurredAt').disabled = true; $('occurredAt').value = nowValue();
        await closeEventDialog(true);
        await loadBeds();
      } catch (error) { show(error.message, true); $('saveEvent').disabled = false; }
    };
  }
  window.addEventListener('DOMContentLoaded', start);
})();
