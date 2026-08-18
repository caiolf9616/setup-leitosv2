(() => {
  const labels = { alta: 'Alta / Transferência', desocupado: 'Desocupado', apto: 'Apto', ocupado: 'Ocupado', sem_status: 'Sem status' };
  const rowsPerPdfPage = 16;
  const reportTimeZone = 'America/Sao_Paulo';
  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[char]);
  const localDate = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  const isoBoundary = (value, end) => new Date(`${value}T${end ? '23:59:59.999' : '00:00:00.000'}-03:00`).toISOString();
  let currentCredential = null;

  function duration(seconds = 0) {
    const minutes = Math.round(seconds / 60), days = Math.floor(minutes / 1440), hours = Math.floor(minutes % 1440 / 60);
    return days ? `${days}d ${hours}h` : hours ? `${hours}h ${minutes % 60}min` : `${minutes}min`;
  }

  function dateTime(value) {
    return new Intl.DateTimeFormat('pt-BR', {
      dateStyle: 'medium',
      timeStyle: 'short',
      timeZone: reportTimeZone
    }).format(new Date(value));
  }

  function renderShell() {
    document.querySelector('.report-times-page').innerHTML = `
      <section class="page-heading"><div><p class="eyebrow">Indicadores assistenciais</p><h1>Relatório de permanência dos leitos</h1><p>Analise o tempo acumulado em cada status e exporte uma versão institucional em PDF.</p></div><button id="printReport" class="primary-button no-print" disabled><i class="fa-solid fa-file-pdf"></i> Salvar como PDF</button></section>
      <section class="panel filters no-print"><label>Período inicial<input id="reportStart" type="date"></label><label>Período final<input id="reportEnd" type="date"></label><label>Unidade<select id="reportUnit"><option value="">Todas as unidades</option></select></label><label>Status atual<select id="reportStatus"><option value="">Todos os status</option><option value="bloqueado">Bloqueado</option><option value="apto">Apto</option><option value="desocupado">Desocupado</option><option value="ocupado">Ocupado</option><option value="alta">Alta / Transferência</option></select></label><div class="filter-actions"><button id="applyFilters" class="primary-button" type="button">Gerar relatório</button><button id="clearFilters" class="secondary-button" type="button">Limpar filtros</button></div></section>
      <p class="filters-hint">O cálculo considera a duração entre cada movimentação e o próximo evento do leito dentro do período selecionado.</p>
      <section class="summary-cards time-summary"><article class="apto"><span><i class="fa-solid fa-bed"></i> Tempo apto</span><strong id="aptoTime">--</strong></article><article class="desocupado"><span><i class="fa-solid fa-door-open"></i> Tempo desocupado</span><strong id="desocupadoTime">--</strong></article><article class="ocupado"><span><i class="fa-solid fa-user-injured"></i> Tempo ocupado</span><strong id="ocupadoTime">--</strong></article><article class="alta"><span><i class="fa-solid fa-arrow-right-from-bracket"></i> Tempo em alta</span><strong id="altaTime">--</strong></article></section>
      <section class="panel report-table-panel"><div class="table-heading"><div><h2>Tempo por leito</h2><p id="reportMeta">Carregando dados...</p></div><span id="generatedAt"></span></div><div class="table-wrap"><table><thead><tr><th>Enfermaria</th><th>Leito</th><th>Status atual</th><th>Apto</th><th>Desocupado</th><th>Ocupado</th><th>Alta</th><th>Situação</th></tr></thead><tbody id="reportRows"></tbody></table></div></section>
      <section id="printDocument" aria-hidden="true"></section>`;
  }

  function bedRow(bed) {
    const d = bed.durations_seconds, status = bed.current_status || 'sem_status';
    return `<tr><td>${esc(bed.ward_name)}</td><td>${esc(bed.number)}</td><td><span class="status-badge ${status}">${labels[status]}</span></td><td>${duration(d.apto)}</td><td>${duration(d.desocupado)}</td><td>${duration(d.ocupado)}</td><td>${duration(d.alta)}</td><td>${bed.blocked ? '<span class="blocked-text">Bloqueado</span>' : 'Ativo'}</td></tr>`;
  }

  function buildPrintDocument(report, beds, totals) {
    const unit = $('reportUnit').selectedOptions[0]?.textContent || 'Todas as unidades';
    const status = $('reportStatus').value ? labels[$('reportStatus').value] : 'Todos os status';
    const generatedAt = dateTime(report.generated_at);
    const generatedBy = currentCredential
      ? `${currentCredential.full_name} (${currentCredential.username})`
      : 'Usuário autenticado';
    const pages = [];
    for (let index = 0; index < beds.length; index += rowsPerPdfPage) pages.push(beds.slice(index, index + rowsPerPdfPage));
    if (!pages.length) pages.push([]);

    $('printDocument').innerHTML = pages.map((pageBeds, pageIndex) => `
      <article class="pdf-page">
        <header class="pdf-header">
          <img src="/img/logo-hm.png" alt="Hospital de Messejana">
          <div><span>Hospital de Messejana Dr. Carlos Alberto Studart Gomes</span><h1>Relatório de permanência dos leitos</h1><p>Setup de Leitos · Indicadores assistenciais</p></div>
          <img class="pdf-government-logo" src="/img/sesa-ceara.png" alt="Governo do Estado do Ceará">
        </header>
        <section class="pdf-metadata">
          <div><span>Período</span><strong>${dateTime(report.start)} a ${dateTime(report.end)}</strong></div>
          <div><span>Unidade</span><strong>${esc(unit)}</strong></div>
          <div><span>Status atual</span><strong>${esc(status)}</strong></div>
          <div><span>Gerado por</span><strong>${esc(generatedBy)}</strong></div>
          <div><span>Data e hora da emissão</span><strong>${generatedAt} (horário de Brasília)</strong></div>
          <div><span>Leitos analisados</span><strong>${beds.length}</strong></div>
        </section>
        <section class="pdf-summary">
          <span>Apto <strong>${duration(totals.apto)}</strong></span>
          <span>Desocupado <strong>${duration(totals.desocupado)}</strong></span>
          <span>Ocupado <strong>${duration(totals.ocupado)}</strong></span>
          <span>Alta <strong>${duration(totals.alta)}</strong></span>
        </section>
        <table class="pdf-table">
          <thead><tr><th>Enfermaria</th><th>Leito</th><th>Status atual</th><th>Apto</th><th>Desocupado</th><th>Ocupado</th><th>Alta</th><th>Situação</th></tr></thead>
          <tbody>${pageBeds.length ? pageBeds.map(bedRow).join('') : '<tr><td colspan="8">Nenhum leito encontrado para os filtros selecionados.</td></tr>'}</tbody>
        </table>
        <footer class="pdf-footer"><span>Documento emitido pelo Setup de Leitos</span><strong>Página ${pageIndex + 1} de ${pages.length}</strong></footer>
      </article>`).join('');
  }

  function render(report) {
    const selectedStatus = $('reportStatus').value;
    const reportableBeds = report.beds.filter((bed) => bed.current_status || bed.blocked);
    const beds = selectedStatus === 'bloqueado'
      ? reportableBeds.filter((bed) => bed.blocked)
      : selectedStatus
        ? reportableBeds.filter((bed) => bed.current_status === selectedStatus)
        : reportableBeds;
    const totals = { alta: 0, desocupado: 0, apto: 0, ocupado: 0 };
    beds.forEach((bed) => Object.keys(totals).forEach((status) => { totals[status] += bed.durations_seconds[status] || 0; }));
    $('aptoTime').textContent = duration(totals.apto);
    $('desocupadoTime').textContent = duration(totals.desocupado);
    $('ocupadoTime').textContent = duration(totals.ocupado);
    $('altaTime').textContent = duration(totals.alta);
    const statusText = selectedStatus ? ` | Status: ${labels[selectedStatus]}` : '';
    $('reportMeta').textContent = `${beds.length} leitos com histórico analisados${statusText} | Período: ${dateTime(report.start)} a ${dateTime(report.end)}`;
    $('generatedAt').textContent = `Gerado em ${dateTime(report.generated_at)}`;
    $('reportRows').innerHTML = beds.length ? beds.map(bedRow).join('') : '<tr><td class="empty-row" colspan="8">Nenhum leito encontrado para os filtros selecionados.</td></tr>';
    buildPrintDocument(report, beds, totals);
    $('printReport').disabled = !beds.length;
  }

  async function loadReport() {
    const start = $('reportStart').value, end = $('reportEnd').value;
    if (!start || !end || end < start) {
      $('reportMeta').textContent = 'Informe um período válido para gerar o relatório.';
      $('printReport').disabled = true;
      return;
    }
    $('applyFilters').disabled = true;
    try {
      const params = new URLSearchParams({ start: isoBoundary(start, false), end: isoBoundary(end, true) });
      if ($('reportUnit').value) params.set('unit_group', $('reportUnit').value);
      const response = await fetch(`/api/reports/bed-times?${params}`, { credentials: 'same-origin' });
      if (!response.ok) throw new Error('Não foi possível gerar o relatório.');
      render(await response.json());
    } catch (error) {
      $('reportRows').innerHTML = `<tr><td class="empty-row" colspan="8">${esc(error.message)}</td></tr>`;
      $('printReport').disabled = true;
    } finally {
      $('applyFilters').disabled = false;
    }
  }

  window.addEventListener('DOMContentLoaded', async () => {
    currentCredential = await requireAuth();
    if (!currentCredential) return;
    renderShell();
    const today = new Date(), monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
    $('reportStart').value = localDate(monthStart);
    $('reportEnd').value = localDate(today);
    try {
      const response = await fetch('/api/wards', { credentials: 'same-origin' });
      if (!response.ok) throw new Error();
      const wards = await response.json();
      [...new Set(wards.map((ward) => ward.unit_group))]
        .sort((a, b) => a.localeCompare(b, 'pt-BR', { numeric: true }))
        .forEach((unit) => $('reportUnit').add(new Option(unit, unit)));
      await loadReport();
    } catch {
      $('reportRows').innerHTML = '<tr><td class="empty-row" colspan="8">Não foi possível carregar as enfermarias.</td></tr>';
    }
    $('applyFilters').onclick = loadReport;
    $('reportStatus').onchange = loadReport;
    $('clearFilters').onclick = () => {
      $('reportUnit').value = '';
      $('reportStatus').value = '';
      $('reportStart').value = localDate(monthStart);
      $('reportEnd').value = localDate(today);
      loadReport();
    };
    $('printReport').onclick = () => window.print();
  });
})();
