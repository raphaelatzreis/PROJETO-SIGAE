(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Estado
  // ---------------------------------------------------------------------------
  var state = window.__INITIAL_STATE__;
  var filtroNivel = 'todos';
  var ordemFila = 'prioridade';  // 'prioridade' (Min-Heap) ou 'chegada' (Rubro-Negra)
  var termoBusca = '';
  var drawerId = null;
  var ultimoSeq = state.ultimo_evento ? state.ultimo_evento.seq : 0;
  var overlayTimer = null;
  var consultSeq = null;      // atendimento cujo formulário está na tela
  var salvarTimer = null;

  var ROTAS = {
    atendimento: { titulo: 'Atendimento', sub: 'Consultório e fila de espera' },
    fila: { titulo: 'Fila de espera', sub: 'Todos os pacientes aguardando, por prioridade' },
    triagem: { titulo: 'Nova triagem', sub: 'Registrar paciente e classificar o risco' },
    equipe: { titulo: 'Equipe médica', sub: 'Médicos disponíveis, pelo menor número de atendimentos (Min-Heap)' },
    estruturas: { titulo: 'Estruturas de dados', sub: 'Tabela Hash, Árvore Rubro-Negra e os dois Min-Heaps em tempo real' },
    historico: { titulo: 'Histórico de chamadas', sub: 'Pacientes já chamados neste turno' }
  };

  function lerPref(chave, padrao) {
    try { var v = localStorage.getItem(chave); return v === null ? padrao : v; } catch (e) { return padrao; }
  }
  function salvarPref(chave, valor) {
    try { localStorage.setItem(chave, valor); } catch (e) {}
  }

  var consultorio = lerPref('sigae-consultorio', state.consultorios[0]);

  var $ = function (id) { return document.getElementById(id); };
  var el = {
    title: $('page-title'), subtitle: $('page-subtitle'), nav: $('nav'),
    clock: $('clock'), consultorio: $('consultorio-select'), tema: $('theme-toggle'),
    hero: $('hero-card'), consult: $('consult-card'), dash: $('dash'), upcoming: $('upcoming-list'),
    filtros: $('filter-group'), busca: $('search-input'), tbody: $('patients-tbody'), hist: $('history-tbody'),
    form: $('triage-form'), formErro: $('form-error'),
    drawer: $('drawer'), drawerBg: $('drawer-backdrop'), drawerContent: $('drawer-content'),
    overlay: $('call-overlay'), callKicker: $('call-kicker'), callName: $('call-name'), callPlace: $('call-place'),
    toasts: $('toasts')
  };

  // ---------------------------------------------------------------------------
  // Utilidades
  // ---------------------------------------------------------------------------
  function num(v) {
    var n = Number(v);
    return isFinite(n) ? n : 0;
  }

  // Único ponto que insere HTML montado em string. Todo dado dinâmico DEVE passar por esc()/num().
  function setHTML(alvo, html) {
    // <template> aceita qualquer trecho (inclusive <tr>/<li>) sem o parser descartar nós
    var doc = new DOMParser().parseFromString('<template>' + html + '</template>', 'text/html');
    alvo.replaceChildren(doc.querySelector('template').content);
  }

  function esc(t) {
    return String(t == null ? '' : t)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function iniciais(nome) {
    var partes = String(nome).trim().split(/\s+/);
    return ((partes[0] || '')[0] + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase();
  }

  function fmtEspera(min) {
    if (min < 60) return min + ' min';
    var h = Math.floor(min / 60), m = min % 60;
    return h + 'h' + (m ? String(m).padStart(2, '0') : '');
  }

  function pctEspera(p) {
    if (!p.alvo_min) return 100;
    return Math.min(100, Math.round((p.espera_min / p.alvo_min) * 100));
  }

  function classeEspera(p) {
    if (p.atrasado) return 'late';
    if (p.alvo_min && p.espera_min / p.alvo_min >= 0.75) return 'warn';
    return 'ok';
  }

  function badge(p, compacto) {
    return '<span class="badge lvl-' + num(p.nivel) + (compacto ? ' badge-sm' : '') + '"><span class="dot"></span>' +
      (compacto ? '' : 'Nível ' + p.nivel + ' · ') + esc(p.nivel_nome) + '</span>';
  }

  function avatar(p, tamanho) {
    return '<span class="avatar lvl-' + num(p.nivel) + (tamanho ? ' avatar-' + tamanho : '') + '" aria-hidden="true">' + esc(iniciais(p.nome)) + '</span>';
  }

  var ICON = {
    megafone: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M11 5 6 9H2v6h4l5 4V5z"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>',
    repetir: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17 2l4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14M7 22l-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/></svg>',
    olho: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>',
    x: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>',
    lixo: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>',
    check: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>',
    proximo: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'
  };

  var NIVEIS = [
    { codigo: 1, nome: 'Emergência', alvo: 'Imediato' },
    { codigo: 2, nome: 'Muito Urgente', alvo: 'Até 10 min' },
    { codigo: 3, nome: 'Urgente', alvo: 'Até 60 min' },
    { codigo: 4, nome: 'Pouco Urgente', alvo: 'Até 120 min' },
    { codigo: 5, nome: 'Não Urgente', alvo: 'Até 240 min' }
  ];

  function api(metodo, url, corpo) {
    if (!corpo && metodo !== 'GET' && metodo !== 'DELETE') corpo = {};
    return fetch(url, {
      method: metodo,
      headers: corpo
        ? { 'Content-Type': 'application/json', 'X-Requested-With': 'fetch' }
        : { 'X-Requested-With': 'fetch' },
      body: corpo ? JSON.stringify(corpo) : undefined
    }).then(function (r) {
      return r.json().then(function (dados) {
        if (!r.ok) throw new Error(dados.erro || 'Erro inesperado.');
        return dados;
      });
    });
  }

  function toast(msg, tipo) {
    var t = document.createElement('div');
    t.className = 'toast' + (tipo ? ' toast-' + tipo : '');
    t.textContent = msg;
    el.toasts.appendChild(t);
    requestAnimationFrame(function () { t.classList.add('show'); });
    setTimeout(function () {
      t.classList.remove('show');
      setTimeout(function () { t.remove(); }, 300);
    }, 3200);
  }

  // ---------------------------------------------------------------------------
  // Renderização
  // ---------------------------------------------------------------------------
  function vitais(sinais, grande) {
    sinais = sinais || {};
    var lista = [
      ['PA', sinais.pa, 'mmHg'],
      ['FC', sinais.fc, 'bpm'],
      ['Temp', sinais.temp != null ? Number(sinais.temp).toFixed(1).replace('.', ',') : null, '°C'],
      ['SpO₂', sinais.spo2, '%']
    ];
    return '<div class="vitals' + (grande ? ' vitals-lg' : '') + '">' + lista.map(function (v) {
      var alerta = (v[0] === 'SpO₂' && sinais.spo2 && sinais.spo2 < 94) ||
                   (v[0] === 'Temp' && sinais.temp && sinais.temp >= 38) ||
                   (v[0] === 'FC' && sinais.fc && (sinais.fc > 110 || sinais.fc < 50));
      return '<div class="vital' + (alerta ? ' vital-alert' : '') + '"><span>' + v[0] + '</span>' +
        '<strong class="mono">' + (v[1] != null && v[1] !== '' ? esc(v[1]) + '<small>' + v[2] + '</small>' : '—') + '</strong></div>';
    }).join('') + '</div>';
  }

  function barraEspera(p) {
    return '<div class="wait-meter ' + classeEspera(p) + '">' +
      '<div class="wm-labels"><span>Espera <strong class="mono">' + fmtEspera(p.espera_min) + '</strong></span>' +
      '<span>Alvo: ' + esc(p.tempo_alvo) + '</span></div>' +
      '<div class="wm-track"><div class="wm-fill" style="width:' + pctEspera(p) + '%"></div></div></div>';
  }

  function renderHero() {
    var p = state.proximo;
    if (!p) {
      el.hero.className = 'card hero hero-empty';
      setHTML(el.hero, '<div class="empty"><div class="empty-icon">✓</div><h3>Fila vazia</h3>' +
        '<p>Nenhum paciente aguardando. Registre uma nova triagem ou restaure os dados de teste.</p>' +
        '<div class="empty-actions"><a class="btn btn-primary" href="#/triagem">Nova triagem</a>' +
        '<button type="button" class="btn btn-ghost" data-action="resetar">Restaurar dados de teste</button></div></div>');
      return;
    }
    el.hero.className = 'card hero lvl-' + num(p.nivel);
    setHTML(el.hero, '<div class="hero-strip"></div>' +
      '<div class="hero-body">' +
        '<div class="hero-top"><span class="kicker"><span class="free-dot"></span>' + esc(consultorio) + ' livre · próximo a ser chamado</span>' + badge(p, true) + '</div>' +
        '<div class="hero-id">' + avatar(p) +
          '<div><h2 class="hero-name">' + esc(p.nome) + '</h2>' +
          '<p class="hero-sub"><strong class="mono">' + esc(p.senha) + '</strong> · ' + num(p.idade) + ' anos · ' + (p.sexo === 'F' ? 'Feminino' : 'Masculino') + ' · chegou ' + esc(p.chegada) + '</p></div>' +
        '</div>' +
        '<p class="hero-complaint">' + esc(p.queixa) + '</p>' +
        vitais(p.sinais) +
        barraEspera(p) +
        '<div class="hero-actions">' +
          '<button type="button" class="btn btn-ghost" data-action="ver" data-id="' + esc(p.id) + '">' + ICON.olho + 'Ver paciente</button>' +
          '<button type="button" class="btn btn-call" data-action="chamar">' + ICON.megafone +
            '<span>Chamar para <strong>' + esc(consultorio) + '</strong></span><kbd>N</kbd></button>' +
        '</div>' +
      '</div>');
  }

  function renderUpcoming() {
    var emAtendimento = !!atendimentoAtual();
    var seguintes = emAtendimento ? state.pacientes : state.pacientes.slice(1);
    $('upcoming-title').textContent = emAtendimento ? 'Fila de espera' : 'Próximos';
    $('upcoming-count').textContent = seguintes.length ? seguintes.length + ' aguardando' : '';
    if (!seguintes.length) {
      setHTML(el.upcoming, '<li class="muted pad">' + (emAtendimento ? 'A fila está vazia.' : 'Sem outros pacientes na sequência.') + '</li>');
      return;
    }
    setHTML(el.upcoming, seguintes.map(function (s) {
      return '<li><button type="button" class="up-item" data-action="ver" data-id="' + esc(s.id) + '">' +
        '<span class="up-pos mono">' + num(s.ordem) + '</span>' + avatar(s) +
        '<span class="up-info"><strong>' + esc(s.nome) + '</strong><span>' + esc(s.queixa) + '</span></span>' +
        '<span class="up-right"><span class="up-level"><span class="dot lvl-' + num(s.nivel) + '"></span>' + esc(s.nivel_nome) + '</span>' +
        '<span class="up-wait mono wait-' + classeEspera(s) + '">' + fmtEspera(s.espera_min) + '</span></span>' +
        '</button></li>';
    }).join(''));
  }

  function renderTabela() {
    var lista = ordemFila === 'chegada' ? state.pacientes_chegada : state.pacientes;
    if (filtroNivel !== 'todos') {
      var n = Number(filtroNivel);
      lista = lista.filter(function (p) { return p.nivel === n; });
    }
    if (termoBusca) {
      var q = termoBusca.toLowerCase();
      lista = lista.filter(function (p) {
        return (p.nome + ' ' + p.id + ' ' + p.queixa).toLowerCase().indexOf(q) !== -1;
      });
    }

    el.filtros.querySelectorAll('[data-count]').forEach(function (c) {
      var k = c.getAttribute('data-count');
      c.textContent = k === 'todos' ? state.total : (state.contagem_niveis[k] || 0);
    });

    if (!lista.length) {
      setHTML(el.tbody, '<tr><td colspan="6" class="table-empty">' +
        (state.total ? 'Nenhum paciente encontrado com os filtros atuais.' : 'A fila está vazia.') + '</td></tr>');
      return;
    }

    setHTML(el.tbody, lista.map(function (p) {
      return '<tr class="row-click" data-action="ver" data-id="' + esc(p.id) + '">' +
        '<td class="c-ord mono">' + num(ordemFila === 'chegada' ? p.chegada_ordem : p.ordem) + '</td>' +
        '<td><div class="cell-person">' + avatar(p) + '<div><div class="cell-primary">' + esc(p.nome) + '</div>' +
          '<div class="cell-secondary"><span class="mono">' + esc(p.id) + '</span> · ' + num(p.idade) + ' anos · ' + esc(p.sexo) + '</div></div></div></td>' +
        '<td><button type="button" class="badge badge-sm badge-edit lvl-' + num(p.nivel) + '" data-action="nivel" data-id="' + esc(p.id) + '"' +
          ' title="Alterar nível de urgência" aria-haspopup="menu"><span class="dot"></span>' + esc(p.nivel_nome) +
          '<svg class="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg></button></td>' +
        '<td class="c-hide-sm cell-complaint">' + esc(p.queixa) + '</td>' +
        '<td class="c-wait"><div class="cell-primary mono wait-' + classeEspera(p) + '">' + fmtEspera(p.espera_min) + '</div>' +
          '<div class="cell-secondary">alvo ' + esc(p.tempo_alvo.replace('Até ', '')) + '</div></td>' +
        '<td class="c-act">' + (p.ordem === 1 ? '<span class="badge badge-sm">Próximo</span>' : '') + '</td>' +
      '</tr>';
    }).join(''));
  }

  function renderHistorico() {
    if (!state.historico.length) {
      setHTML(el.hist, '<tr><td colspan="8" class="table-empty">Nenhuma chamada registrada ainda.</td></tr>');
      return;
    }
    setHTML(el.hist, state.historico.map(function (c, i) {
      return '<tr' + (i === 0 ? ' class="row-latest"' : '') + '>' +
        '<td class="mono">' + esc(c.horario) + '</td>' +
        '<td><div class="cell-person">' + avatar(c) + '<div><div class="cell-primary">' + esc(c.nome) + '</div>' +
          '<div class="cell-secondary mono">' + esc(c.senha) + ' · ' + esc(c.id) + (c.vezes > 1 ? ' · chamado ' + num(c.vezes) + 'x' : '') + '</div></div></div></td>' +
        '<td>' + badge(c, true) + '</td>' +
        '<td>' + esc(c.consultorio) + '</td>' +
        '<td>' + (c.medico
          ? '<div class="cell-primary">' + esc(c.medico) + '</div><div class="cell-secondary mono">#' + num(c.medico_id) + '</div>'
          : '<span class="muted">—</span>') + '</td>' +
        '<td class="c-hide-sm mono">' + fmtEspera(c.espera_min) + '</td>' +
        '<td>' + (c.status === 'encerrado'
          ? '<span class="status status-done">' + esc(c.desfecho_nome) + '</span><div class="cell-secondary">' + fmtEspera(c.duracao_min) + ' de consulta · ' + esc(c.fim) + '</div>'
          : '<span class="status status-live"><span class="live-dot"></span>Em atendimento</span>') + '</td>' +
        '<td class="c-act">' + (c.status === 'encerrado' ? '' :
          '<button type="button" class="btn btn-ghost btn-sm" data-action="rechamar" data-seq="' + num(c.seq) + '">' + ICON.repetir + '<span class="c-hide-sm">Rechamar</span></button>') + '</td>' +
      '</tr>';
    }).join(''));
  }

  function renderDrawer() {
    if (!drawerId) return;
    var p = state.pacientes.find(function (x) { return x.id === drawerId; });
    if (!p) {
      fecharDrawer();
      return;
    }
    el.drawerContent.className = 'drawer-inner lvl-' + num(p.nivel);
    setHTML(el.drawerContent, '<div class="drawer-head">' +
        '<span class="kicker">Posição ' + num(p.ordem) + ' de ' + num(state.total) + ' na fila</span>' +
        '<button type="button" class="icon-btn" data-action="fechar-drawer" aria-label="Fechar">' + ICON.x + '</button>' +
      '</div>' +
      '<div class="drawer-id">' + avatar(p, 'xl') +
        '<div><h2 id="drawer-title">' + esc(p.nome) + '</h2>' +
        '<p class="mono muted">Senha <strong>' + esc(p.senha) + '</strong> · ' + esc(p.id) + '</p></div></div>' +
      '<div class="drawer-badge">' + badge(p) + '</div>' +
      '<dl class="facts">' +
        '<div><dt>Idade</dt><dd>' + num(p.idade) + ' anos</dd></div>' +
        '<div><dt>Sexo</dt><dd>' + (p.sexo === 'F' ? 'Feminino' : 'Masculino') + '</dd></div>' +
        '<div><dt>Chegada</dt><dd class="mono">' + esc(p.chegada) + '</dd></div>' +
        '<div><dt>Tempo-alvo</dt><dd>' + esc(p.tempo_alvo) + '</dd></div>' +
      '</dl>' +
      '<h3 class="drawer-sec">Queixa principal</h3><p class="drawer-text">' + esc(p.queixa) + '</p>' +
      '<h3 class="drawer-sec">Sinais vitais</h3>' + vitais(p.sinais, true) +
      (p.observacoes ? '<h3 class="drawer-sec">Observações</h3><p class="drawer-text">' + esc(p.observacoes) + '</p>' : '') +
      '<h3 class="drawer-sec">Tempo de espera</h3>' + barraEspera(p) +
      '<div class="drawer-actions">' +
        '<button type="button" class="btn btn-ghost btn-danger" data-action="remover" data-id="' + esc(p.id) + '">' + ICON.lixo + 'Remover</button>' +

      '</div>');
  }

  function renderEquipe() {
    var px = state.proximo_medico;
    $('medico-proximo').textContent = px
      ? 'Próximo a ser designado: ' + px.nome + ' (' + px.concluidos + ' concluído(s))'
      : 'Nenhum médico disponível: as chamadas ficam bloqueadas.';
    setHTML($('medicos-tbody'), (state.medicos || []).map(function (m, i) {
      return '<tr><td class="c-ord mono">' + (m.disponivel ? num(i + 1) : '—') + '</td>' +
        '<td><div class="cell-primary">' + esc(m.nome) + '</div><div class="cell-secondary mono">#' + num(m.id) + '</div></td>' +
        '<td class="mono">' + num(m.concluidos) + '</td>' +
        '<td>' + (m.disponivel ? 'Disponível' : 'Em atendimento · ' + esc(m.paciente)) + '</td></tr>';
    }).join('') || '<tr><td colspan="4" class="table-empty">Nenhum médico cadastrado.</td></tr>');
  }

  // ---------------------------------------------------------------------------
  // Seção Estruturas: Hash, Rubro-Negra e os dois Min-Heaps (somente leitura)
  // ---------------------------------------------------------------------------
  var hashAlvo = null;   // { indice, id } da última busca na Hash
  var SVG_NS = 'http://www.w3.org/2000/svg';
  var R = 19, DX = 50, DY = 62;

  function svgEl(tag, attrs, texto) {
    var n = document.createElementNS(SVG_NS, tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (texto !== undefined) n.textContent = texto;
    return n;
  }

  // nos: [{ chave, x, y, rotulo, extra, classe, titulo }]; arestas: [[chavePai, chaveFilho]]
  function desenharArvore(alvo, nos, arestas, largura, altura) {
    alvo.replaceChildren();
    if (!nos.length) {
      var vazio = document.createElement('p');
      vazio.className = 'muted est-vazio';
      vazio.textContent = 'Estrutura vazia.';
      alvo.appendChild(vazio);
      return;
    }
    var svg = svgEl('svg', { viewBox: '0 0 ' + largura + ' ' + altura, role: 'img' });
    svg.style.minWidth = largura + 'px';  // árvores largas rolam na horizontal
    var pos = {};
    nos.forEach(function (n) { pos[n.chave] = n; });
    arestas.forEach(function (a) {
      var p = pos[a[0]], f = pos[a[1]];
      svg.appendChild(svgEl('line', { x1: p.x, y1: p.y, x2: f.x, y2: f.y, class: 'est-aresta' }));
    });
    nos.forEach(function (n) {
      var g = svgEl('g', { class: 'est-no ' + n.classe });
      g.appendChild(svgEl('title', {}, n.titulo));
      g.appendChild(svgEl('circle', { cx: n.x, cy: n.y, r: R }));
      g.appendChild(svgEl('text', { x: n.x, y: n.y + 4, 'text-anchor': 'middle', class: 'est-rotulo' }, n.rotulo));
      if (n.extra) g.appendChild(svgEl('text', { x: n.x, y: n.y + R + 13, 'text-anchor': 'middle', class: 'est-extra' }, n.extra));
      svg.appendChild(g);
    });
    alvo.appendChild(svg);
  }

  function desenharRubroNegra(raiz) {
    // x = posição no percurso em ordem (ordem de chegada); y = profundidade
    var nos = [], arestas = [], ordem = 0, prof = 0;
    (function visitar(no, d, pai) {
      if (!no) return;
      visitar(no.esq, d + 1, no);
      prof = Math.max(prof, d);
      nos.push({
        chave: no.id, x: R + 8 + ordem * DX, y: R + 8 + d * DY,
        rotulo: no.id.replace('PAC-', ''), extra: no.horario,
        classe: no.cor === 'VERMELHO' ? 'rb-vermelho' : 'rb-preto',
        titulo: no.id + ' · chegou ' + no.horario + ' · ' + (no.cor === 'VERMELHO' ? 'vermelho' : 'preto') + ' · nível ' + no.nivel
      });
      ordem++;
      if (pai) arestas.push([pai.id, no.id]);
      visitar(no.dir, d + 1, no);
    })(raiz, 0, null);
    desenharArvore($('rb-svg'), nos, arestas, Math.max(ordem * DX + 16, 200), (prof + 1) * DY + 20);
  }

  // Heap guardado em vetor: filho esquerdo de i em 2i+1, direito em 2i+2
  function desenharHeap(alvo, vetor, rotulo, extra, titulo) {
    var n = vetor.length;
    var niveis = n ? Math.floor(Math.log2(n)) + 1 : 0;
    var largura = Math.max(Math.pow(2, Math.max(niveis - 1, 0)) * DX + 16, 200);
    var nos = vetor.map(function (item, i) {
      var d = Math.floor(Math.log2(i + 1)), slot = i - (Math.pow(2, d) - 1), vagas = Math.pow(2, d);
      return {
        chave: String(i), x: (slot + 0.5) * largura / vagas, y: R + 8 + d * DY,
        rotulo: rotulo(item), extra: extra(item), classe: i === 0 ? 'heap-raiz' : 'heap-no', titulo: '[' + i + '] ' + titulo(item)
      };
    });
    var arestas = vetor.map(function (_, i) { return i ? [String(Math.floor((i - 1) / 2)), String(i)] : null; })
      .filter(Boolean);
    desenharArvore(alvo, nos, arestas, largura, niveis * DY + 20);
  }

  function renderEstruturas() {
    var e = state.estruturas, h = e.hash;

    setHTML($('est-status'), e.integra
      ? '<span class="est-ok">✓ Integridade OK</span> Hash, Rubro-Negra, Heap de pacientes e Heap de médicos com os mesmos pacientes ativos.'
      : '<span class="est-erro">✗ Inconsistência</span> As estruturas divergem. Verifique o servidor.');

    var abertos = state.atendimentos || [];
    setHTML($('vinculos'), abertos.length ? abertos.map(function (a) {
      var p = a.paciente, c = a.criterio;
      var concluidos = c ? num(c.medico_concluidos) + ' concluído(s) ao ser designado' : '';
      return '<div class="vinculo">' +
        '<div class="vinculo-lado lvl-' + num(p.nivel) + '">' +
          '<span class="vinculo-tipo">Paciente</span>' +
          '<div class="vinculo-nome">' + esc(p.nome) + '</div>' +
          '<div class="vinculo-info"><strong class="mono">' + esc(p.id) + '</strong> · ' + badge(p, true) + ' · chegou ' + esc(p.chegada) + '</div>' +
          (c ? '<p class="vinculo-criterio">' + esc(c.paciente.texto) + '</p>' : '') +
        '</div>' +
        '<div class="vinculo-meio"><span class="vinculo-seta" aria-hidden="true">⇄</span><span>' + esc(a.consultorio) + '</span>' +
          '<span class="mono">desde ' + esc(a.inicio) + '</span></div>' +
        '<div class="vinculo-lado">' +
          '<span class="vinculo-tipo">Médico</span>' +
          '<div class="vinculo-nome">' + esc(a.medico) + '</div>' +
          '<div class="vinculo-info"><strong class="mono">#' + num(a.medico_id) + '</strong>' + (concluidos ? ' · ' + concluidos : '') + '</div>' +
          (c ? '<p class="vinculo-criterio">' + esc(c.medico.texto) + '</p>' : '') +
        '</div>' +
      '</div>';
    }).join('') : '<p class="muted est-vazio">Nenhum atendimento em andamento. Chame o próximo paciente na tela de Atendimento.</p>');

    $('hash-resumo').textContent = 'Encadeamento separado · h(ID) = ID % ' + num(h.capacidade) + ' · ' + num(h.total) +
      ' paciente(s) · ' + num(h.colisoes) + ' colisão(ões) · ocupação ' + num(h.ocupacao) + '% (dobra de tamanho acima de 75%)';
    setHTML($('hash-buckets'), h.buckets.map(function (b, i) {
      var classe = 'bucket' + (b.length > 1 ? ' bucket-hot' : '') + (hashAlvo && hashAlvo.indice === i ? ' bucket-alvo' : '');
      return '<div class="' + classe + '"><span class="bucket-idx mono">' + num(i) + '</span>' +
        (b.length ? b.map(function (id) {
          var achado = hashAlvo && hashAlvo.id === id ? ' bucket-achado' : '';
          return '<span class="bucket-item mono' + achado + '">' + esc(id) + '</span>';
        }).join('') : '<span class="muted">—</span>') + '</div>';
    }).join(''));

    $('rb-resumo').textContent = num(h.total) + ' nó(s) · altura ' + num(e.arvore_altura) + ' · ' +
      (e.arvore_valida ? 'propriedades rubro-negras válidas' : 'propriedades violadas!');
    desenharRubroNegra(e.arvore);

    var hp = e.heap_pacientes;
    $('heap-resumo').textContent = hp.length
      ? 'Raiz: ' + hp[0].id + ' (nível ' + hp[0].nivel + ') · ' + hp.length + ' no vetor'
      : 'Nenhum paciente aguardando.';
    desenharHeap($('heap-svg'), hp,
      function (p) { return p.id.replace('PAC-', ''); },
      function (p) { return 'P' + p.nivel; },
      function (p) { return p.id + ' · nível ' + p.nivel; });

    var hm = e.heap_medicos;
    $('heap-med-resumo').textContent = hm.length
      ? 'Raiz: ' + hm[0].nome + ' (' + hm[0].concluidos + ' concluído(s)) · só médicos disponíveis ficam no heap'
      : 'Nenhum médico disponível: as chamadas ficam bloqueadas.';
    desenharHeap($('heap-med-svg'), hm,
      function (m) { return '#' + m.id; },
      function (m) { return m.concluidos + ' at.'; },
      function (m) { return m.nome + ' · ' + m.concluidos + ' atendimento(s) concluído(s)'; });
  }

  function renderNav() {
    $('nav-count-fila').textContent = state.total;
    $('nav-count-historico').textContent = state.historico.length;
  }

  function renderTudo() {
    renderHero();
    renderAtendimento();
    renderUpcoming();
    renderTabela();
    renderHistorico();
    renderDrawer();
    renderNav();
    renderEquipe();
    renderEstruturas();
    renderPreview();
  }

  // ---------------------------------------------------------------------------
  // Navegação por seções (hash)
  // ---------------------------------------------------------------------------
  function irPara() {
    var rota = (location.hash.replace(/^#\/?/, '') || 'atendimento');
    if (!ROTAS[rota]) rota = 'atendimento';
    document.querySelectorAll('.view').forEach(function (v) {
      v.hidden = v.getAttribute('data-view') !== rota;
    });
    el.nav.querySelectorAll('.nav-item').forEach(function (a) {
      a.classList.toggle('active', a.getAttribute('data-route') === rota);
    });
    el.title.textContent = ROTAS[rota].titulo;
    el.subtitle.textContent = ROTAS[rota].sub;
    document.title = ROTAS[rota].titulo + ' — SIGAE';
    if (rota === 'triagem') setTimeout(function () { el.form.elements.nome.focus(); }, 50);
  }
  window.addEventListener('hashchange', irPara);

  $('ordem-group').addEventListener('click', function (e) {
    var b = e.target.closest('[data-ordem]');
    if (!b) return;
    ordemFila = b.getAttribute('data-ordem');
    this.querySelectorAll('.chip').forEach(function (c) { c.classList.toggle('active', c === b); });
    renderTabela();
  });

  $('hash-busca').addEventListener('submit', function (e) {
    e.preventDefault();
    var id = $('hash-id').value.trim().toUpperCase();
    if (/^\d+$/.test(id)) id = 'PAC-' + id;
    var saida = $('hash-resultado');
    api('GET', '/api/estruturas/hash/' + encodeURIComponent(id))
      .then(function (r) {
        hashAlvo = { indice: r.indice, id: r.id };
        var onde = 'h(' + r.id.replace('PAC-', '') + ') = bucket ' + r.indice + ' · ' + r.bucket.length + ' registro(s) no bucket';
        var SITUACOES = { em_atendimento: 'em atendimento (já saiu da Hash)', historico: 'atendimento encerrado (já saiu da Hash)' };
        saida.className = 'est-resultado ' + (r.encontrado ? 'est-ok' : 'est-erro');
        saida.textContent = r.encontrado
          ? 'Encontrado: ' + r.nome + ' · ' + onde
          : 'Não está na Hash' + (r.situacao ? ': ' + SITUACOES[r.situacao] : '') + ' · ' + onde;
        saida.hidden = false;
        renderEstruturas();
      })
      .catch(function (err) {
        hashAlvo = null;
        saida.className = 'est-resultado est-erro';
        saida.textContent = err.message;
        saida.hidden = false;
        renderEstruturas();
      });
  });

  $('medico-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var nome = $('medico-nome').value.trim();
    api('POST', '/api/medicos', { nome: nome })
      .then(function (novo) {
        state = novo; renderTudo();
        $('medico-nome').value = '';
        toast('Médico ' + nome + ' cadastrado.', 'success');
      })
      .catch(function (err) { toast(err.message, 'error'); });
  });

  // ---------------------------------------------------------------------------
  // Gaveta "Ver paciente"
  // ---------------------------------------------------------------------------
  function abrirDrawer(id) {
    drawerId = id;
    renderDrawer();
    el.drawerBg.hidden = false;
    requestAnimationFrame(function () {
      el.drawer.classList.add('open');
      el.drawerBg.classList.add('show');
    });
    el.drawer.setAttribute('aria-hidden', 'false');
  }

  function fecharDrawer() {
    drawerId = null;
    el.drawer.classList.remove('open');
    el.drawerBg.classList.remove('show');
    el.drawer.setAttribute('aria-hidden', 'true');
    setTimeout(function () { if (!drawerId) el.drawerBg.hidden = true; }, 250);
  }

  // ---------------------------------------------------------------------------
  // Chamadas (som e voz só no telão; aqui apenas o aviso visual)
  // ---------------------------------------------------------------------------
  function mostrarChamada(evento) {
    var c = evento.chamada;
    el.overlay.className = 'call-overlay lvl-' + num(c.nivel);
    el.callKicker.textContent = evento.tipo === 'rechamada' ? 'Rechamando' : 'Chamando';
    el.callName.textContent = c.nome;
    el.callPlace.textContent = c.consultorio;
    el.overlay.hidden = false;
    requestAnimationFrame(function () { el.overlay.classList.add('show'); });
    clearTimeout(overlayTimer);
    overlayTimer = setTimeout(fecharChamada, 9000);
  }

  function fecharChamada() {
    clearTimeout(overlayTimer);
    el.overlay.classList.remove('show');
    setTimeout(function () { el.overlay.hidden = true; }, 250);
  }

  function processarEvento(evento, proprio) {
    if (!evento || evento.seq <= ultimoSeq) return;
    ultimoSeq = evento.seq;
    if (proprio) {
      mostrarChamada(evento);
    } else {
      toast((evento.tipo === 'rechamada' ? 'Rechamado: ' : 'Chamado: ') + evento.chamada.nome + ' → ' + evento.chamada.consultorio);
    }
  }

  function chamar(id) {
    var ativo = atendimentoAtual();
    if (ativo) {
      toast('Encerre o atendimento de ' + ativo.paciente.nome + ' antes de chamar outro paciente.', 'error');
      return;
    }
    if (!id && !state.proximo) return;
    api('POST', '/api/chamar', { consultorio: consultorio, id: id || null })
      .then(function (novo) {
        state = novo;
        renderTudo();
        processarEvento(novo.ultimo_evento, true);
      })
      .catch(function (e) { toast(e.message, 'error'); });
  }

  function rechamar(seq) {
    var corpo = seq ? { seq: Number(seq) } : {};
    api('POST', '/api/rechamar', corpo)
      .then(function (novo) {
        state = novo;
        renderTudo();
        processarEvento(novo.ultimo_evento, true);
      })
      .catch(function (e) { toast(e.message, 'error'); });
  }

  function remover(id) {
    var p = state.pacientes.find(function (x) { return x.id === id; });
    if (!p || !confirm('Remover ' + p.nome + ' da fila?')) return;
    api('DELETE', '/api/pacientes/' + encodeURIComponent(id))
      .then(function (novo) {
        state = novo;
        fecharDrawer();
        renderTudo();
        toast(p.nome + ' removido da fila.');
      })
      .catch(function (e) { toast(e.message, 'error'); });
  }

  // ---------------------------------------------------------------------------
  // Atendimento em andamento no consultório selecionado
  // ---------------------------------------------------------------------------
  function atendimentoAtual() {
    return (state.atendimentos || []).find(function (a) { return a.consultorio === consultorio; }) || null;
  }

  function fmtCronometro(seg) {
    seg = Math.max(0, Math.floor(seg));
    var h = Math.floor(seg / 3600), m = Math.floor(seg % 3600 / 60), sg = seg % 60;
    var dois = function (n) { return String(n).padStart(2, '0'); };
    return (h ? h + ':' + dois(m) : dois(m)) + ':' + dois(sg);
  }

  function atualizarCronometro() {
    var a = atendimentoAtual();
    var alvo = $('cs-timer');
    if (!a || !alvo) return;
    alvo.textContent = fmtCronometro((Date.now() - Date.parse(a.inicio_iso)) / 1000);
  }

  function renderAtendimento() {
    var a = atendimentoAtual();
    el.dash.setAttribute('data-mode', a ? 'atendimento' : 'livre');
    el.hero.hidden = !!a;
    el.consult.hidden = !a;
    if (!a) {
      consultSeq = null;
      setHTML(el.consult, '');
      return;
    }

    var p = a.paciente;
    var vezes = (state.historico.find(function (c) { return c.seq === a.seq; }) || {}).vezes || 1;
    if (consultSeq === a.seq) {
      // Mesmo atendimento: não reconstrói o formulário (o médico pode estar digitando)
      var v = $('cs-vezes');
      if (v) v.textContent = vezes > 1 ? ' · chamado ' + num(vezes) + 'x' : '';
      return;
    }
    consultSeq = a.seq;
    var pr = a.prontuario || {};
    var desfechos = state.desfechos || [];

    el.consult.className = 'card consult lvl-' + num(p.nivel);
    setHTML(el.consult, '<header class="cs-head">' + avatar(p, 'lg') +
        '<div class="cs-id"><div class="cs-title"><h2 class="cs-name">' + esc(p.nome) + '</h2>' + badge(p, true) + '</div>' +
          '<p class="cs-sub"><strong class="mono">' + esc(p.id) + '</strong> · senha <span class="mono">' + esc(p.senha) + '</span> · ' +
          num(p.idade) + ' anos · ' + (p.sexo === 'F' ? 'Feminino' : 'Masculino') +
          ' · chamado às ' + esc(a.inicio) + '<span id="cs-vezes">' + (vezes > 1 ? ' · chamado ' + num(vezes) + 'x' : '') + '</span></p>' +
          '<p class="cs-sub cs-medico">Médico: <strong>' + esc(a.medico) + '</strong> · ID <strong class="mono">#' + num(a.medico_id) + '</strong></p></div>' +
        '<div class="cs-timer"><span class="live-dot"></span><span>Em atendimento</span><strong class="mono" id="cs-timer">00:00</strong></div>' +
      '</header>' +
      '<div class="cs-body">' +
        '<section class="cs-triage">' +
          '<div class="cs-triage-top"><span class="kicker">Dados da triagem</span>' +
            '<span class="cs-wait">Aguardou <strong class="mono">' + fmtEspera(p.espera_min) + '</strong> · alvo ' + esc(p.tempo_alvo.replace('Até ', 'até ')) + '</span></div>' +
          '<p class="cs-complaint">' + esc(p.queixa) + '</p>' +
          vitais(p.sinais) +
          (p.observacoes ? '<p class="cs-obs"><strong>Observações:</strong> ' + esc(p.observacoes) + '</p>' : '') +
        '</section>' +
        '<form class="cs-form" id="consult-form" data-seq="' + a.seq + '" autocomplete="off">' +
          '<label class="field"><span>Anamnese <em>relato do paciente</em></span>' +
            '<textarea name="anamnese" rows="4" placeholder="Queixa nas palavras do paciente, início e evolução dos sintomas, antecedentes, medicações em uso, alergias…">' + esc(pr.anamnese) + '</textarea></label>' +
          '<div class="cs-grid2">' +
            '<label class="field"><span>Exame físico</span>' +
              '<textarea name="exame_fisico" rows="3" placeholder="Estado geral, ausculta, palpação, achados relevantes…">' + esc(pr.exame_fisico) + '</textarea></label>' +
            '<label class="field"><span>Conduta e prescrição</span>' +
              '<textarea name="conduta" rows="3" placeholder="Medicações, exames solicitados, orientações ao paciente…">' + esc(pr.conduta) + '</textarea></label>' +
          '</div>' +
          '<label class="field"><span>Hipótese diagnóstica</span>' +
            '<input name="hipotese" type="text" placeholder="Ex.: Crise asmática moderada (CID J45)" value="' + esc(pr.hipotese) + '"></label>' +
          '<div class="field" id="cs-desfecho"><span>Desfecho <em>obrigatório para encerrar</em></span><div class="outcomes" role="radiogroup">' +
            desfechos.map(function (d) {
              return '<label class="outcome outcome-' + d.codigo + '"><input type="radio" name="desfecho" value="' + d.codigo + '"' + (pr.desfecho === d.codigo ? ' checked' : '') + '>' +
                '<span>' + esc(d.nome) + '</span></label>';
            }).join('') +
          '</div></div>' +
        '</form>' +
      '</div>' +
      '<footer class="cs-foot">' +
        '<span class="cs-save" id="cs-save">' + (a.salvo_em ? 'Salvo às ' + esc(a.salvo_em) : 'Salvamento automático') + '</span>' +
        '<button type="button" class="btn btn-ghost" data-action="rechamar" data-seq="' + a.seq + '">' + ICON.repetir + 'Rechamar</button>' +
        '<button type="button" class="btn btn-ghost" data-action="encerrar">' + ICON.check + 'Encerrar atendimento</button>' +
        (state.total ? '<button type="button" class="btn btn-call" data-action="encerrar-proximo">Encerrar e chamar próximo' + ICON.proximo + '</button>' : '') +
      '</footer>');

    var form = $('consult-form');
    form.addEventListener('input', agendarSalvamento);
    form.addEventListener('change', agendarSalvamento);
    form.addEventListener('submit', function (e) { e.preventDefault(); });
    atualizarCronometro();
  }

  function lerProntuario() {
    var form = $('consult-form');
    if (!form) return null;
    var f = form.elements;
    return {
      anamnese: f.anamnese.value, exame_fisico: f.exame_fisico.value,
      conduta: f.conduta.value, hipotese: f.hipotese.value,
      desfecho: (form.querySelector('input[name=desfecho]:checked') || {}).value || ''
    };
  }

  function statusSalvamento(texto, tipo) {
    var alvo = $('cs-save');
    if (!alvo) return;
    alvo.textContent = texto;
    alvo.className = 'cs-save' + (tipo ? ' is-' + tipo : '');
  }

  function agendarSalvamento() {
    $('cs-desfecho').classList.remove('is-missing');
    statusSalvamento('Salvando…', 'pending');
    clearTimeout(salvarTimer);
    var seq = consultSeq;
    salvarTimer = setTimeout(function () { salvarTimer = null; salvarProntuario(seq); }, 700);
  }

  function salvarProntuario(seq) {
    if (seq !== consultSeq) return Promise.resolve();
    var prontuario = lerProntuario();
    return api('PATCH', '/api/atendimentos/' + seq, { prontuario: prontuario })
      .then(function (r) {
        var a = atendimentoAtual();
        if (a && a.seq === seq) { a.prontuario = prontuario; a.salvo_em = r.salvo_em; }
        if (seq === consultSeq) statusSalvamento('Salvo às ' + r.salvo_em, 'ok');
      })
      .catch(function (e) { if (seq === consultSeq) statusSalvamento(e.message, 'error'); });
  }

  function encerrarAtendimento(chamarProximo) {
    var a = atendimentoAtual();
    if (!a) return;
    var prontuario = lerProntuario();
    if (!prontuario.desfecho) {
      var campo = $('cs-desfecho');
      campo.classList.add('is-missing');
      campo.scrollIntoView({ behavior: 'smooth', block: 'center' });
      toast('Selecione o desfecho para encerrar o atendimento.', 'error');
      return;
    }
    clearTimeout(salvarTimer);
    salvarTimer = null;
    api('POST', '/api/atendimentos/' + a.seq + '/encerrar', { prontuario: prontuario })
      .then(function (novo) {
        state = novo;
        consultSeq = null;
        renderTudo();
        var d = state.desfechos.find(function (x) { return x.codigo === prontuario.desfecho; });
        toast('Atendimento de ' + a.paciente.nome + ' encerrado · ' + (d ? d.nome : '') + '.', 'success');
        if (chamarProximo) chamar();
      })
      .catch(function (e) { toast(e.message, 'error'); });
  }

  // ---------------------------------------------------------------------------
  // Alterar nível de urgência (menu flutuante na fila)
  // ---------------------------------------------------------------------------
  var menuNivel = null;

  function fecharMenuNivel() {
    if (!menuNivel) return;
    menuNivel.remove();
    menuNivel = null;
  }

  function abrirMenuNivel(botao, id) {
    var mesmo = menuNivel && menuNivel.getAttribute('data-id') === id;
    fecharMenuNivel();
    if (mesmo) return;
    var p = state.pacientes.find(function (x) { return x.id === id; });
    if (!p) return;

    menuNivel = document.createElement('div');
    menuNivel.className = 'level-menu';
    menuNivel.setAttribute('role', 'menu');
    menuNivel.setAttribute('data-id', id);
    setHTML(menuNivel, '<div class="level-menu-title">Reclassificar urgência</div>' + NIVEIS.map(function (n) {
      var atual = n.codigo === p.nivel;
      return '<button type="button" role="menuitemradio" aria-checked="' + atual + '" class="lm-option lvl-' + n.codigo + (atual ? ' current' : '') + '"' +
        ' data-action="definir-nivel" data-id="' + esc(id) + '" data-nivel="' + n.codigo + '">' +
        '<span class="dot"></span><span class="lm-name">' + esc(n.nome) + '</span>' +
        '<span class="lm-target">' + esc(n.alvo) + '</span></button>';
    }).join(''));
    document.body.appendChild(menuNivel);

    var r = botao.getBoundingClientRect();
    var w = menuNivel.offsetWidth, h = menuNivel.offsetHeight;
    var top = r.bottom + 6;
    if (top + h > window.innerHeight - 8) top = Math.max(8, r.top - h - 6);
    var left = Math.min(Math.max(8, r.left), window.innerWidth - w - 8);
    menuNivel.style.top = top + 'px';
    menuNivel.style.left = left + 'px';
    var foco = menuNivel.querySelector('.current') || menuNivel.querySelector('.lm-option');
    if (foco) foco.focus();
  }

  function definirNivel(id, nivel) {
    fecharMenuNivel();
    var p = state.pacientes.find(function (x) { return x.id === id; });
    if (!p || p.nivel === nivel) return;
    api('PATCH', '/api/pacientes/' + encodeURIComponent(id), { nivel: nivel })
      .then(function (novo) {
        state = novo;
        renderTudo();
        var n = NIVEIS[nivel - 1];
        toast(p.nome + ' → ' + n.nome, 'success');
      })
      .catch(function (e) { toast(e.message, 'error'); });
  }

  function resetar() {
    api('POST', '/api/resetar').then(function (novo) {
      state = novo;
      renderTudo();
      toast('Dados de teste restaurados.', 'success');
    });
  }

  // ---------------------------------------------------------------------------
  // Eventos
  // ---------------------------------------------------------------------------
  document.addEventListener('click', function (e) {
    var alvo = e.target.closest('[data-action]');
    if (menuNivel && !e.target.closest('.level-menu') && !(alvo && alvo.getAttribute('data-action') === 'nivel')) fecharMenuNivel();
    if (!alvo) return;
    var acao = alvo.getAttribute('data-action');
    var id = alvo.getAttribute('data-id');

    if (acao === 'chamar') { e.stopPropagation(); chamar(id); }
    else if (acao === 'nivel') abrirMenuNivel(alvo, id);
    else if (acao === 'encerrar') encerrarAtendimento(false);
    else if (acao === 'encerrar-proximo') encerrarAtendimento(true);
    else if (acao === 'definir-nivel') definirNivel(id, Number(alvo.getAttribute('data-nivel')));
    else if (acao === 'rechamar') rechamar(alvo.getAttribute('data-seq'));
    else if (acao === 'ver') abrirDrawer(id);
    else if (acao === 'fechar-drawer') fecharDrawer();
    else if (acao === 'remover') remover(id);
    else if (acao === 'resetar') resetar();
    else if (acao === 'filtrar') {
      filtroNivel = alvo.getAttribute('data-nivel');
      el.filtros.querySelectorAll('.chip').forEach(function (b) {
        b.classList.toggle('active', b.getAttribute('data-nivel') === filtroNivel);
      });
      renderTabela();
      location.hash = '#/fila';
    }
  });

  el.drawerBg.addEventListener('click', fecharDrawer);
  $('call-close').addEventListener('click', fecharChamada);
  $('call-repeat').addEventListener('click', function () { rechamar(); });
  el.overlay.addEventListener('click', function (e) { if (e.target === el.overlay) fecharChamada(); });

  el.filtros.addEventListener('click', function (e) {
    var b = e.target.closest('.chip');
    if (!b) return;
    filtroNivel = b.getAttribute('data-nivel');
    el.filtros.querySelectorAll('.chip').forEach(function (x) { x.classList.toggle('active', x === b); });
    renderTabela();
  });

  el.busca.addEventListener('input', function () {
    termoBusca = el.busca.value.trim();
    renderTabela();
  });

  // Consultório
  if (state.consultorios.indexOf(consultorio) === -1) consultorio = state.consultorios[0];
  el.consultorio.value = consultorio;
  el.consultorio.addEventListener('change', function () {
    // Garante que o texto digitado no prontuário aberto seja salvo antes de trocar
    if (salvarTimer) { clearTimeout(salvarTimer); salvarTimer = null; salvarProntuario(consultSeq); }
    consultorio = el.consultorio.value;
    salvarPref('sigae-consultorio', consultorio);
    renderTudo();
  });

  // Tema
  el.tema.addEventListener('click', function () {
    var novo = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', novo);
    salvarPref('sigae-theme', novo);
  });

  // Formulário de triagem — prévia ao vivo
  var ICON_ALERTA = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><path d="M12 9v4M12 17h.01"/></svg>';

  function lerTriagem() {
    var f = el.form.elements;
    var num = function (v) { return v === '' || isNaN(Number(v)) ? null : Number(v); };
    return {
      nome: f.nome.value.trim(),
      idade: num(f.idade.value),
      sexo: f.sexo.value,
      nivel: num(f.nivel.value),
      queixa: f.queixa.value.trim(),
      sinais: { pa: f.pa.value.trim(), fc: num(f.fc.value), temp: num(f.temp.value), spo2: num(f.spo2.value) }
    };
  }

  function alertasVitais(s) {
    var lista = {};
    var pa = /^(\d{2,3})\s*[\/x]\s*(\d{2,3})$/i.exec(s.pa || '');
    if (pa && (Number(pa[1]) >= 180 || Number(pa[2]) >= 110)) lista.pa = 'Pressão arterial muito elevada';
    if (pa && Number(pa[1]) < 90) lista.pa = 'Pressão arterial baixa';
    if (s.fc != null && (s.fc > 110 || s.fc < 50)) lista.fc = s.fc > 110 ? 'Taquicardia' : 'Bradicardia';
    if (s.temp != null && s.temp >= 38) lista.temp = 'Febre';
    if (s.spo2 != null && s.spo2 < 94) lista.spo2 = 'Saturação abaixo de 94%';
    return lista;
  }

  function renderPreview() {
    var box = $('triage-preview');
    if (!box) return;
    var t = lerTriagem();
    var n = t.nivel ? NIVEIS[t.nivel - 1] : null;
    var alertas = alertasVitais(t.sinais);

    el.form.querySelectorAll('[data-vital]').forEach(function (campo) {
      campo.classList.toggle('is-alert', !!alertas[campo.getAttribute('data-vital')]);
    });

    box.className = 'card preview ' + (n ? 'lvl-' + n.codigo : 'pv-none');

    var meta = [];
    if (t.idade != null) meta.push(t.idade + (t.idade === 1 ? ' ano' : ' anos'));
    if (t.sexo) meta.push(t.sexo === 'F' ? 'Feminino' : 'Masculino');

    var nivelHtml;
    if (n) {
      var frente = state.pacientes.filter(function (p) { return p.nivel <= n.codigo; }).length;
      nivelHtml =
        '<div class="pv-level"><span class="lc-num">' + n.codigo + '</span><div><strong>' + esc(n.nome) + '</strong>' +
          '<small>Tempo-alvo: ' + esc(n.alvo) + '</small></div></div>' +
        '<div class="pv-pos"><span class="pv-pos-num">' + (frente + 1) + 'º</span><span>posição prevista na fila<br>' +
          (frente === 0 ? 'Será o próximo a ser chamado' : frente + (frente === 1 ? ' paciente' : ' pacientes') + ' à frente') +
          ' · ' + (state.total + 1) + ' no total</span></div>';
    } else {
      nivelHtml = '<p class="pv-empty">Escolha o nível de risco para ver a posição prevista na fila.</p>';
    }

    var msgs = Object.keys(alertas).map(function (k) { return alertas[k]; });
    var alertaHtml = '';
    if (msgs.length) {
      alertaHtml = '<div class="pv-alert">' + ICON_ALERTA + '<span><strong>' + esc(msgs.join(' · ')) + '</strong>' +
        (n && n.codigo >= 3 ? '<br>Considere uma classificação mais urgente.' : '') + '</span></div>';
    }

    var checks = [
      ['Nome', t.nome.length >= 3], ['Idade', t.idade != null], ['Sexo', !!t.sexo],
      ['Nível de risco', !!n], ['Queixa', !!t.queixa]
    ];
    var feitos = checks.filter(function (c) { return c[1]; }).length;

    setHTML(box, '<div class="pv-band"><span class="kicker">Prévia da triagem</span>' +
        '<div class="pv-person"><span class="avatar" aria-hidden="true">' + (t.nome ? esc(iniciais(t.nome)) : '?') + '</span>' +
          '<div><div class="pv-name' + (t.nome ? '' : ' placeholder') + '">' + esc(t.nome || 'Novo paciente') + '</div>' +
          '<div class="pv-meta">' + (meta.length ? esc(meta.join(' · ')) : 'Idade e sexo não informados') + '</div></div></div>' +
      '</div>' +
      '<div class="pv-sec"><span class="kicker">Classificação</span>' + nivelHtml + '</div>' +
      (t.queixa ? '<div class="pv-sec"><span class="kicker">Queixa</span><p class="pv-complaint">' + esc(t.queixa) + '</p></div>' : '') +
      '<div class="pv-sec"><span class="kicker">Sinais vitais</span>' +
        vitais({ pa: t.sinais.pa || null, fc: t.sinais.fc, temp: t.sinais.temp, spo2: t.sinais.spo2 }) + alertaHtml + '</div>' +
      '<div class="pv-sec"><div class="pv-progress"><span>Campos obrigatórios</span><strong>' + feitos + '/' + checks.length + '</strong></div>' +
        '<div class="pv-bar"><i style="width:' + Math.round(feitos / checks.length * 100) + '%"></i></div>' +
        '<ul class="pv-checks">' + checks.map(function (c) {
          return '<li' + (c[1] ? ' class="done"' : '') + '>' + c[0] + '</li>';
        }).join('') + '</ul></div>');
  }

  el.form.addEventListener('input', renderPreview);
  el.form.addEventListener('change', renderPreview);

  el.form.addEventListener('submit', function (e) {
    e.preventDefault();
    el.formErro.textContent = '';
    var f = el.form.elements;
    if (!el.form.checkValidity()) {
      var invalido = el.form.querySelector(':invalid');
      el.formErro.textContent = 'Preencha os campos obrigatórios: nome, idade, sexo, nível e queixa.';
      if (invalido && invalido.focus) invalido.focus();
      return;
    }
    var corpo = {
      nome: f.nome.value, idade: f.idade.value, sexo: f.sexo.value, nivel: f.nivel.value,
      queixa: f.queixa.value, observacoes: f.observacoes.value,
      sinais: { pa: f.pa.value, fc: f.fc.value, temp: f.temp.value, spo2: f.spo2.value }
    };
    var botao = el.form.querySelector('[type=submit]');
    botao.disabled = true;
    api('POST', '/api/pacientes', corpo)
      .then(function (novo) {
        state = novo;
        renderTudo();
        el.form.reset();
        var p = state.pacientes.find(function (x) { return x.id === novo.criado_id; });
        toast((p ? p.nome + ' entrou na fila na posição ' + p.ordem : 'Paciente adicionado') + '.', 'success');
        location.hash = '#/fila';
      })
      .catch(function (err) { el.formErro.textContent = err.message; })
      .then(function () { botao.disabled = false; });
  });
  el.form.addEventListener('reset', function () {
    el.formErro.textContent = '';
    setTimeout(renderPreview, 0);
  });

  // Atalhos de teclado
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      if (menuNivel) fecharMenuNivel();
      else if (!el.overlay.hidden) fecharChamada();
      else if (drawerId) fecharDrawer();
      return;
    }
    var tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select' || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === 'n' || e.key === 'N') { e.preventDefault(); chamar(); }
    else if ((e.key === 'r' || e.key === 'R') && state.ultimo_chamado) { e.preventDefault(); rechamar(); }
  });

  window.addEventListener('resize', fecharMenuNivel);
  document.addEventListener('scroll', fecharMenuNivel, true);

  // Relógio
  function relogio() {
    el.clock.textContent = new Date().toLocaleTimeString('pt-BR');
    atualizarCronometro();
  }
  relogio();
  setInterval(relogio, 1000);

  // Sincronização com o servidor (outros operadores, tempos de espera)
  function sincronizar() {
    if (document.hidden) return;
    api('GET', '/api/estado').then(function (novo) {
      state = novo;
      renderTudo();
      processarEvento(novo.ultimo_evento, false);
    }).catch(function () {});
  }
  setInterval(sincronizar, 5000);

  // Inicialização
  irPara();
  renderTudo();
})();
