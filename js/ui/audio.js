/* =========================================================================
 *  audio.js —— WebAudio 程序合成音效（零外部素材，双击即有声）
 *  设计：短促的 UI 音 + 咒力感的打击音 + 极低音量的环境氛围层。
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};

  var ctx = null;
  var master = null;
  var sfxBus = null;
  var ambientBus = null;
  var noiseBuf = null;
  var enabled = true;
  var volume = 0.65;
  var ambientOn = false;
  var ambientNodes = null;
  var lastAt = {};

  try {
    var s = global.localStorage.getItem('jjk_audio');
    if (s) {
      var o = JSON.parse(s);
      if (typeof o.enabled === 'boolean') enabled = o.enabled;
      if (typeof o.volume === 'number') volume = o.volume;
    }
  } catch (e) { /* ignore */ }

  function persist() {
    try {
      global.localStorage.setItem('jjk_audio', JSON.stringify({ enabled: enabled, volume: volume }));
    } catch (e) { /* ignore */ }
  }

  function ensure() {
    if (ctx) return ctx;
    var AC = global.AudioContext || global.webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = enabled ? volume * 0.95 : 0;
    master.connect(ctx.destination);

    sfxBus = ctx.createGain();
    sfxBus.gain.value = 1;
    sfxBus.connect(master);

    ambientBus = ctx.createGain();
    ambientBus.gain.value = 0;
    ambientBus.connect(master);

    // 预生成 1 秒白噪声
    var len = Math.floor(ctx.sampleRate * 1.0);
    noiseBuf = ctx.createBuffer(1, len, ctx.sampleRate);
    var d = noiseBuf.getChannelData(0);
    for (var i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    return ctx;
  }

  /* -------------------------------------------------------------- 基础 */
  function now() { return ctx.currentTime; }

  function tone(opts) {
    if (!ctx) return;
    var t0 = now() + (opts.delay || 0);
    var osc = ctx.createOscillator();
    var g = ctx.createGain();
    osc.type = opts.type || 'sine';
    osc.frequency.setValueAtTime(opts.freq, t0);
    if (opts.to) osc.frequency.exponentialRampToValueAtTime(Math.max(20, opts.to), t0 + opts.dur);
    var peak = opts.gain === undefined ? 0.2 : opts.gain;
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(Math.max(0.0002, peak), t0 + (opts.attack || 0.006));
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + opts.dur);
    var node = osc;
    if (opts.filter) {
      var f = ctx.createBiquadFilter();
      f.type = opts.filter;
      f.frequency.value = opts.freq2 || 900;
      f.Q.value = opts.q || 1;
      node.connect(f);
      node = f;
    }
    node.connect(g);
    g.connect(opts.bus || sfxBus);
    osc.start(t0);
    osc.stop(t0 + opts.dur + 0.02);
  }

  function noise(opts) {
    if (!ctx || !noiseBuf) return;
    var t0 = now() + (opts.delay || 0);
    var src = ctx.createBufferSource();
    src.buffer = noiseBuf;
    src.loop = true;
    var f = ctx.createBiquadFilter();
    f.type = opts.filter || 'bandpass';
    f.frequency.setValueAtTime(opts.freq || 1200, t0);
    if (opts.to) f.frequency.exponentialRampToValueAtTime(Math.max(60, opts.to), t0 + opts.dur);
    f.Q.value = opts.q === undefined ? 0.9 : opts.q;
    var g = ctx.createGain();
    var peak = opts.gain === undefined ? 0.16 : opts.gain;
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(Math.max(0.0002, peak), t0 + (opts.attack || 0.004));
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + opts.dur);
    src.connect(f); f.connect(g); g.connect(opts.bus || sfxBus);
    src.start(t0);
    src.stop(t0 + opts.dur + 0.02);
  }

  /* -------------------------------------------------------------- 音色库 */
  var VOICES = {
    click: function () {
      tone({ freq: 880, to: 660, dur: 0.06, type: 'triangle', gain: 0.10 });
      noise({ freq: 3200, dur: 0.04, gain: 0.03, filter: 'highpass' });
    },
    hover: function () {
      tone({ freq: 1560, dur: 0.035, type: 'sine', gain: 0.028 });
    },
    buy: function () {
      tone({ freq: 620, to: 930, dur: 0.10, type: 'triangle', gain: 0.13 });
      tone({ freq: 1240, dur: 0.09, type: 'sine', gain: 0.07, delay: 0.05 });
    },
    sell: function () {
      tone({ freq: 520, to: 300, dur: 0.14, type: 'triangle', gain: 0.11 });
      noise({ freq: 900, to: 300, dur: 0.16, gain: 0.05 });
    },
    deny: function () {
      tone({ freq: 190, to: 130, dur: 0.16, type: 'square', gain: 0.08, filter: 'lowpass', freq2: 700 });
      tone({ freq: 150, to: 110, dur: 0.2, type: 'sawtooth', gain: 0.05, delay: 0.04, filter: 'lowpass', freq2: 500 });
    },
    equip: function () {
      tone({ freq: 900, to: 1500, dur: 0.12, type: 'sine', gain: 0.09 });
      tone({ freq: 1800, dur: 0.16, type: 'sine', gain: 0.045, delay: 0.05 });
    },
    place: function () {
      tone({ freq: 220, to: 160, dur: 0.1, type: 'sine', gain: 0.13 });
      noise({ freq: 500, dur: 0.08, gain: 0.05, filter: 'lowpass' });
    },
    upgrade: function () {
      var notes = [523.25, 659.25, 783.99, 1046.5];
      for (var i = 0; i < notes.length; i++) {
        tone({ freq: notes[i], dur: 0.42, type: 'triangle', gain: 0.10, delay: i * 0.055 });
        tone({ freq: notes[i] * 2, dur: 0.3, type: 'sine', gain: 0.04, delay: i * 0.055 });
      }
      noise({ freq: 5000, to: 2200, dur: 0.5, gain: 0.035, filter: 'highpass' });
    },
    trait: function () {
      tone({ freq: 1046.5, dur: 0.5, type: 'sine', gain: 0.075 });
      tone({ freq: 1568, dur: 0.45, type: 'sine', gain: 0.045, delay: 0.04 });
    },
    levelup: function () {
      tone({ freq: 392, to: 784, dur: 0.35, type: 'triangle', gain: 0.1 });
      tone({ freq: 1174, dur: 0.3, type: 'sine', gain: 0.05, delay: 0.12 });
    },
    hit: function () {
      noise({ freq: 2200, to: 700, dur: 0.075, gain: 0.075, filter: 'bandpass', q: 0.7 });
      tone({ freq: 150, to: 90, dur: 0.075, type: 'sine', gain: 0.06 });
    },
    bf: function () {
      tone({ freq: 88, to: 42, dur: 0.42, type: 'sine', gain: 0.26 });
      noise({ freq: 2600, to: 260, dur: 0.34, gain: 0.16, filter: 'lowpass' });
      tone({ freq: 660, to: 220, dur: 0.22, type: 'sawtooth', gain: 0.07, filter: 'lowpass', freq2: 1200 });
    },
    /* ---- 打击层：轻/重/技能/连击，带随机音高，避免重复听腻 ---- */
    hitLight: function () {
      var f = 1900 + Math.random() * 500;
      noise({ freq: f, to: 620, dur: 0.055, gain: 0.055 + Math.random() * 0.02, filter: 'bandpass', q: 1.1 });
      tone({ freq: 190 + Math.random() * 40, to: 110, dur: 0.05, type: 'sine', gain: 0.045 });
    },
    hitHeavy: function () {
      noise({ freq: 1400, to: 220, dur: 0.14, gain: 0.14, filter: 'lowpass' });
      tone({ freq: 120, to: 52, dur: 0.2, type: 'sine', gain: 0.16 });
      tone({ freq: 320, to: 90, dur: 0.12, type: 'square', gain: 0.05, filter: 'lowpass', freq2: 900 });
    },
    hitCombo: function () {
      tone({ freq: 620 + Math.random() * 260, dur: 0.045, type: 'triangle', gain: 0.05 });
      noise({ freq: 3400, dur: 0.03, gain: 0.035, filter: 'highpass' });
    },
    slash: function () {
      noise({ freq: 4200, to: 900, dur: 0.13, gain: 0.06, filter: 'bandpass', q: 0.9 });
    },
    block: function () {
      noise({ freq: 700, dur: 0.09, gain: 0.07, filter: 'bandpass', q: 2.4 });
      tone({ freq: 260, dur: 0.08, type: 'square', gain: 0.05, filter: 'lowpass', freq2: 800 });
    },
    /* ---- 黑闪：闷雷 + 电流嘶鸣，比普通命中重得多 ---- */
    bfCharge: function () {
      tone({ freq: 60, to: 150, dur: 0.16, type: 'sawtooth', gain: 0.1, filter: 'lowpass', freq2: 400 });
    },
    bfThunder: function () {
      noise({ freq: 5200, to: 300, dur: 0.42, gain: 0.22, filter: 'lowpass' });
      tone({ freq: 70, to: 34, dur: 0.5, type: 'sine', gain: 0.24 });
      tone({ freq: 1240, to: 380, dur: 0.16, type: 'sawtooth', gain: 0.075, filter: 'lowpass', freq2: 1800 });
      noise({ freq: 2600, to: 900, dur: 0.1, gain: 0.1, filter: 'bandpass', q: 3 });
    },
    /* ---- 必杀：切入风声 + 低频轰鸣 + 金属泛音 ---- */
    ult: function () {
      noise({ freq: 380, to: 4200, dur: 0.34, gain: 0.1, filter: 'bandpass', q: 1.2 });
      tone({ freq: 58, to: 34, dur: 0.9, type: 'sine', gain: 0.22 });
      tone({ freq: 156, to: 78, dur: 0.7, type: 'triangle', gain: 0.1 });
      tone({ freq: 1244, dur: 0.5, type: 'sine', gain: 0.05, delay: 0.08 });
      tone({ freq: 1866, dur: 0.42, type: 'sine', gain: 0.032, delay: 0.14 });
      noise({ freq: 6000, to: 1800, dur: 0.5, gain: 0.05, filter: 'highpass' });
    },
    cast: function () {
      noise({ freq: 700, to: 3200, dur: 0.3, gain: 0.075, filter: 'bandpass', q: 2.2 });
      tone({ freq: 300, to: 700, dur: 0.26, type: 'triangle', gain: 0.06 });
    },
    heal: function () {
      tone({ freq: 700, to: 1100, dur: 0.28, type: 'sine', gain: 0.055 });
    },
    death: function () {
      tone({ freq: 260, to: 70, dur: 0.34, type: 'triangle', gain: 0.1 });
      noise({ freq: 900, to: 160, dur: 0.3, gain: 0.06, filter: 'lowpass' });
    },
    victory: function () {
      var notes = [523.25, 659.25, 783.99, 1046.5, 1318.5];
      for (var i = 0; i < notes.length; i++) {
        tone({ freq: notes[i], dur: 0.7, type: 'triangle', gain: 0.09, delay: i * 0.08 });
      }
      tone({ freq: 130.8, dur: 1.2, type: 'sine', gain: 0.09 });
    },
    defeat: function () {
      var notes = [440, 392, 349.23, 261.63];
      for (var i = 0; i < notes.length; i++) {
        tone({ freq: notes[i], dur: 0.75, type: 'triangle', gain: 0.085, delay: i * 0.14 });
      }
      tone({ freq: 110, dur: 1.4, type: 'sine', gain: 0.08 });
    },
    /* 领域展开：三段式
       ① 蓄势（0~0.9s）低频上扫 + 反向噪声，营造「结界正在成形」
       ② 撞击（0.7s）次低音下坠 + 铜锣泛音列 + 金属嘶鸣，领域「落地」
       ③ 余韵（1s~4s）两个微失谐的低音制造拍频，持续的不安感 */
    domain: function () {
      // ① 蓄势
      tone({ freq: 26, to: 104, dur: 0.92, type: 'sine', gain: 0.30, attack: 0.18 });
      noise({ freq: 160, to: 2800, dur: 0.88, gain: 0.115, filter: 'bandpass', q: 0.85, attack: 0.3 });
      tone({ freq: 392, to: 196, dur: 0.85, type: 'triangle', gain: 0.045, attack: 0.3 });

      // ② 撞击
      tone({ freq: 128, to: 28, dur: 1.6, type: 'sine', gain: 0.44, delay: 0.70 });
      tone({ freq: 213.7, dur: 2.8, type: 'triangle', gain: 0.105, delay: 0.70 });
      tone({ freq: 320.6, dur: 2.4, type: 'sine', gain: 0.052, delay: 0.72 });
      tone({ freq: 427.4, dur: 2.0, type: 'sine', gain: 0.034, delay: 0.75 });
      tone({ freq: 640.9, dur: 1.5, type: 'sine', gain: 0.018, delay: 0.78 });
      noise({ freq: 5400, to: 260, dur: 1.5, gain: 0.20, filter: 'lowpass', delay: 0.70 });
      noise({ freq: 1800, dur: 0.09, gain: 0.16, filter: 'bandpass', q: 3.0, delay: 0.70 });

      // ③ 余韵（拍频）
      tone({ freq: 55, dur: 3.4, type: 'sine', gain: 0.135, delay: 0.80, attack: 0.5 });
      tone({ freq: 58.4, dur: 3.4, type: 'sine', gain: 0.095, delay: 0.80, attack: 0.5 });
      noise({ freq: 820, to: 220, dur: 3.2, gain: 0.045, filter: 'lowpass', delay: 0.85, attack: 0.6 });
    },
    /* 领域持续期间的底噪（由 startHum/stopHum 控制） */
    domainEnd: function () {
      tone({ freq: 92, to: 26, dur: 1.3, type: 'sine', gain: 0.26 });
      noise({ freq: 1600, to: 120, dur: 1.2, gain: 0.14, filter: 'lowpass' });
      tone({ freq: 174.6, to: 87, dur: 0.9, type: 'triangle', gain: 0.06, delay: 0.05 });
    },
    overtime: function () {
      tone({ freq: 120, to: 60, dur: 0.8, type: 'sawtooth', gain: 0.1, filter: 'lowpass', freq2: 400 });
    },
    start: function () {
      tone({ freq: 174, to: 348, dur: 0.45, type: 'triangle', gain: 0.14 });
      noise({ freq: 400, to: 1800, dur: 0.4, gain: 0.07, filter: 'bandpass' });
      tone({ freq: 87, dur: 0.6, type: 'sine', gain: 0.12 });
    }
  };

  var THROTTLE = { hit: 0.035, hover: 0.05, click: 0.02 };

  /* -------------------------------------------------------------- 领域持续音 */
  var humNodes = null;

  function startHum() {
    if (humNodes || !ensure()) return;
    var t = now();
    humNodes = [];
    // 四个低音叠加，其中一对轻微失谐制造缓慢拍频（结界在「呼吸」）
    [41.2, 55.0, 82.4, 123.5, 124.9].forEach(function (f, i) {
      var o = ctx.createOscillator();
      o.type = i % 2 ? 'sine' : 'triangle';
      o.frequency.value = f;
      var g = ctx.createGain();
      g.gain.setValueAtTime(0.0001, t);
      g.gain.linearRampToValueAtTime(0.030 / (1 + i * 0.55), t + 1.1);
      o.connect(g);
      g.connect(sfxBus);
      o.start(t);
      humNodes.push({ o: o, g: g });
    });
  }

  function stopHum() {
    if (!humNodes) return;
    var t = now();
    humNodes.forEach(function (h) {
      try {
        h.g.gain.cancelScheduledValues(t);
        h.g.gain.setValueAtTime(h.g.gain.value || 0.01, t);
        h.g.gain.linearRampToValueAtTime(0.0001, t + 1.1);
        h.o.stop(t + 1.25);
      } catch (e) { /* ignore */ }
    });
    humNodes = null;
  }

  /* -------------------------------------------------------------- 语音 */
  // 不引用任何动画原声（版权原因），改用浏览器内置语音合成朗读领域名。
  var VOICE_KEY = 'jjk_voiceline';

  function voiceOn() {
    try { return localStorage.getItem(VOICE_KEY) !== '0'; } catch (e) { return true; }
  }
  function setVoice(v) {
    try { localStorage.setItem(VOICE_KEY, v ? '1' : '0'); } catch (e) {}
    if (!v && typeof speechSynthesis !== 'undefined') {
      try { speechSynthesis.cancel(); } catch (e) {}
    }
  }

  function speak(text, opts) {
    if (!enabled || !voiceOn()) return;
    if (typeof speechSynthesis === 'undefined') return;
    if (!text) return;
    opts = opts || {};
    try {
      var u = new SpeechSynthesisUtterance(text);
      u.lang = opts.lang || 'ja-JP';
      u.rate = opts.rate || 0.80;
      u.pitch = opts.pitch || 0.5;
      u.volume = Math.min(1, (opts.vol === undefined ? 0.95 : opts.vol));
      var vs = speechSynthesis.getVoices() || [];
      var want = (opts.lang || 'ja').slice(0, 2).toLowerCase();
      var pick = vs.filter(function (v) { return (v.lang || '').toLowerCase().indexOf(want) === 0; })[0]
              || vs.filter(function (v) { return (v.lang || '').toLowerCase().indexOf(want) >= 0; })[0];
      if (pick) u.voice = pick;
      speechSynthesis.cancel();
      speechSynthesis.speak(u);
    } catch (e) { /* ignore */ }
  }

  // 领域展开播报：优先日文「領域展開」，没有日文语音包就退回中文
  function announceDomain(name) {
    if (!enabled || !voiceOn()) return;
    // 必杀名本身就带「领域展开」，先剥掉，否则会念两遍
    var clean = String(name || '')
      .replace(/领域展开|領域展開|[「」【】]/g, '')
      .trim();
    var vs = [];
    try { vs = (typeof speechSynthesis !== 'undefined' && speechSynthesis.getVoices()) || []; } catch (e) {}
    var hasJa = vs.some(function (v) { return /^ja/i.test(v.lang || ''); });
    var hasZh = vs.some(function (v) { return /^zh/i.test(v.lang || ''); });
    if (hasJa) {
      speak('領域展開 ' + clean, { lang: 'ja-JP', rate: 1.05, pitch: 0.44 });
    } else if (hasZh) {
      speak('领域展开 ' + clean, { lang: 'zh-CN', rate: 1.15, pitch: 0.6 });
    } else {
      // 语音包还没加载完（部分浏览器异步返回）：直接读中文，交给默认音色
      speak('领域展开 ' + clean, { rate: 1.15, pitch: 0.6 });
    }
  }

  function play(name) {
    if (!enabled) return;
    if (!ensure()) return;
    if (ctx.state === 'suspended') { try { ctx.resume(); } catch (e) { /* ignore */ } }
    var t = performance.now() / 1000;
    var thr = THROTTLE[name];
    if (thr && lastAt[name] && t - lastAt[name] < thr) return;
    lastAt[name] = t;
    var v = VOICES[name];
    if (!v) return;
    try { v(); } catch (e) { /* ignore */ }
  }

  /* -------------------------------------------------------------- 氛围 */
  function startAmbient() {
    if (ambientOn || !ensure()) return;
    ambientOn = true;
    var t = now();
    var nodes = {};

    // 低频咒力底噪
    var droneGain = ctx.createGain();
    droneGain.gain.setValueAtTime(0.0001, t);
    droneGain.gain.linearRampToValueAtTime(0.13, t + 3.5);
    var lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 420;
    lp.Q.value = 0.7;
    droneGain.connect(lp);
    lp.connect(ambientBus);

    nodes.oscs = [];
    [55, 82.41, 110].forEach(function (f, i) {
      var o = ctx.createOscillator();
      o.type = i === 2 ? 'triangle' : 'sine';
      o.frequency.value = f;
      var g = ctx.createGain();
      g.gain.value = i === 0 ? 0.5 : (i === 1 ? 0.22 : 0.10);
      o.connect(g); g.connect(droneGain);
      o.start(t);
      nodes.oscs.push(o);
    });

    // 缓慢滤波器摆动
    var lfo = ctx.createOscillator();
    var lfoGain = ctx.createGain();
    lfo.frequency.value = 0.045;
    lfoGain.gain.value = 160;
    lfo.connect(lfoGain); lfoGain.connect(lp.frequency);
    lfo.start(t);

    // 气声风
    var windSrc = ctx.createBufferSource();
    windSrc.buffer = noiseBuf;
    windSrc.loop = true;
    var bp = ctx.createBiquadFilter();
    bp.type = 'bandpass';
    bp.frequency.value = 620;
    bp.Q.value = 0.8;
    var windGain = ctx.createGain();
    windGain.gain.value = 0.016;
    windSrc.connect(bp); bp.connect(windGain); windGain.connect(ambientBus);
    windSrc.start(t);

    nodes.extra = [lfo, windSrc];
    ambientNodes = nodes;
    ambientBus.gain.cancelScheduledValues(t);
    ambientBus.gain.setValueAtTime(ambientBus.gain.value, t);
    ambientBus.gain.linearRampToValueAtTime(1, t + 2.5);
  }

  function stopAmbient() {
    if (!ambientOn || !ctx) return;
    ambientOn = false;
    var t = now();
    ambientBus.gain.cancelScheduledValues(t);
    ambientBus.gain.setValueAtTime(ambientBus.gain.value, t);
    ambientBus.gain.linearRampToValueAtTime(0.0001, t + 1.0);
    var nodes = ambientNodes;
    ambientNodes = null;
    setTimeout(function () {
      if (!nodes) return;
      try {
        nodes.oscs.forEach(function (o) { o.stop(); });
        nodes.extra.forEach(function (o) { o.stop(); });
      } catch (e) { /* ignore */ }
    }, 1400);
  }

  /* --------------------------------------------------------------- BGM */
  var BGM_SRC = {
    prep: 'assets/audio/bgm_prep.m4a',
    battle: 'assets/audio/bgm_battle.m4a'
  };
  var bgmEl = null;
  var bgmName = '';

  function bgmVol() {
    return enabled ? Math.min(1, volume * 0.45) : 0;
  }

  function startBgm(name) {
    var src = BGM_SRC[name];
    if (!src) return;
    if (bgmName === name && bgmEl && !bgmEl.paused) {
      bgmEl.volume = bgmVol();
      return;
    }
    bgmName = name;
    if (!bgmEl) {
      bgmEl = new Audio();
      bgmEl.loop = true;
      bgmEl.preload = 'auto';
    }
    if (bgmEl.getAttribute('src') !== src) {
      bgmEl.setAttribute('src', src);
    }
    bgmEl.volume = bgmVol();
    var pr = bgmEl.play();
    if (pr && pr.catch) pr.catch(function () { /* 需用户手势，忽略 */ });
  }

  function stopBgm() {
    bgmName = '';
    if (bgmEl) {
      try { bgmEl.pause(); } catch (e) { /* ignore */ }
    }
  }

  function syncBgmVolume() {
    if (bgmEl) bgmEl.volume = bgmVol();
    if (!enabled && bgmEl) { try { bgmEl.pause(); } catch (e) {} }
    else if (enabled && bgmName && bgmEl && bgmEl.paused) {
      var pr = bgmEl.play();
      if (pr && pr.catch) pr.catch(function () {});
    }
  }

  /* -------------------------------------------------------------- 控制 */
  function setEnabled(v) {
    enabled = !!v;
    if (master && ctx) master.gain.setTargetAtTime(enabled ? volume * 0.95 : 0, now(), 0.05);
    syncBgmVolume();
    if (enabled && ambientOn === false && JJK.App && JJK.App.inGame) startAmbient();
    if (!enabled) stopAmbient();
    persist();
  }

  function setVolume(v) {
    volume = Math.max(0, Math.min(1, v));
    syncBgmVolume();
    if (master && ctx) master.gain.setTargetAtTime(enabled ? volume * 0.95 : 0, now(), 0.05);
    persist();
  }

  function unlock() {
    ensure();
    if (ctx && ctx.state === 'suspended') ctx.resume();
  }

  JJK.Audio = {
    play: play,
    unlock: unlock,
    startAmbient: startAmbient,
    stopAmbient: stopAmbient,
    startHum: startHum,
    stopHum: stopHum,
    speak: speak,
    announceDomain: announceDomain,
    isVoiceOn: voiceOn,
    setVoice: setVoice,
    setEnabled: setEnabled,
    setVolume: setVolume,
    startBgm: startBgm,
    stopBgm: stopBgm,
    isEnabled: function () { return enabled; },
    getVolume: function () { return volume; }
  };

  // 首次交互自动解锁音频
  ['pointerdown', 'keydown'].forEach(function (ev) {
    global.addEventListener(ev, function once() {
      unlock();
      if (enabled) startAmbient();
      global.removeEventListener(ev, once);
    }, { once: true });
  });

})(window);
