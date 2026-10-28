/* =========================================================================
 *  particles.js —— 棋盘内的 Canvas 粒子层
 *
 *  为什么用 Canvas 而不是 DOM：一次团战会出现 100+ 个粒子，
 *  DOM 节点会引发大量 layout/paint；Canvas 只有一个节点，稳 60fps。
 *  另外按调研结论实现了**对象池**（粒子只在初始化时创建，战斗中只复用），
 *  避免 GC 抖动。
 *
 *  对外接口：
 *    Particles.init(canvas)
 *    Particles.burst(cell, {count, color, speed, size, gravity, life})
 *    Particles.spark(cell, color)
 *    Particles.coin(x, y)            // 屏幕坐标，用于金币获得
 *    Particles.resize()
 * ========================================================================= */
(function (global) {
  'use strict';

  var JJK = global.JJK = global.JJK || {};
  var U = JJK.util;

  var canvas = null, ctx = null, dpr = 1;
  var W = 0, H = 0;
  var POOL_SIZE = 260;
  var pool = [];
  var cursor = 0;
  var running = false;
  var ambientOn = true;
  var ambientAcc = 0;

  function Particle() {
    this.active = false;
    this.x = 0; this.y = 0;
    this.vx = 0; this.vy = 0;
    this.life = 0; this.maxLife = 1;
    this.size = 2;
    this.color = '255,255,255';
    this.gravity = 0;
    this.friction = 0.94;
    this.shape = 'dot';
    this.rot = 0;
    this.vr = 0;
  }

  function init(el) {
    canvas = el;
    if (!canvas) return;
    ctx = canvas.getContext('2d', { alpha: true });
    for (var i = 0; i < POOL_SIZE; i++) pool.push(new Particle());
    resize();
    if (!running) {
      running = true;
      U.addTicker(step);
    }
  }

  function resize() {
    if (!canvas) return;
    var r = canvas.getBoundingClientRect();
    dpr = Math.min(2, global.devicePixelRatio || 1);
    W = Math.max(1, Math.round(r.width));
    H = Math.max(1, Math.round(r.height));
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function take() {
    // 环形扫描找空闲粒子；池满时覆盖最旧的，保证不 new
    for (var i = 0; i < POOL_SIZE; i++) {
      cursor = (cursor + 1) % POOL_SIZE;
      if (!pool[cursor].active) return pool[cursor];
    }
    cursor = (cursor + 1) % POOL_SIZE;
    return pool[cursor];
  }

  function spawn(x, y, opt) {
    var p = take();
    p.active = true;
    p.x = x; p.y = y;
    p.vx = opt.vx; p.vy = opt.vy;
    p.maxLife = opt.life;
    p.life = opt.life;
    p.size = opt.size;
    p.color = opt.color;
    p.gravity = opt.gravity;
    p.friction = opt.friction;
    p.shape = opt.shape || 'dot';
    p.rot = opt.rot || 0;
    p.vr = opt.vr || 0;
    return p;
  }

  function rgb(color) {
    // 接受 #rrggbb / rgb() / 'r,g,b'
    if (!color) return '255,255,255';
    if (color.charAt(0) === '#') {
      var h = color.slice(1);
      if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
      var n = parseInt(h, 16);
      return ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255);
    }
    return color;
  }

  /* ------------------------------------------------------------ 组合特效 */
  // 命中火花：12-30 个径向粒子（按调研：命中 10-30 个）
  function burst(cell, opt) {
    if (!ctx) return;
    opt = opt || {};
    var cs = opt.cellSize || 90;
    var x = (cell.x + 0.5) * cs;
    var y = (cell.y + 0.5) * cs;
    var n = opt.count || 16;
    var color = rgb(opt.color || '#ffd7a8');
    for (var i = 0; i < n; i++) {
      var ang = (Math.PI * 2 * i) / n + U.rand(-0.4, 0.4);
      var spd = U.rand(0.6, 1.0) * (opt.speed || 190);
      spawn(x, y, {
        vx: Math.cos(ang) * spd,
        vy: Math.sin(ang) * spd - U.rand(10, 50),
        life: U.rand(0.32, 0.62) * (opt.lifeScale || 1),
        size: U.rand(1.6, 3.6) * (opt.sizeScale || 1),
        color: color,
        gravity: opt.gravity === undefined ? 460 : opt.gravity,
        friction: 0.9,
        shape: Math.random() < 0.3 ? 'shard' : 'dot',
        rot: U.rand(0, 6.28),
        vr: U.rand(-8, 8)
      });
    }
    // 中心一团亮核
    spawn(x, y, {
      vx: 0, vy: 0, life: 0.14, size: 16 * (opt.sizeScale || 1),
      color: color, gravity: 0, friction: 1, shape: 'glow'
    });
  }

  function spark(cell, color, cellSize) {
    burst(cell, { count: 8, color: color, speed: 140, sizeScale: 0.7, cellSize: cellSize });
  }

  // 金币/资源获得：向上飞的金色小点（屏幕坐标）
  function coin(x, y) {
    if (!ctx) return;
    for (var i = 0; i < 7; i++) {
      spawn(x + U.rand(-8, 8), y, {
        vx: U.rand(-40, 40), vy: U.rand(-190, -120),
        life: U.rand(0.5, 0.8), size: U.rand(1.8, 3.2),
        color: '255,224,130', gravity: 320, friction: 0.97, shape: 'dot'
      });
    }
  }

  // 领域展开：从中心向外的大范围粒子
  function domain(cellSize) {
    if (!ctx) return;
    var cx = W / 2, cy = H / 2;
    for (var i = 0; i < 46; i++) {
      var ang = U.rand(0, Math.PI * 2);
      var spd = U.rand(120, 420);
      spawn(cx, cy, {
        vx: Math.cos(ang) * spd, vy: Math.sin(ang) * spd * 0.6,
        life: U.rand(0.5, 1.1), size: U.rand(1.5, 3.2),
        color: '196,164,255', gravity: -40, friction: 0.955, shape: 'dot'
      });
    }
  }

  /* ------------------------------------------------------------ 每帧 */
  function step(dt) {
    if (!ctx || !canvas) return;
    ctx.clearRect(0, 0, W, H);

    // 常驻咒力浮尘：极慢上升的小光点，让空棋盘也有"呼吸"
    if (ambientOn && W > 0) {
      ambientAcc += dt;
      while (ambientAcc > 0.26) {
        ambientAcc -= 0.26;
        spawn(U.rand(0, W), H + 6, {
          vx: U.rand(-8, 8), vy: U.rand(-26, -12),
          life: U.rand(3.2, 6.5), size: U.rand(0.9, 2.0),
          color: Math.random() < 0.5 ? '196,164,255' : '232,200,90',
          gravity: -2, friction: 1, shape: 'dot'
        });
      }
    }
    var alive = 0;
    for (var i = 0; i < POOL_SIZE; i++) {
      var p = pool[i];
      if (!p.active) continue;
      p.life -= dt;
      if (p.life <= 0) { p.active = false; continue; }
      alive++;
      p.vy += p.gravity * dt;
      p.vx *= Math.pow(p.friction, dt * 60);
      p.vy *= Math.pow(p.friction, dt * 60);
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.rot += p.vr * dt;

      var t = p.life / p.maxLife;
      var a = t > 0.7 ? 1 : Math.max(0, t / 0.7);
      ctx.globalAlpha = a;
      if (p.shape === 'glow') {
        var g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.size);
        g.addColorStop(0, 'rgba(' + p.color + ',0.95)');
        g.addColorStop(1, 'rgba(' + p.color + ',0)');
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, 6.2832);
        ctx.fill();
      } else if (p.shape === 'shard') {
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot);
        ctx.fillStyle = 'rgba(' + p.color + ',0.95)';
        ctx.fillRect(-p.size, -p.size * 0.35, p.size * 2, p.size * 0.7);
        ctx.restore();
      } else {
        ctx.fillStyle = 'rgba(' + p.color + ',0.95)';
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, 6.2832);
        ctx.fill();
      }
    }
    ctx.globalAlpha = 1;
    // 全部熄灭后跳过绘制，省一次 clear
    if (alive === 0 && canvas.dataset.clean === '1') return;
    canvas.dataset.clean = alive === 0 ? '1' : '0';
  }

  JJK.Particles = {
    init: init,
    resize: resize,
    burst: burst,
    spark: spark,
    coin: coin,
    domain: domain,
    setAmbient: function (on) { ambientOn = !!on; },
    count: function () {
      var n = 0;
      for (var i = 0; i < POOL_SIZE; i++) if (pool[i].active) n++;
      return n;
    }
  };

})(window);
