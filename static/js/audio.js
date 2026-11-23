/*
 * SIGAE — Áudio de chamada
 * Som de aviso sintetizado (Web Audio API, sem arquivos externos) + voz pt-BR (Web Speech API).
 */
(function () {
  var ctx = null;
  var vozes = [];

  function getCtx() {
    if (!ctx) {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
    }
    return ctx;
  }

  function carregarVozes() {
    if (!('speechSynthesis' in window)) return;
    vozes = window.speechSynthesis.getVoices() || [];
  }

  if ('speechSynthesis' in window) {
    carregarVozes();
    window.speechSynthesis.onvoiceschanged = carregarVozes;
  }

  function escolherVoz() {
    if (!vozes.length) carregarVozes();
    var pt = vozes.filter(function (v) { return /^pt(-|_)?BR/i.test(v.lang); });
    if (!pt.length) pt = vozes.filter(function (v) { return /^pt/i.test(v.lang); });
    if (!pt.length) return null;
    // Preferência por vozes mais naturais quando disponíveis
    var preferidas = [/natural/i, /google/i, /francisca/i, /thalita/i, /antonio/i, /luciana/i, /maria/i];
    for (var i = 0; i < preferidas.length; i++) {
      var achou = pt.find(function (v) { return preferidas[i].test(v.name); });
      if (achou) return achou;
    }
    return pt[0];
  }

  // Uma nota com timbre de sino: fundamental + harmônico, ataque rápido e decaimento longo
  function nota(ac, freq, inicio, duracao, volume) {
    var saida = ac.createGain();
    saida.gain.setValueAtTime(0.0001, inicio);
    saida.gain.exponentialRampToValueAtTime(volume, inicio + 0.015);
    saida.gain.exponentialRampToValueAtTime(0.0001, inicio + duracao);
    saida.connect(ac.destination);

    [[1, 'sine', 1], [2, 'sine', 0.25], [3, 'triangle', 0.08]].forEach(function (parcial) {
      var osc = ac.createOscillator();
      var g = ac.createGain();
      osc.type = parcial[1];
      osc.frequency.setValueAtTime(freq * parcial[0], inicio);
      g.gain.value = parcial[2];
      osc.connect(g);
      g.connect(saida);
      osc.start(inicio);
      osc.stop(inicio + duracao + 0.05);
    });
  }

  /** Toca o "plim-plim-plom" de chamada. Resolve quando o som termina. */
  function tocarAviso(volume) {
    var ac = getCtx();
    if (!ac) return Promise.resolve();
    var vol = typeof volume === 'number' ? volume : 0.35;
    return (ac.state === 'suspended' ? ac.resume() : Promise.resolve()).then(function () {
      var t = ac.currentTime + 0.05;
      nota(ac, 784.0, t, 1.1, vol);        // Sol5
      nota(ac, 659.25, t + 0.42, 1.1, vol); // Mi5
      nota(ac, 523.25, t + 0.84, 1.6, vol); // Dó5
      return new Promise(function (resolve) { setTimeout(resolve, 2100); });
    });
  }

  /** Fala um texto em português. Resolve quando termina (ou após um tempo limite). */
  function falar(texto, opcoes) {
    opcoes = opcoes || {};
    if (!('speechSynthesis' in window)) return Promise.resolve();
    return new Promise(function (resolve) {
      var synth = window.speechSynthesis;
      var u = new SpeechSynthesisUtterance(texto);
      var voz = escolherVoz();
      if (voz) u.voice = voz;
      u.lang = voz ? voz.lang : 'pt-BR';
      u.rate = opcoes.rate || 0.92;
      u.pitch = 1;
      u.volume = 1;
      var terminou = false;
      function fim() { if (!terminou) { terminou = true; resolve(); } }
      u.onend = fim;
      u.onerror = fim;
      setTimeout(fim, 12000);
      synth.speak(u);
    });
  }

  function textoChamada(chamada) {
    return 'Paciente ' + chamada.nome + ', por favor, dirija-se ao ' + chamada.consultorio + '.';
  }

  var fila = Promise.resolve();

  /**
   * Anuncia uma chamada: som + voz (repetida `repeticoes` vezes).
   * Chamadas consecutivas entram numa fila para não se sobreporem.
   */
  function anunciar(chamada, opcoes) {
    opcoes = opcoes || {};
    var som = opcoes.som !== false;
    var voz = opcoes.voz !== false;
    var repeticoes = opcoes.repeticoes || 1;

    fila = fila.then(function () {
      var passo = som ? tocarAviso(opcoes.volume) : Promise.resolve();
      if (!voz) return passo;
      var texto = textoChamada(chamada);
      for (var i = 0; i < repeticoes; i++) {
        passo = passo.then(function (idx) {
          return function () {
            return (idx > 0 ? new Promise(function (r) { setTimeout(r, 600); }) : Promise.resolve())
              .then(function () { return falar(texto, { rate: opcoes.rate }); });
          };
        }(i));
      }
      return passo;
    }).catch(function () {});
    return fila;
  }

  /** Precisa ser chamado dentro de um clique para liberar o áudio no navegador. */
  function desbloquear() {
    var ac = getCtx();
    if (ac && ac.state === 'suspended') ac.resume();
    if ('speechSynthesis' in window) {
      // "Aquece" o motor de voz com uma fala vazia
      var u = new SpeechSynthesisUtterance(' ');
      u.volume = 0;
      window.speechSynthesis.speak(u);
    }
  }

  window.SigaeAudio = {
    tocarAviso: tocarAviso,
    falar: falar,
    anunciar: anunciar,
    desbloquear: desbloquear,
    textoChamada: textoChamada,
    suportaVoz: 'speechSynthesis' in window
  };
})();
