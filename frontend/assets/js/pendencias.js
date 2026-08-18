(() => {
  const labels = { alta: 'Alta / Transferência', desocupado: 'Desocupado', apto: 'Apto' };
  const watchedStatuses = new Set(Object.keys(labels));
  const limitsMinutes = { alta: 60, desocupado: 60, apto: 360 };
  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[char]);
  let beds = [];

  function elapsedMinutes(bed) {
    if (!bed.last_event_at) return 0;
    return Math.max(0, Math.floor((Date.now() - new Date(bed.last_event_at).getTime()) / 60000));
  }

  function duration(minutes) {
    const days = Math.floor(minutes / 1440);
    const hours = Math.floor((minutes % 1440) / 60);
    const rest = minutes % 60;
    if (days) return `${days}d ${hours}h`;
    if (hours) return `${hours}h ${rest}min`;
    return `${rest}min`;
  }

  function isOverdue(bed) {
    return elapsedMinutes(bed) >= limitsMinutes[bed.last_event_type];
  }

  function render() {
    const monitored = beds.filter((bed) => !bed.blocked && watchedStatuses.has(bed.last_event_type));
    const unit = $('pendingUnit').value;
    const status = $('pendingStatus').value;
    const critical = $('pendingCritical').value;
    const filtered = monitored.filter((bed) => {
      if (unit && bed.unit_group !== unit) return false;
      if (status && bed.last_event_type !== status) return false;
      if (critical === 'overdue' && !isOverdue(bed)) return false;
      if (critical === 'normal' && isOverdue(bed)) return false;
      return true;
    }).sort((a, b) => Number(isOverdue(b)) - Number(isOverdue(a)) || elapsedMinutes(b) - elapsedMinutes(a));

    $('trackedBeds').textContent = monitored.length;
    $('overdueBeds').textContent = monitored.filter(isOverdue).length;
    $('highOverdue').textContent = monitored.filter((bed) => bed.last_event_type === 'alta' && isOverdue(bed)).length;
    $('vacatedOverdue').textContent = monitored.filter((bed) => bed.last_event_type === 'desocupado' && isOverdue(bed)).length;
    $('pendingCount').textContent = `${filtered.length} leito${filtered.length === 1 ? '' : 's'}`;
    $('pendingRows').innerHTML = filtered.length ? filtered.map((bed) => {
      const overdue = isOverdue(bed);
      return `<tr class="${overdue ? 'overdue-row' : ''}">
        <td data-label="Unidade / leito"><strong>${esc(bed.unit_group)} · Leito ${esc(bed.number)}</strong><small>${esc(bed.ward_name)}</small></td>
        <td data-label="Status"><span class="status-pill ${bed.last_event_type}">${labels[bed.last_event_type]}</span></td>
        <td data-label="Tempo"><strong class="elapsed ${overdue ? 'overdue' : ''}">${duration(elapsedMinutes(bed))}</strong><small>${overdue ? 'Tempo acima do esperado' : 'Dentro do limite atual'}</small></td>
        <td data-label="Pendência"><span class="waiting-value"><i class="fa-solid fa-link-slash"></i> Aguardando integração</span></td>
        <td data-label="Setor"><span class="placeholder-value">—</span></td>
        <td data-label="Prioridade"><span class="placeholder-value">—</span></td>
        <td data-label="Previsão"><span class="placeholder-value">—</span></td>
        <td data-label="Ação"><button class="kanbam-button" type="button" disabled title="Disponível após a integração"><i class="fa-solid fa-arrow-up-right-from-square"></i> Ver no Kanbam</button></td>
      </tr>`;
    }).join('') : '<tr><td class="empty-row" colspan="8">Nenhum leito encontrado para os filtros selecionados.</td></tr>';
  }

  async function loadPending() {
    const button = $('refreshPending');
    button.disabled = true;
    try {
      if (!await requireAuth()) return;
      const response = await fetch('/api/beds', { credentials: 'same-origin', cache: 'no-store' });
      if (!response.ok) throw new Error('Não foi possível carregar os leitos.');
      beds = await response.json();
      const units = [...new Set(beds.map((bed) => bed.unit_group))].sort((a, b) => a.localeCompare(b, 'pt-BR', { numeric: true }));
      const selected = $('pendingUnit').value;
      $('pendingUnit').innerHTML = '<option value="">Todas as unidades</option>' + units.map((name) => `<option value="${esc(name)}">${esc(name)}</option>`).join('');
      $('pendingUnit').value = selected;
      render();
      $('pendingMessage').textContent = `Atualizado em ${new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Sao_Paulo' }).format(new Date())}.`;
    } catch (error) {
      $('pendingMessage').className = 'pending-message error';
      $('pendingMessage').textContent = error.message;
    } finally {
      button.disabled = false;
    }
  }

  window.addEventListener('DOMContentLoaded', () => {
    ['pendingUnit', 'pendingStatus', 'pendingCritical'].forEach((id) => $(id).addEventListener('change', render));
    $('refreshPending').addEventListener('click', loadPending);
    loadPending();
    setInterval(() => beds.length && render(), 60000);
  });
})();
