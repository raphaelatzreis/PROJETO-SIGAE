(function () {
  'use strict';

  var state = window.__INITIAL_STATE__;
  var ultimoSeq = state.ultimo_evento ? state.ultimo_evento.seq : 0;
  var audioLiberado = false;
  var chaveAtual = null;
  var chaveHistorico = null;

  var $ = function (id) { return document.getElementById(id); };
  var elAtual = $('tv-current');
  var elHist = $('tv-history');
  var elUnlock = $('tv-unlock');

  function esc(t) {
    return String(t == null ? '' : t)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // A chamada em destaque é a do último evento (inclui rechamadas de pacientes mais antigos)
  function chamadaAtual() {
    return state.ultimo_evento ? state.ultimo_evento.chamada : state.ultimo_chamado;
  }

  function renderAtual(destacar) {
    var c = chamadaAtual();
    // Só redesenha quando a chamada exibida muda, para não interromper a animação
    var chave = c ? c.seq + ':' + c.vezes : 'vazio';
    if (chave === chaveAtual && !destacar) return;
    chaveAtual = chave;

    if (!c) {
      elAtual.className = 'tv-current tv-idle';
      elAtual.innerHTML = '<div class="tv-senha">— —</div>' +
        '<div class="tv-info"><span class="tv-nome">Aguardando chamadas</span></div>';
      return;
    }

    elAtual.className = 'tv-current';
    elAtual.innerHTML =
      '<div class="tv-senha">' + esc(c.senha) + '</div>' +
      '<div class="tv-info">' +
        '<span class="tv-nome">' + esc(c.nome) + '</span>' +
        '<span class="tv-local">' + esc(c.consultorio) + '</span>' +
      '</div>';

    if (destacar) {
      void elAtual.offsetWidth; // reinicia a animação mesmo numa rechamada
      elAtual.classList.add('flash');
    }
  }

  function renderHistorico() {
    var atual = chamadaAtual();
    var lista = state.historico.filter(function (c) { return !atual || c.seq !== atual.seq; });
    // Só redesenha quando muda, preservando a rolagem
    var chave = lista.map(function (c) { return c.seq + ':' + c.vezes; }).join(',');
    if (chave === chaveHistorico) return;
    chaveHistorico = chave;

    if (!lista.length) {
      elHist.innerHTML = '<li class="tv-empty">Nenhuma chamada anterior</li>';
      return;
    }
    elHist.innerHTML = lista.map(function (c) {
      return '<li>' +
        '<span class="th-name">' + esc(c.nome) + '</span>' +
        '<span class="th-place">' + esc(c.consultorio) + '</span>' +
        '<span class="th-time">' + esc(c.horario) + '</span></li>';
    }).join('');
  }

  function render(destacar) {
    renderAtual(destacar);
    renderHistorico();
  }

  function aplicar(novo) {
    state = novo;
    var ev = novo.ultimo_evento;
    var temNovo = ev && ev.seq > ultimoSeq;
    if (temNovo) ultimoSeq = ev.seq;
    render(temNovo);
    if (temNovo && audioLiberado) {
      window.SigaeAudio.anunciar(ev.chamada, { repeticoes: 2, volume: 0.5 });
    }
  }

  function sincronizar() {
    fetch('/api/estado')
      .then(function (r) { return r.json(); })
      .then(aplicar)
      .catch(function () {});
  }

  // Tela cheia (Fullscreen API com fallback WebKit). Exige gesto do usuário.
  function entrarTelaCheia() {
    if (document.fullscreenElement || document.webkitFullscreenElement) return;
    var raiz = document.documentElement;
    var req = raiz.requestFullscreen || raiz.webkitRequestFullscreen;
    if (!req) return;
    try {
      var p = req.call(raiz);
      if (p && p.catch) p.catch(function () {});
    } catch (e) {}
  }

  // Saiu da tela cheia (ESC) ou abriu a URL direto: qualquer clique reativa
  document.addEventListener('click', entrarTelaCheia);

  $('btn-unlock').addEventListener('click', function () {
    entrarTelaCheia();
    audioLiberado = true;
    window.SigaeAudio.desbloquear();
    window.SigaeAudio.tocarAviso(0.3);
    elUnlock.classList.add('hide');
    setTimeout(function () { elUnlock.remove(); }, 400);
  });

  // Modo quiosque (?kiosk): para TVs com navegador iniciado com autoplay liberado
  // (ex.: chrome --kiosk --autoplay-policy=no-user-gesture-required)
  if (/[?&]kiosk\b/.test(location.search)) {
    audioLiberado = true;
    elUnlock.remove();
  }

  function relogio() {
    $('tv-time').textContent = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }

  relogio();
  setInterval(relogio, 1000);
  render(false);
  setInterval(sincronizar, 2000);
})();
