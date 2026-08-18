(() => {
    const labels = {
        ocupado: 'Ocupado',
        apto: 'Apto',
        desocupado: 'Desocupado',
        alta: 'Alta / transferência',
        sem_status: 'Sem status',
    };
    const statuses = ['ocupado', 'apto', 'desocupado', 'alta', 'sem_status'];
    const $ = (id) => document.getElementById(id);
    const percent = (value, total) => total ? Math.round(value / total * 100) : 0;
    const hours = (seconds) => new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(seconds / 3600);

    function dateRange(days) {
        const end = new Date();
        const start = new Date(end);
        start.setDate(start.getDate() - days);
        return { start: start.toISOString(), end: end.toISOString() };
    }

    function renderBars(target, values, total, valueFormatter) {
        target.innerHTML = statuses
            .filter((status) => status !== 'sem_status' || Object.hasOwn(values, status))
            .map((status) => {
                const value = values[status] || 0;
                const share = percent(value, total);
                return `<div class="bar-row">
                    <span class="bar-label">${labels[status]}</span>
                    <div class="bar-track" title="${share}%"><div class="bar-fill ${status}" style="width:${share}%"></div></div>
                    <span class="bar-value">${valueFormatter(value, share)}</span>
                </div>`;
            }).join('');
    }

    function renderUnits(beds) {
        const units = new Map();
        beds.filter((bed) => !bed.blocked).forEach((bed) => {
            const unit = units.get(bed.unit_group) || { total: 0, monitored: 0, ocupado: 0, apto: 0 };
            unit.total += 1;
            if (bed.last_event_type) unit.monitored += 1;
            if (bed.last_event_type === 'ocupado') unit.ocupado += 1;
            if (bed.last_event_type === 'apto') unit.apto += 1;
            units.set(bed.unit_group, unit);
        });
        $('unitIndicatorRows').innerHTML = [...units.entries()]
            .sort(([a], [b]) => a.localeCompare(b, 'pt-BR'))
            .map(([name, unit]) => {
                const hasData = unit.monitored > 0;
                const occupancy = hasData ? percent(unit.ocupado, unit.total) : null;
                return `<tr>
                    <td data-label="Unidade"><strong>${name}</strong></td>
                    <td data-label="Leitos ativos">${unit.total}</td>
                    <td data-label="Monitorados">${unit.monitored}</td>
                    <td data-label="Ocupados">${unit.ocupado}</td>
                    <td data-label="Aptos">${unit.apto}</td>
                    <td data-label="Ocupação"><span class="occupancy-pill ${hasData && occupancy >= 85 ? 'high' : ''}">${hasData ? `${occupancy}%` : 'Sem dados'}</span></td>
                </tr>`;
            }).join('') || '<tr><td colspan="6">Nenhuma unidade encontrada.</td></tr>';
    }

    function render(beds, report) {
        const activeBeds = beds.filter((bed) => !bed.blocked);
        const monitored = activeBeds.filter((bed) => bed.last_event_type);
        const current = Object.fromEntries(statuses.map((status) => [status, 0]));
        activeBeds.forEach((bed) => { current[bed.last_event_type || 'sem_status'] += 1; });

        const occupied = current.ocupado;
        const occupancy = monitored.length ? percent(occupied, activeBeds.length) : null;
        $('currentOccupancy').textContent = occupancy === null ? 'Sem dados' : `${occupancy}%`;
        $('occupiedDetail').textContent = `${occupied} de ${activeBeds.length} leitos ativos`;
        $('availableNow').textContent = current.apto;
        $('monitoringCoverage').textContent = `${percent(monitored.length, activeBeds.length)}%`;
        $('monitoredDetail').textContent = `${monitored.length} de ${activeBeds.length} leitos ativos`;
        $('activeBedsTotal').textContent = `${activeBeds.length} leitos`;

        const durationTotal = Object.values(report.totals_seconds).reduce((sum, value) => sum + value, 0);
        $('trackedTime').textContent = `${hours(durationTotal)} h`;
        renderBars($('currentStatusBars'), current, activeBeds.length, (value) => String(value));
        renderBars($('durationBars'), report.totals_seconds, durationTotal, (_, share) => `${share}%`);
        renderUnits(beds);
    }

    async function loadIndicators() {
        const button = $('refreshIndicators');
        const message = $('indicatorMessage');
        button.disabled = true;
        message.className = 'indicator-message';
        message.textContent = 'Atualizando indicadores…';
        try {
            if (!await requireAuth()) return;
            const range = dateRange(Number($('indicatorPeriod').value));
            const params = new URLSearchParams(range);
            const [bedsResponse, reportResponse] = await Promise.all([
                fetch('/api/beds', { credentials: 'same-origin' }),
                fetch(`/api/reports/bed-times?${params}`, { credentials: 'same-origin' }),
            ]);
            if (!bedsResponse.ok || !reportResponse.ok) throw new Error('Não foi possível carregar os indicadores.');
            render(await bedsResponse.json(), await reportResponse.json());
            message.textContent = `Atualizado em ${new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Sao_Paulo' }).format(new Date())}.`;
        } catch (error) {
            message.className = 'indicator-message error';
            message.textContent = error.message;
        } finally {
            button.disabled = false;
        }
    }

    window.addEventListener('DOMContentLoaded', () => {
        $('indicatorPeriod').addEventListener('change', loadIndicators);
        $('refreshIndicators').addEventListener('click', loadIndicators);
        loadIndicators();
    });
})();
