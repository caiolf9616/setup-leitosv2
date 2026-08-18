(() => {
  const labels = { alta: 'Alta / Transferência', desocupado: 'Desocupado', apto: 'Apto', ocupado: 'Ocupado' };
  const badgeClass = { alta: 'interditado', desocupado: 'limpeza', apto: 'livre', ocupado: 'ocupado' };
  const $ = (id) => document.getElementById(id);
  const formatTime = (value) => new Intl.DateTimeFormat('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'America/Sao_Paulo'
  }).format(new Date(value));

  function setSummary(index, value) {
    const target = document.querySelectorAll('.resumo p')[index];
    if (target) target.lastChild.textContent = ` ${value}`;
  }

  function render(beds, events) {
    const activeBeds = beds.filter((bed) => !bed.blocked);
    const bedsWithoutStatus = activeBeds.filter((bed) => !bed.last_event_type).length;
    const count = (status) => activeBeds.filter((bed) => bed.last_event_type === status).length;
    $('altas').textContent = count('alta');
    $('desocupados').textContent = count('desocupado');
    $('aptos').textContent = count('apto');
    $('ocupados').textContent = count('ocupado');

    setSummary(0, activeBeds.length);
    setSummary(1, new Set(beds.map((bed) => bed.unit_group)).size);
    setSummary(2, bedsWithoutStatus);
    setSummary(3, activeBeds.length ? `${(count('ocupado') / activeBeds.length * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%` : '—');
    setSummary(4, events.length ? `${formatTime(events[0].occurred_at)} (${events[0].unit_group} · Leito ${events[0].bed_number})` : 'Sem movimentações');

    $('ultimasAtualizacoes').innerHTML = events.length ? events.map((event) => `<tr><td>${formatTime(event.occurred_at)}</td><td>${event.unit_group} · Leito ${event.bed_number}</td><td><span class="badge ${badgeClass[event.event_type] || ''}">${labels[event.event_type] || 'Sem status'}</span></td></tr>`).join('') : '<tr><td colspan="3">Ainda não há movimentações registradas.</td></tr>';
  }

  async function loadDashboard() {
    if (!await requireAuth()) return;
    try {
      const [bedsResponse, eventsResponse] = await Promise.all([
        fetch('/api/beds', { credentials: 'same-origin' }),
        fetch('/api/events/recent?limit=5', { credentials: 'same-origin' }),
      ]);
      if (!bedsResponse.ok || !eventsResponse.ok) throw new Error();
      render(await bedsResponse.json(), await eventsResponse.json());
    } catch {
      $('ultimasAtualizacoes').innerHTML = '<tr><td colspan="3">Não foi possível carregar os dados.</td></tr>';
    }
  }

  window.addEventListener('DOMContentLoaded', loadDashboard);
})();
