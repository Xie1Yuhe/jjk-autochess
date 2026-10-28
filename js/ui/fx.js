/* =========================================================================
 *  fx.js —— 战斗与界面特效（跳字 / 打击 / 领域 / 震屏 / 粒子联动）
 *
 *  Phase 7 重做要点（参考 game-feel 调研）：
 *   · 跳字走**弧线**：水平随机漂移 + 垂直抬升 + 轻微旋转，而不是直线上升
 *   · 字号按伤害量做**对数分级**（10-100 / 100-1000 / 1000+）
 *   · 命中叠加：白闪 + 抖动 + 冲击环 + 火花粒子
 *   · 暴击/黑闪额外有爆闪与顿帧（顿帧由 main.js 冻结模拟实现）
 *   · 所有 DOM 特效节点用完即删；粒子走 canvas 对象池
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};
  var U = JJK.util;
  var h = U.h;

  var boardEl = null, fxLayer = null, shakeWrap = null, cellSize = 88;
  var bannerTimer = null;
  var lastShake = 0;
  var activeShake = 0;

  function init() {
    boardEl = document.getElementById('board');
    fxLayer = document.getElementById('board-fx');
    shakeWrap = document.getElementById('shake-wrap');
    measure();
    U.addTicker(function () {
      if (boardEl) {
        var cs = parseFloat(getComputedStyle(boardEl).getPropertyValue('--cell'));
        if (cs && Math.abs(cs - cellSize) > 0.5) {
          cellSize = cs;
          if (JJK.Particles) JJK.Particles.resize();
        }
      }
    });
  }

  function measure() {
    if (!boardEl) return;
    var cs = parseFloat(getComputedStyle(boardEl).getPropertyValue('--cell'));
    if (cs) cellSize = cs;
    if (JJK.Particles) JJK.Particles.resize();
  }

  function cellCenter(x, y) {
    var cs = cellSize;
    return { px: (x + 0.5) * cs, py: (y + 0.5) * cs };
  }

  function add(el, life) {
    if (!fxLayer) return null;
    fxLayer.appendChild(el);
    if (life) setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, life);
    return el;
  }

  /* ------------------------------------------------------------ 跳字 */
  // opts: { crit, scale, life }
  function float(cell, text, cls, opts) {
    opts = opts || {};
    var c = cellCenter(cell.x, cell.y);
    var dx = U.rand(-0.22, 0.22) * cellSize;
    var rise = cellSize * U.rand(0.72, 1.15);
    var rot = U.rand(-7, 7);
    var el = h('div', {
      class: 'dmg-float ' + (cls || ''),
      text: text,
      style: {
        left: c.px + 'px',
        top: (c.py - cellSize * 0.2) + 'px',
        '--dx': dx.toFixed(1) + 'px',
        '--rise': rise.toFixed(1) + 'px',
        '--rot': rot.toFixed(1) + 'deg',
        '--dur': (0.9 + U.rand(0, 0.22)).toFixed(2) + 's'
      }
    });
    return add(el, 1250);
  }

  function skillName(cell, name, foe) {
    var c = cellCenter(cell.x, cell.y);
    var el = h('div', {
      class: 'skill-name' + (foe ? ' foe' : ''),
      text: '「' + name + '」',
      style: { left: c.px + 'px', top: (c.py - cellSize * 0.5) + 'px' }
    });
    return add(el, 1100);
  }

  /* ------------------------------------------------------------ 打击 */
  function hit(cell, opts) {
    opts = opts || {};
    var c = cellCenter(cell.x, cell.y);
    add(h('div', {
      class: 'fx-hit',
      style: { left: c.px + 'px', top: c.py + 'px', transform: 'scale(' + (opts.scale || 1) + ')' }
    }), 400);
    if (JJK.Particles) {
      JJK.Particles.burst(cell, {
        count: opts.particles || 14,
        color: opts.color || '#ffd7a8',
        cellSize: cellSize
      });
    }
  }

  // 冲击环：受击位置扩散的白环
  function shock(cell) {
    var c = cellCenter(cell.x, cell.y);
    add(h('div', { class: 'fx-shock', style: { left: c.px + 'px', top: c.py + 'px' } }), 420);
  }

  // 暴击：径向爆闪 + 粒子
  function crit(cell, color) {
    var c = cellCenter(cell.x, cell.y);
    add(h('div', { class: 'fx-crit', style: { left: c.px + 'px', top: c.py + 'px' } }), 560);
    shock(cell);
    if (JJK.Particles) {
      JJK.Particles.burst(cell, {
        count: 46, color: color || '#ff5c7a', cellSize: cellSize,
        speed: 300, sizeScale: 1.35, lifeScale: 1.3
      });
    }
  }

  // 技能落点：十字星芒
  function star(cell, color) {
    var c = cellCenter(cell.x, cell.y);
    add(h('div', {
      class: 'fx-star',
      style: { left: c.px + 'px', top: c.py + 'px', filter: 'drop-shadow(0 0 10px ' + (color || '#ffe9a8') + ')' }
    }), 460);
  }

  function blackFlash(cell) {
    var c = cellCenter(cell.x, cell.y);
    add(h('div', { class: 'fx-bf', style: { left: c.px + 'px', top: c.py + 'px' } }), 560);
    add(h('div', { class: 'fx-hit', style: { left: c.px + 'px', top: c.py + 'px' } }), 400);
    if (JJK.Particles) {
      JJK.Particles.burst(cell, {
        count: 34, color: '#ff2d55', cellSize: cellSize, speed: 340, sizeScale: 1.4
      });
    }
    shake(12);
  }

  function ring(cell, color) {
    var c = cellCenter(cell.x, cell.y);
    add(h('div', {
      class: 'fx-cast',
      style: { left: c.px + 'px', top: c.py + 'px', '--fc': color || 'rgba(196,164,255,.9)' }
    }), 700);
  }

  function slash(cell, rot, color) {
    var c = cellCenter(cell.x, cell.y);
    add(h('div', {
      class: 'fx-slash',
      style: { left: c.px + 'px', top: c.py + 'px', '--rot': (rot || -32) + 'deg', '--fc': color || '#ffd166' }
    }), 340);
  }

  function domain(team) {
    if (!fxLayer) return;
    add(h('div', { class: 'fx-domain' }), 1200);
    if (boardEl) {
      boardEl.classList.add('is-domain');
      setTimeout(function () { boardEl.classList.remove('is-domain'); }, 1600);
    }
    if (JJK.Particles) JJK.Particles.domain(cellSize);
    shake(16);
  }

  function bolt(from, to, color, dur) {
    if (!fxLayer) return;
    var a = cellCenter(from.x, from.y);
    var b = cellCenter(to.x, to.y);
    var d = Math.max(0.12, dur || 0.3);
    var el = h('div', {
      class: 'fx-bolt',
      style: {
        left: a.px + 'px',
        top: a.py + 'px',
        '--fc': color || '#8b5cf6',
        animation: 'none',
        transition: 'transform ' + d + 's linear, opacity ' + d + 's linear'
      }
    });
    add(el, d * 1000 + 200);
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        el.style.transform = 'translate(' + (b.px - a.px) + 'px,' + (b.py - a.py) + 'px)';
        el.style.opacity = '0.15';
      });
    });
  }

  /* ------------------------------------------------------------ 全屏 */
  // 震屏：按调研分级（轻 2-5px / 中 5-10px / 重 10-20px），指数衰减
  function shake(power) {
    if (!shakeWrap || U.reduceMotion) return;
    var now = performance.now();
    if (now - lastShake < 36) return;
    lastShake = now;
    power = Math.min(20, Math.max(2, power));
    activeShake = Math.max(activeShake, power);
    shakeWrap.style.setProperty('--shk', power + 'px');
    shakeWrap.style.animation = 'none';
    void shakeWrap.offsetWidth;
    shakeWrap.style.animation = 'shake-screen ' + (0.16 + power * 0.012).toFixed(2) + 's cubic-bezier(0.16,1,0.3,1)';
    setTimeout(function () {
      shakeWrap.style.animation = '';
      activeShake = 0;
    }, 260 + power * 8);
  }

  function hpFlash(blue) {
    var el = h('div', { class: 'hp-vignette' + (blue ? ' blue' : '') });
    document.body.appendChild(el);
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 700);
  }

  // 顿帧视觉替身：一层极短的白色径向脉冲
  function hitstopFlash(strength) {
    var el = h('div', { class: 'hitstop-flash' });
    if (strength) el.style.opacity = String(Math.min(1, strength));
    document.body.appendChild(el);
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 220);
  }

  function banner(main, sub, life, color) {
    var old = document.querySelector('.battle-banner');
    if (old && old.parentNode) old.parentNode.removeChild(old);
    if (bannerTimer) clearTimeout(bannerTimer);
    var el = h('div', { class: 'battle-banner' }, [
      h('div', { class: 'bb-main', text: main }),
      sub ? h('div', { class: 'bb-sub', text: sub }) : null
    ]);
    if (color) {
      el.style.setProperty('--bb', color);
      el.classList.add('has-tint');
    }
    document.body.appendChild(el);
    bannerTimer = setTimeout(function () {
      if (el.parentNode) {
        el.style.transition = 'opacity .35s ease, transform .35s ease';
        el.style.opacity = '0';
        el.style.transform = 'translateX(-50%) translateY(-10px)';
        setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 380);
      }
    }, life || 1400);
  }

  // 升星：金色扩散环 + 星字上飘 + 粒子
  function starBurst(el, star) {
    if (!el) return;
    var r = el.getBoundingClientRect();
    var cx = r.left + r.width / 2;
    var cy = r.top + r.height / 2;
    var ring = h('div', {
      style: {
        position: 'fixed',
        left: cx + 'px', top: cy + 'px',
        width: (r.width * 1.5) + 'px', height: (r.width * 1.5) + 'px',
        borderRadius: '50%',
        border: '2px solid rgba(240,195,74,.9)',
        boxShadow: '0 0 26px rgba(240,195,74,.8), inset 0 0 26px rgba(240,195,74,.5)',
        transform: 'translate(-50%,-50%) scale(.2)',
        opacity: '0.95', pointerEvents: 'none', zIndex: '90',
        animation: 'ring-expand 0.72s cubic-bezier(0.22,1,0.36,1) forwards'
      }
    });
    document.body.appendChild(ring);
    setTimeout(function () { if (ring.parentNode) ring.parentNode.removeChild(ring); }, 780);

    var st = h('div', {
      style: {
        position: 'fixed', left: cx + 'px', top: cy + 'px',
        transform: 'translate(-50%,-50%)',
        fontFamily: 'var(--font-display)', fontWeight: '900', fontSize: '26px',
        color: '#ffe9a8',
        textShadow: '0 0 20px rgba(240,195,74,.95), 0 2px 0 #7a5410',
        pointerEvents: 'none', zIndex: '91',
        animation: 'star-burst 0.9s cubic-bezier(0.22,1,0.36,1) forwards'
      },
      text: '★' + star
    });
    document.body.appendChild(st);
    setTimeout(function () { if (st.parentNode) st.parentNode.removeChild(st); }, 950);
    shake(7);
  }

  function burst(cell, color) {
    var c = cellCenter(cell.x, cell.y);
    for (var i = 0; i < 5; i++) {
      var el = h('div', {
        style: {
          position: 'absolute',
          left: c.px + 'px', top: c.py + 'px',
          width: (cellSize * 0.1) + 'px', height: (cellSize * 0.1) + 'px',
          borderRadius: '50%',
          background: color || '#e8c85a',
          boxShadow: '0 0 12px ' + (color || '#e8c85a'),
          transform: 'translate(-50%,-50%)',
          pointerEvents: 'none',
          transition: 'transform .55s cubic-bezier(0.22,1,0.36,1), opacity .55s',
          opacity: '1'
        }
      });
      add(el, 620);
      (function (el, i) {
        var ang = (Math.PI * 2 * i) / 5 + U.rand(-0.3, 0.3);
        var dist = cellSize * U.rand(0.5, 0.9);
        requestAnimationFrame(function () {
          el.style.transform = 'translate(' + (Math.cos(ang) * dist - cellSize * 0.05) + 'px,' +
            (Math.sin(ang) * dist - cellSize * 0.05) + 'px)';
          el.style.opacity = '0';
        });
      })(el, i);
    }
  }

  JJK.FX = {
    init: init,
    measure: measure,
    cellCenter: cellCenter,
    float: float,
    skillName: skillName,
    hit: hit,
    shock: shock,
    crit: crit,
    star: star,
    blackFlash: blackFlash,
    ring: ring,
    slash: slash,
    domain: domain,
    bolt: bolt,
    shake: shake,
    hpFlash: hpFlash,
    hitstopFlash: hitstopFlash,
    banner: banner,
    starBurst: starBurst,
    burst: burst,
    getCell: function () { return cellSize; }
  };

})(window);
