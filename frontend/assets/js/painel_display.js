let estadoLeitos = new Map();
let filaChamadas = [];
let leitoAtualExibindo = null;
let linhaDeBaseCriada = false;
let ultimoTempoAtualizacao = null;
let chamadaTimeout = null;

const synth = window.speechSynthesis;
const DURACAO_CHAMADA_MS = 12000;
const mainPanel = document.getElementById('mainPanel');
const displayUnidade = document.getElementById('displayUnidade');
const displayLeito = document.getElementById('displayLeito');
const displayStatus = document.getElementById('displayStatus');
const updateTime = document.getElementById('updateTime');
const filaAptos = document.getElementById('filaAptos');
const filaAltaDesocupados = document.getElementById('filaAltaDesocupados');
const horaAtual = document.getElementById('horaAtual');

const statusVisiveis = new Set(['apto', 'desocupado', 'alta']);
const statusLabels = {
    apto: 'Disponível',
    desocupado: 'Desocupado',
    alta: 'Em Alta',
};
const statusIcons = {
    apto: 'fa-circle-check',
    desocupado: 'fa-door-open',
    alta: 'fa-arrow-right-from-bracket',
};
let vozFeminina = null;

function chaveLeito(leito) {
    if (leito.bed_id !== undefined && leito.bed_id !== null) return `id:${leito.bed_id}`;
    return `${leito.unidade || ''}|${leito.quarto || ''}|${leito.leito || ''}`;
}

function normalizarStatus(value) {
    const status = String(value || '').trim().toUpperCase();
    if (['APTO', 'LIVRE', 'AVAILABLE'].includes(status)) return 'apto';
    if (status === 'DESOCUPADO') return 'desocupado';
    if (status === 'ALTA') return 'alta';
    return null;
}

function nomeUnidade(value) {
    const unidade = String(value || 'Sem unidade').trim();
    if (/^[A-J]$/i.test(unidade)) return `Unidade ${unidade.toUpperCase()}`;
    if (/^unidade\s+/i.test(unidade)) {
        const sufixo = unidade.replace(/^unidade\s+/i, '').toUpperCase();
        return `Unidade ${sufixo}`;
    }
    return unidade;
}

function normalizarLeito(item) {
    const bloqueado = item?.blocked === true || item?.blocked === 1 || String(item?.blocked).toLowerCase() === 'true';
    if (!item || bloqueado) return null;
    const status = normalizarStatus(
        item.status || item.event_type || item.last_event_type || (item.apto_since ? 'APTO' : '')
    );
    if (!statusVisiveis.has(status)) return null;
    return {
        bed_id: item.bed_id,
        unidade: nomeUnidade(item.unit_group || item.unidade),
        quarto: item.ward_name || item.quarto || '',
        leito: item.bed_number || item.leito || 'Sem leito',
        status,
        status_since: item.status_since || item.last_event_at || item.apto_since || new Date().toISOString(),
    };
}

function obterHora(data) {
    if (!data) return '--:--';
    return new Date(data).toLocaleTimeString('pt-BR', {
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'America/Sao_Paulo',
    });
}

function selecionarVozFeminina() {
    if (!synth) return null;
    const vozes = synth.getVoices();
    const femininos = [
        'female', 'feminina', 'woman', 'mulher', 'maria', 'francisca',
        'helena', 'luciana', 'fernanda', 'camila', 'beatriz', 'vitória',
    ];
    const portugues = vozes.filter((voz) => /^pt(-|_)?br$/i.test(voz.lang || ''));
    vozFeminina = portugues.find((voz) =>
        femininos.some((nome) => voz.name.toLowerCase().includes(nome))
    ) || portugues[0] || vozes.find((voz) => /^pt/i.test(voz.lang || '')) || null;
    return vozFeminina;
}

if (synth) {
    selecionarVozFeminina();
    synth.addEventListener?.('voiceschanged', selecionarVozFeminina);
}

function anunciarMensagem(texto) {
    if (!synth) return;
    try {
        synth.cancel();
        const utterance = new SpeechSynthesisUtterance(texto);
        utterance.lang = 'pt-BR';
        utterance.rate = 0.92;
        utterance.pitch = 1.2;
        utterance.volume = 1;
        const voz = vozFeminina || selecionarVozFeminina();
        if (voz) utterance.voice = voz;
        synth.speak(utterance);
    } catch (erro) {
        console.error('Erro ao anunciar:', erro);
    }
}

function anunciarLeito(leito) {
    const inicio = leito.status === 'alta'
        ? 'Leito em alta'
        : `Leito ${statusLabels[leito.status].toLowerCase()}`;
    anunciarMensagem(`${inicio}. ${leito.unidade}, leito ${leito.leito}.`);
}

function ordenarLeitos(leitos) {
    return leitos.sort((a, b) => {
        const unidade = a.unidade.localeCompare(b.unidade, 'pt-BR', { numeric: true });
        if (unidade !== 0) return unidade;
        return String(a.leito).localeCompare(String(b.leito), 'pt-BR', { numeric: true });
    });
}

function consolidarLeitos(leitosBrutos) {
    const unicos = new Map();
    leitosBrutos.forEach((item) => {
        const leito = normalizarLeito(item);
        if (!leito) return;
        const chave = chaveLeito(leito);
        const anterior = unicos.get(chave);
        if (!anterior || new Date(leito.status_since) >= new Date(anterior.status_since)) {
            unicos.set(chave, leito);
        }
    });
    return unicos;
}

function enfileirarMudanca(leito) {
    const chave = chaveLeito(leito);
    // Se o mesmo leito mudar duas vezes antes da chamada, anuncia somente o
    // estado mais recente.
    filaChamadas = filaChamadas.filter((item) => chaveLeito(item) !== chave);
    filaChamadas.push(leito);
}

function processarLeitos(leitosBrutos) {
    if (!Array.isArray(leitosBrutos)) throw new Error('Resposta do painel não contém uma lista válida.');
    const novoEstado = consolidarLeitos(leitosBrutos);

    if (!linhaDeBaseCriada) {
        estadoLeitos = novoEstado;
        linhaDeBaseCriada = true;
        atualizarFilaLateral();
        return;
    }

    novoEstado.forEach((leito, chave) => {
        const anterior = estadoLeitos.get(chave);
        if (!anterior || anterior.status !== leito.status) enfileirarMudanca(leito);
    });

    if (leitoAtualExibindo) {
        const atual = novoEstado.get(chaveLeito(leitoAtualExibindo));
        if (!atual || atual.status !== leitoAtualExibindo.status) {
            if (chamadaTimeout) clearTimeout(chamadaTimeout);
            chamadaTimeout = null;
            leitoAtualExibindo = null;
            exibirVazio();
        }
    }

    estadoLeitos = novoEstado;
    atualizarFilaLateral();
    if (!leitoAtualExibindo && filaChamadas.length) exibirProximoLeito();
}

function aplicarStatusVisual(status) {
    mainPanel.classList.remove('status-apto', 'status-desocupado', 'status-alta', 'status-aguardando');
    mainPanel.classList.add(status ? `status-${status}` : 'status-aguardando');
}

function exibirProximoLeito() {
    if (!filaChamadas.length) return;
    if (chamadaTimeout) clearTimeout(chamadaTimeout);
    leitoAtualExibindo = filaChamadas.shift();
    aplicarStatusVisual(leitoAtualExibindo.status);
    mainPanel.classList.remove('novo');
    void mainPanel.offsetWidth;
    mainPanel.classList.add('novo');
    displayUnidade.textContent = leitoAtualExibindo.unidade;
    displayLeito.textContent = `Leito ${String(leitoAtualExibindo.leito).toUpperCase()}`;
    displayStatus.textContent = statusLabels[leitoAtualExibindo.status];
    anunciarLeito(leitoAtualExibindo);
    chamadaTimeout = setTimeout(() => {
        chamadaTimeout = null;
        leitoAtualExibindo = null;
        if (filaChamadas.length) exibirProximoLeito();
        else exibirVazio();
    }, DURACAO_CHAMADA_MS);
}

function exibirVazio() {
    aplicarStatusVisual(null);
    displayUnidade.textContent = '--';
    displayLeito.textContent = '--';
    displayStatus.textContent = 'Aguardando...';
}

function atualizarFilaLateral() {
    const leitos = ordenarLeitos([...estadoLeitos.values()]);
    renderizarColuna(filaAptos, leitos.filter((leito) => leito.status === 'apto'), 'Nenhum leito apto');
    renderizarColuna(
        filaAltaDesocupados,
        leitos.filter((leito) => leito.status === 'alta' || leito.status === 'desocupado'),
        'Nenhum leito em alta ou desocupado',
    );
}

function renderizarColuna(container, leitos, mensagemVazia) {
    pararRotacaoCircular(container);
    if (!leitos.length) {
        container.innerHTML = `<div class="fila-empty">${mensagemVazia}</div>`;
        return;
    }
    iniciarRotacaoCircular(container, leitos);
}

function cartaoLeito(leito) {
    return `
        <article class="fila-item status-${leito.status}" data-bed-key="${escAttr(chaveLeito(leito))}">
            <div class="fila-item-unidade">${escHtml(leito.unidade)}</div>
            <div class="fila-item-leito">Leito ${escHtml(leito.leito)}</div>
            <div class="fila-item-rodape">
                <span class="fila-item-status"><i class="fa-solid ${statusIcons[leito.status]}"></i>${statusLabels[leito.status]}</span>
                <span class="fila-item-detalhe">${obterHora(leito.status_since)}</span>
            </div>
        </article>`;
}

function escHtml(value) {
    return String(value).replace(/[&<>"']/g, (char) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;',
    })[char]);
}

function escAttr(value) {
    return escHtml(value);
}

const rotationStates = new Map();
const ROTATION_INTERVAL_MS = 5000;
const ROTATION_TRANSITION_MS = 260;

function pararRotacaoCircular(container) {
    const state = rotationStates.get(container);
    if (state?.interval) clearInterval(state.interval);
    if (state?.transition) clearTimeout(state.transition);
    rotationStates.delete(container);
    container.classList.remove('changing-group');
}

function iniciarRotacaoCircular(container, leitos) {
    const tamanhoGrupo = Math.max(1, Math.floor((container.clientHeight + 10) / 126));
    const grupos = [];
    for (let index = 0; index < leitos.length; index += tamanhoGrupo) {
        grupos.push(leitos.slice(index, index + tamanhoGrupo));
    }
    const state = { index: 0, interval: null, transition: null };
    const mostrarGrupo = () => {
        container.innerHTML = grupos[state.index].map(cartaoLeito).join('');
    };
    mostrarGrupo();
    if (grupos.length === 1) return;

    state.interval = setInterval(() => {
        container.classList.add('changing-group');
        state.transition = setTimeout(() => {
            state.index = (state.index + 1) % grupos.length;
            mostrarGrupo();
            requestAnimationFrame(() => container.classList.remove('changing-group'));
            state.transition = null;
        }, ROTATION_TRANSITION_MS);
    }, ROTATION_INTERVAL_MS);
    rotationStates.set(container, state);
}

function atualizarHora() {
    const agora = new Date();
    horaAtual.textContent = agora.toLocaleTimeString('pt-BR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZone: 'America/Sao_Paulo',
    });
    if (!ultimoTempoAtualizacao) return;
    const diff = Math.floor((agora - ultimoTempoAtualizacao) / 1000);
    updateTime.textContent = diff < 10 ? 'Agora' : diff < 60 ? `${diff}s atrás` : `${Math.floor(diff / 60)}m atrás`;
}

const STATUS_URL = '/api/painel/status';
const WS_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/painel`;
let statusRequestPromise = null;
let ws = null;
let reconnectAttempt = 0;
let reconnectTimer = null;

async function buscarStatusAtual() {
    if (statusRequestPromise) return statusRequestPromise;
    statusRequestPromise = (async () => {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 8000);
        try {
            const response = await fetch(STATUS_URL, { cache: 'no-store', signal: controller.signal });
            if (!response.ok) throw new Error(`Painel indisponível (HTTP ${response.status}).`);
            const dados = await response.json();
            processarLeitos(dados);
            ultimoTempoAtualizacao = new Date();
            atualizarHora();
        } catch (erro) {
            console.error('Erro ao buscar status:', erro);
            updateTime.textContent = 'Sem conexão';
        } finally {
            clearTimeout(timeout);
            statusRequestPromise = null;
        }
    })();
    return statusRequestPromise;
}

function conectarWebSocket() {
    ws = new WebSocket(WS_URL);
    ws.onopen = () => {
        reconnectAttempt = 0;
        buscarStatusAtual();
    };
    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'leitos_disponiveis' && Array.isArray(msg.leitos)) {
                processarLeitos(msg.leitos);
                ultimoTempoAtualizacao = new Date();
                atualizarHora();
            }
        } catch (erro) {
            console.error('Erro ao processar WebSocket:', erro);
        }
    };
    ws.onclose = agendarReconexao;
    ws.onerror = () => ws.close();
}

function agendarReconexao() {
    if (reconnectTimer) return;
    const delay = Math.min(1000 * 2 ** reconnectAttempt, 30000);
    reconnectAttempt += 1;
    updateTime.textContent = 'Reconectando...';
    reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        conectarWebSocket();
    }, delay);
}

function iniciar() {
    exibirVazio();
    conectarWebSocket();
    setInterval(atualizarHora, 1000);
    setInterval(buscarStatusAtual, 30000);
}

window.addEventListener('load', iniciar);
