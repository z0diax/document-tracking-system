/*!
 * Winter Theme: Falling Snowflakes (snowflake shapes + ground) and Animated Snowman
 * Overlays: canvas and ground are pointer-events: none; snowman allows hover only
 * Z-index kept below navbar/offcanvas, above content
 */
(function() {
  // Theme toggle via localStorage:
  //   window.WinterTheme.disable() -> sets localStorage 'winterTheme' = 'off' and reloads
  //   window.WinterTheme.enable()  -> removes flag and reloads
  const THEME_DISABLED = (function() {
    try { return localStorage.getItem('winterTheme') === 'off'; } catch (_) { return false; }
  })();
  const FALLBACK_THEME = 'classic';

  const GLOBAL_THEME = (function() {
    try {
      const theme = document.body && document.body.dataset ? document.body.dataset.seasonTheme : null;
      return theme || FALLBACK_THEME;
    } catch (_) {
      return FALLBACK_THEME;
    }
  })();

  const THEMES = {
    CLASSIC: 'classic',
    WINTER: 'winter',
    HALLO: 'hallochristmas'
  };

  const ACTIVE_THEME = (typeof GLOBAL_THEME === 'string' && GLOBAL_THEME.trim().length > 0)
    ? GLOBAL_THEME.toLowerCase()
    : FALLBACK_THEME;

  const IS_HALLOCHRISTMAS = ACTIVE_THEME === THEMES.HALLO;
  const IS_WINTER_ONLY = ACTIVE_THEME === THEMES.WINTER;
  const IS_SEASONAL = IS_HALLOCHRISTMAS || IS_WINTER_ONLY;
  const ALLOW_EMBERS = IS_HALLOCHRISTMAS;

  try {
    window.WinterTheme = {
      disable() { try { localStorage.setItem('winterTheme', 'off'); } catch (_) {} location.reload(); },
      enable()  { try { localStorage.removeItem('winterTheme'); } catch (_) {} location.reload(); }
    };
  } catch (_) {}

  // Run after DOM is parsed
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  function init() {
    if (THEME_DISABLED || !IS_SEASONAL) {
      teardownSeasonalDecor();
      return;
    }
    addSnowCanvas();
    if (IS_HALLOCHRISTMAS) {
      addHolidayGarland();
      addFloatingSprites();
      removeElementById('snow-ground');
      removeElementById('snowman-container');
      removeElementById('snowman-greeting');
    } else {
      removeElementById('holiday-garland');
      removeElementById('holiday-sprites');
    }
    if (IS_WINTER_ONLY) {
      addSnowGround();
      addSnowman();
    }
    // addSnowman(); // Disabled: remove animated snowman (keep falling snowflakes)
  }

  function teardownSeasonalDecor() {
    ['snow-canvas', 'holiday-garland', 'holiday-sprites', 'snow-ground', 'snowman-container', 'snowman-greeting'].forEach(removeElementById);
    try { localStorage.removeItem('snowflakes'); } catch (_) {}
  }

  function removeElementById(id) {
    const el = document.getElementById(id);
    if (!el) return;
    if (typeof el.remove === 'function') {
      el.remove();
    } else if (el.parentNode) {
      el.parentNode.removeChild(el);
    }
  }

  function addSnowCanvas() {
    const nav = document.querySelector('nav.navbar');
    if (!nav) return;

    let canvas = document.getElementById('snow-canvas');
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.id = 'snow-canvas';
      canvas.setAttribute('aria-hidden', 'true');
      // insert as first child so other nav contents paint above it
      nav.insertBefore(canvas, nav.firstChild);
    } else if (canvas.parentElement !== nav) {
      try { canvas.remove(); } catch (_) {}
      canvas = document.createElement('canvas');
      canvas.id = 'snow-canvas';
      canvas.setAttribute('aria-hidden', 'true');
      nav.insertBefore(canvas, nav.firstChild);
    }


    const ctx = canvas.getContext('2d');

    // Keep DPR to 1 for small, lightweight navbar animation
    const dpr = 1;

    function resize() {
      const rect = nav.getBoundingClientRect();
      const w = Math.max(1, Math.floor(rect.width));
      const h = Math.max(1, Math.floor(rect.height));
      canvas.style.width = w + 'px';
      canvas.style.height = h + 'px';
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    window.addEventListener('resize', resize);

    const W = () => canvas.width / dpr;
    const H = () => canvas.height / dpr;

    // Snowflake engine sized to navbar area
    const navArea = () => Math.max(1, W() * H());
    const FLAKE_COUNT_BASE = 60;
    let FLAKE_COUNT = Math.max(20, Math.min(60, Math.floor((navArea() / (1280 * 60)) * FLAKE_COUNT_BASE)));
    const PREFERS_REDUCED_MOTION = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (PREFERS_REDUCED_MOTION) {
      FLAKE_COUNT = Math.min(40, FLAKE_COUNT);
    }

    const flakes = [];
    const TWO_PI = Math.PI * 2;

    function rand(min, max) {
      return Math.random() * (max - min) + min;
    }

    // Mixed snowfall: small round snow dots + larger unicode winterflakes (❅/❆)
    class SnowDot {
      constructor() { this.reset(true); }
      reset(initial) {
        this.x = rand(0, W());
        this.y = initial ? rand(-H(), H()) : rand(-20, -5);
        this.r = rand(0.6, 1.8);
        this.speedY = rand(10, 26) / 60;
        this.speedX = rand(-5, 5) / 60;
        if (PREFERS_REDUCED_MOTION) {
          this.speedY *= 0.6;
          this.speedX *= 0.6;
        }
        this.alpha = rand(0.35, 0.9);
        this.windAmplitude = rand(4, 12);
        this.windPhase = rand(0, TWO_PI);
      }
      update() {
        // gentle random drift
        this.windPhase += rand(-0.01, 0.01);
        this.x += this.speedX + Math.sin(this.windPhase) * (this.windAmplitude / 120);
        this.y += this.speedY;
        if (this.y - this.r > H() || this.x + this.r < -20 || this.x - this.r > W() + 20) {
          this.reset(false);
        }
      }
      draw(ctx) {
        ctx.save();
        ctx.globalAlpha = this.alpha;
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.r + 0.6, 0, TWO_PI);
        ctx.fill();
        ctx.restore();
      }
    }

    class Winterflake {
      constructor() { this.reset(true); }
      reset(initial) {
        // If initial, start at random Y in nav; else respawn just above navbar
        this.x = rand(0, W());
        this.y = initial ? rand(-H(), H()) : rand(-20, -5);

        // size controls font size of the glyph
        this.r = rand(1.2, 2.4);
        this.speedY = rand(12, 28) / 60;   // px/frame vertical
        this.speedX = rand(-7, 7) / 60;    // px/frame horizontal drift
        if (PREFERS_REDUCED_MOTION) {
          this.speedY *= 0.6;
          this.speedX *= 0.6;
        }
        this.alpha = rand(0.45, 0.95);
        this.windAmplitude = rand(6, 16);
        this.windPhase = rand(0, TWO_PI);
        this.spin = rand(-0.02, 0.02);
        this.rot = rand(0, TWO_PI);
        const glyphs = ['❅', '❆'];
        this.glyph = glyphs[Math.floor(rand(0, glyphs.length))];
      }

      update() {
        this.windPhase += this.spin;
        // Horizontal sway with wind
        this.x += this.speedX + Math.sin(this.windPhase) * (this.windAmplitude / 120);
        this.y += this.speedY;

        if (this.y - this.r > H() || this.x + this.r < -20 || this.x - this.r > W() + 20) {
          this.reset(false);
        }
      }

      draw(ctx) {
        // Render a unicode winterflake glyph "❅/❆"
        ctx.save();
        ctx.translate(this.x, this.y);
        ctx.rotate(this.rot);

        const alpha = this.alpha.toFixed(3);
        ctx.fillStyle = 'rgba(255,255,255,' + alpha + ')';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        // Size scaled to flake radius; tuned for navbar height (~60px)
        const size = Math.max(10, Math.min(24, this.r * 8 + 6));
        ctx.font = size + 'px "Segoe UI Symbol","Apple Color Emoji","Noto Color Emoji","Twemoji Mozilla",sans-serif';

        // Optional subtle glow (kept minimal for perf)
        ctx.shadowColor = 'rgba(255,255,255,' + alpha + ')';
        ctx.shadowBlur = 2;

        ctx.fillText(this.glyph, 0, 0);

        ctx.restore();
      }
    }

    class EmberParticle {
      constructor() { this.reset(true); }
      reset(initial) {
        this.x = rand(0, W());
        this.y = initial ? rand(-H(), H()) : rand(-18, -8);
        this.r = rand(0.9, 1.6);
        this.speedY = rand(18, 34) / 60;
        this.speedX = rand(-12, 12) / 60;
        if (PREFERS_REDUCED_MOTION) {
          this.speedY *= 0.6;
          this.speedX *= 0.6;
        }
        this.alpha = rand(0.45, 0.92);
        this.windPhase = rand(0, TWO_PI);
        this.windAmplitude = rand(4, 10);
        this.flickerSpeed = rand(0.04, 0.08);
      }
      update() {
        this.windPhase += this.flickerSpeed;
        this.x += this.speedX * 0.4 + Math.sin(this.windPhase) * (this.windAmplitude / 140);
        this.y += this.speedY * 0.9;
        if (this.y - this.r > H() || this.x + this.r < -24 || this.x - this.r > W() + 24) {
          this.reset(false);
        }
      }
      draw(ctx) {
        ctx.save();
        const flicker = 0.75 + Math.sin(this.windPhase * 2.4) * 0.25;
        const innerAlpha = Math.min(1, this.alpha * 1.35);
        const outerAlpha = this.alpha * 0.4;
        const gradient = ctx.createRadialGradient(this.x, this.y, 0, this.x, this.y, this.r * 4.2);
        gradient.addColorStop(0, `rgba(255, ${Math.floor(90 + flicker * 120)}, ${Math.floor(40 + flicker * 60)}, ${innerAlpha})`);
        gradient.addColorStop(1, `rgba(255, ${Math.floor(120 + flicker * 90)}, 0, ${outerAlpha})`);
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.r * 3.6, 0, TWO_PI);
        ctx.fill();
        ctx.restore();
      }
    }

    // Function to save the state of snowflakes (navbar snowfall)
    function saveState() {
        try {
          const snowflakesState = flakes.map((flake) => {
            const entry = {
              x: flake.x,
              y: flake.y,
              speedY: flake.speedY,
              speedX: flake.speedX,
              type: (flake instanceof SnowDot)
                ? 'dot'
                : (flake instanceof EmberParticle ? 'ember' : 'flake')
            };
            if (typeof flake.windPhase === 'number') entry.windPhase = flake.windPhase;
            if (typeof flake.rot === 'number') entry.rot = flake.rot;
            if (typeof flake.glyph === 'string') entry.glyph = flake.glyph;
            if (typeof flake.flickerSpeed === 'number') entry.flickerSpeed = flake.flickerSpeed;
            return entry;
          });
          // Wrap with timestamp for potential TTL/validation
          localStorage.setItem('snowflakes', JSON.stringify({ ts: Date.now(), data: snowflakesState }));
        } catch (_) {}
    }
    // Function to restore the state of snowflakes (navbar snowfall)
    function restoreState() {
        try {
            const raw = localStorage.getItem('snowflakes');
            if (!raw) return;
            const parsed = JSON.parse(raw);
            const arr = Array.isArray(parsed) ? parsed : (parsed && Array.isArray(parsed.data) ? parsed.data : null);
            if (!arr) return;
            const n = Math.min(arr.length, flakes.length);
            for (let idx = 0; idx < n; idx++) {
                const state = arr[idx];
                if (!state) continue;
                // Recreate correct type
                let particle;
                if (state.type === 'ember' && !ALLOW_EMBERS) {
                  particle = new SnowDot();
                } else if (state.type === 'dot') {
                  particle = new SnowDot();
                } else if (state.type === 'ember') {
                  particle = new EmberParticle();
                } else {
                  particle = new Winterflake();
                }
                particle.x = (typeof state.x === 'number') ? state.x : particle.x;
                particle.y = (typeof state.y === 'number') ? state.y : particle.y;
                if (typeof state.speedX === 'number') particle.speedX = state.speedX;
                if (typeof state.speedY === 'number') particle.speedY = state.speedY;
                if (typeof state.windPhase === 'number') particle.windPhase = state.windPhase;
                if (typeof state.rot === 'number' && particle instanceof Winterflake) {
                  particle.rot = state.rot;
                }
                if (typeof state.glyph === 'string' && particle instanceof Winterflake) {
                  particle.glyph = state.glyph;
                }
                if (typeof state.flickerSpeed === 'number' && particle instanceof EmberParticle) {
                  particle.flickerSpeed = state.flickerSpeed;
                }
                flakes[idx] = particle;
            }
        } catch (_) {}
    }
    const RATIO_DOTS = IS_HALLOCHRISTMAS ? 0.55 : 0.7;
    const RATIO_EMBERS = ALLOW_EMBERS ? 0.18 : 0;
    const TOTAL_COUNT = FLAKE_COUNT;

    flakes.length = 0;
    for (let i = 0; i < TOTAL_COUNT; i++) {
      const mix = Math.random();
      if (mix < RATIO_DOTS) {
        flakes.push(new SnowDot());
      } else if (mix < RATIO_DOTS + RATIO_EMBERS) {
        flakes.push(new EmberParticle());
      } else {
        flakes.push(new Winterflake());
      }
    }

    // Animation loop with frame throttling (~24fps)
    const FRAME_INTERVAL = 1000 / 24;
    let lastTime = 0;

    function animate(ts) {
      if (!lastTime) lastTime = ts;
      const delta = ts - lastTime;
      if (delta < FRAME_INTERVAL) {
        requestAnimationFrame(animate);
        return;
      }
      lastTime = ts;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      for (let i = 0; i < flakes.length; i++) {
        const f = flakes[i];
        f.update();
        f.draw(ctx);
      }
      requestAnimationFrame(animate);
    }

    // Attempt to restore flake state once before starting animation
    restoreState();
    // Save state before page unload
    try { window.removeEventListener('beforeunload', saveState); } catch (_) {}
    window.addEventListener('beforeunload', saveState);

    requestAnimationFrame(animate);
  }

  function addHolidayGarland() {
    if (!IS_HALLOCHRISTMAS) {
      removeElementById('holiday-garland');
      return;
    }
    const nav = document.querySelector('nav.navbar');
    if (!nav) return;

    let garland = document.getElementById('holiday-garland');
    if (garland && garland.parentElement !== nav) {
      try { garland.remove(); } catch (_) {}
      garland = null;
    }

    if (!garland) {
      garland = document.createElement('div');
      garland.id = 'holiday-garland';
      garland.setAttribute('aria-hidden', 'true');
    }

    const iconOrder = ['pumpkin', 'snowflake', 'ornament', 'bat'];
    const icons = iconOrder.concat(iconOrder).concat(iconOrder.slice(0, 2));
    garland.innerHTML = `
      <div class="holiday-garland-track">
        ${icons.map((type) => {
          const markup = holidayIconMarkup(type);
          return `<span class="holiday-icon holiday-icon-${type}">${markup}</span>`;
        }).join('')}
      </div>
    `.trim();

    const canvas = document.getElementById('snow-canvas');
    if (!garland.parentElement) {
      if (canvas && canvas.parentElement === nav) {
        nav.insertBefore(garland, canvas.nextSibling);
      } else {
        nav.appendChild(garland);
      }
    }
  }

  function addFloatingSprites() {
    if (!IS_HALLOCHRISTMAS) {
      removeElementById('holiday-sprites');
      return;
    }
    const body = document.body;
    if (!body) return;

    let layer = document.getElementById('holiday-sprites');
    if (layer && layer.parentElement !== body) {
      try { layer.remove(); } catch (_) {}
      layer = null;
    }

    if (!layer) {
      layer = document.createElement('div');
      layer.id = 'holiday-sprites';
      layer.setAttribute('aria-hidden', 'true');
      body.appendChild(layer);
    }

    const sprites = [
      { type: 'ghost', left: '8%', top: '52%', duration: '28s', delay: '-6s', size: '92px', opacity: '0.55' },
      { type: 'cane', left: '74%', top: '46%', duration: '24s', delay: '-4s', size: '76px', opacity: '0.52' },
      { type: 'hat', left: '42%', top: '60%', duration: '26s', delay: '-2s', size: '88px', opacity: '0.6' },
      { type: 'ghost', left: '86%', top: '58%', duration: '32s', delay: '-10s', size: '80px', opacity: '0.45' }
    ];

    const spriteMarkup = sprites.map((sprite) => {
      const style = Object.entries({
        '--sprite-left': sprite.left,
        '--sprite-top': sprite.top,
        '--sprite-duration': sprite.duration,
        '--sprite-delay': sprite.delay,
        '--sprite-size': sprite.size,
        '--sprite-opacity': sprite.opacity
      }).filter(([, value]) => value != null)
        .map(([key, value]) => `${key}:${value}`)
        .join(';');
      return `<span class="sprite sprite-${sprite.type}" style="${style}">${floatingSpriteMarkup(sprite.type)}</span>`;
    }).join('');

    layer.innerHTML = spriteMarkup;
  }

  function holidayIconMarkup(type) {
    switch (type) {
      case 'pumpkin':
        return `
<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" role="presentation" focusable="false">
  <path fill="#f97316" d="M16 6c-5 0-9.5 4-9.5 9.3S11 24.5 16 24.5s9.5-4 9.5-9.3S21 6 16 6z"></path>
  <path fill="#fb923c" opacity="0.55" d="M16 6c-3.3 0-5.8 4-5.8 9.3s2.5 9.2 5.8 9.2 5.8-4 5.8-9.2S19.3 6 16 6z"></path>
  <path fill="#78350f" d="M15 3.6h2v4h-2z"></path>
  <path fill="#111827" d="M12.4 15.2l2-2.1 2.1 2.1h-4.1zm7.2 0l-2.1-2.1-2 2.1h4zm-7.2 4.5c1.3 0.9 3 1.5 4.6 1.5s3.3-.6 4.6-1.5c-1.1.2-2.9.5-4.6.5s-3.5-.3-4.6-.5z"></path>
</svg>`.trim();
      case 'snowflake':
        return `
<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" role="presentation" focusable="false">
  <path fill="#bfdbfe" d="M15 4h2v24h-2z"></path>
  <path fill="#bfdbfe" d="M4 15h24v2H4z"></path>
  <path fill="#bfdbfe" d="M8 8l1.4-1.4L24 21.2 22.6 22.6z"></path>
  <path fill="#bfdbfe" d="M24 8l1.4 1.4L10 22.6 8.6 21.2z"></path>
  <circle cx="16" cy="16" r="4" fill="#e0f2fe"></circle>
</svg>`.trim();
      case 'ornament':
        return `
<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" role="presentation" focusable="false">
  <circle cx="16" cy="17" r="9" fill="#ef4444"></circle>
  <path fill="#b91c1c" d="M14 6h4v5h-4z"></path>
  <path fill="#fca5a5" opacity="0.5" d="M16 10a7 7 0 00-7 7h6l3.5-6.1A6.9 6.9 0 0016 10z"></path>
  <circle cx="16" cy="17" r="3" fill="#fee2e2" opacity="0.8"></circle>
</svg>`.trim();
      case 'bat':
        return `
<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" role="presentation" focusable="false">
  <path fill="#1f2937" d="M4 19c1.2-3 3.2-5.4 6.2-5.1 1-2.7 3.6-4.6 5.8-4.6s4.8 1.9 5.8 4.6c3-.3 5 2.1 6.2 5.1-1.7-1-2.9-1-4.2 0-.9-1.8-2-2.7-3.2-2.7-1.3 0-2.5.9-3.7 2.7-1-.8-1.7-1.2-2.1-1.2s-1.1.4-2.1 1.2c-1.2-1.8-2.4-2.7-3.7-2.7-1.2 0-2.3.9-3.2 2.7-1.3-1-2.5-1-4.2 0z"></path>
  <circle cx="13.5" cy="15.5" r="0.7" fill="#fef08a"></circle>
  <circle cx="18.5" cy="15.5" r="0.7" fill="#fef08a"></circle>
</svg>`.trim();
      default:
        return '';
    }
  }

  function floatingSpriteMarkup(type) {
    switch (type) {
      case 'ghost':
        return `
<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="presentation" focusable="false">
  <path d="M32 6c-11.6 0-20 8.6-20 20.5v15.4c0 2.3 1.8 4.1 4.1 4.1 3.3 0 4.7-3.4 7.4-3.4s4.1 3.4 7.5 3.4 4.8-3.4 7.5-3.4 4.1 3.4 7.4 3.4c2.3 0 4.1-1.8 4.1-4.1V26.5C52 14.6 43.6 6 32 6z" fill="rgba(255,255,255,0.82)"></path>
  <circle cx="24.5" cy="24.5" r="2.8" fill="#0f172a"></circle>
  <circle cx="39.5" cy="24.5" r="2.8" fill="#0f172a"></circle>
  <path d="M26 34c1.8 1.6 3.8 2.4 6 2.4s4.2-0.8 6-2.4" stroke="#0f172a" stroke-width="2.2" stroke-linecap="round" fill="none"></path>
</svg>`.trim();
      case 'cane':
        return `
<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="presentation" focusable="false">
  <path d="M36 10c-7 0-12 5.3-12 12v26.5c0 2.6 2.1 4.7 4.7 4.7h2.6c2.6 0 4.7-2.1 4.7-4.7V22c0-2.2 1.8-4 4-4s4 1.8 4 4c0 2.8 2.2 5 5 5s5-2.2 5-5c0-6.7-5.3-12-12-12z" fill="#f87171"></path>
  <path d="M36 14c-4 0-7 3-7 7v27c0 1.1.9 2 2 2h2c1.1 0 2-.9 2-2V22c0-4.4 3.6-8 8-8" fill="#fef2f2"></path>
  <path d="M31 27h10" stroke="#ef4444" stroke-width="2.6" stroke-linecap="round"></path>
  <path d="M31 35h10" stroke="#ef4444" stroke-width="2.6" stroke-linecap="round"></path>
  <path d="M31 43h10" stroke="#ef4444" stroke-width="2.6" stroke-linecap="round"></path>
</svg>`.trim();
      case 'hat':
        return `
<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="presentation" focusable="false">
  <path d="M32 12c-7.5 0-12.8 6.6-13.8 18.1-.4 4.2-.7 8.7-1.2 13.6-.3 2.8 2 5.3 4.8 5.3h20.4c2.8 0 5-2.5 4.8-5.3-.5-4.9-.8-9.4-1.2-13.6C44.8 18.6 39.5 12 32 12z" fill="#111827"></path>
  <rect x="10" y="42" width="44" height="8" rx="3.2" fill="#1f2937"></rect>
  <rect x="20" y="32" width="24" height="6" fill="#d946ef"></rect>
  <path d="M25 32h14" stroke="#f9a8d4" stroke-width="2" stroke-linecap="round"></path>
</svg>`.trim();
      default:
        return '';
    }
  }

  // Adds decorative snow hills at the bottom edge of the navbar (disabled per request)
  function addSnowHillsNav(nav, canvas) {
    try {
      const existing = document.getElementById('snow-hills-nav');
      if (existing) { try { existing.remove(); } catch (_) {} }
      return;
      let hills = document.getElementById('snow-hills-nav');
      if (hills && hills.parentElement !== nav) {
        try { hills.remove(); } catch (_) {}
        hills = null;
      }
      if (!hills) {
        hills = document.createElement('div');
        hills.id = 'snow-hills-nav';
        hills.setAttribute('aria-hidden', 'true');
        // Insert right after the canvas
        if (canvas && canvas.parentElement === nav) {
          nav.insertBefore(hills, canvas.nextSibling);
        } else {
          const ref = nav.firstChild ? nav.firstChild.nextSibling : null;
          nav.insertBefore(hills, ref);
        }
      }

      // Deterministic pseudo-random helper for small variations (avoid jank across renders)
      function prand(i) {
        const n = ((i * 9301 + 49297) % 233280) / 233280;
        return n;
      }

      function buildHillsSVG(widthPx) {
        const H = 28; // fixed visual height in px (kept in CSS too)
        const W = Math.max(320, Math.floor(widthPx)); // minimum so waves are visible even on very narrow widths

        // Wave helper: build a cubic-bezier wave across W at a given baseline/amp/period
        function wavePath(baseline, amp, period) {
          let d = `M0,${baseline}`;
          for (let x = 0; x <= W; x += period) {
            const x1 = x + period * 0.25;
            const x2 = x + period * 0.75;
            const x3 = x + period;
            const yUp = baseline - amp;
            const yDown = baseline + amp;
            d += ` C ${x1},${yUp} ${x2},${yDown} ${x3},${baseline}`;
          }
          d += ` L ${W},${H} L 0,${H} Z`;
          return d;
        }

        // Paths tuned to keep curves visible at wide widths
        const backPath = wavePath(24, 3.4, 36);
        const midPath  = wavePath(22, 4.6, 30);
        const frontPath= wavePath(20, 6.2, 24);

        // Trees along the front baseline; density scales with width
        const nTrees = Math.min(18, Math.max(6, Math.floor(W / 110) + 4));
        let trees = '';
        for (let i = 0; i < nTrees; i++) {
          const t = (i + 0.5) / nTrees;
          const x = Math.floor(t * W);
          // Slight deterministic size/offset variation
          const r = prand(i);
          const triHalf = 2.4 + Math.floor(r * 3) * 0.4; // 2.4..3.6
          const topLift = 4 + Math.floor(r * 3);         // 4..6
          const baseY = 20;                               // front baseline
          const topY = baseY - (6 + topLift);            // higher top for taller trees

          const poly = `${x},${topY} ${x - triHalf},${baseY} ${x + triHalf},${baseY}`;
          const trunkW = 1.1 + (r > 0.66 ? 0.1 : 0);
          const trunkH = 2.6;
          const trunkX = (x - trunkW / 2).toFixed(2);
          const trunkY = baseY.toFixed(2);

          trees += `
    <g>
      <polygon points="${poly}" fill="#2e7d32"></polygon>
      <rect x="${trunkX}" y="${trunkY}" width="${trunkW}" height="${trunkH}" fill="#8b5a2b"></rect>
    </g>`;
        }

        // Compose SVG with viewBox matching actual pixel width/height to avoid distortion
        return `
<svg width="100%" height="100%" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <rect x="0" y="0" width="${W}" height="${H}" fill="none"></rect>

  <!-- Back soft ridge -->
  <path d="${backPath}" fill="#ffffff" opacity="0.78"></path>

  <!-- Middle hill layer -->
  <path d="${midPath}" fill="#ffffff" opacity="0.88"></path>

  <!-- Front hill layer (strongest curvature) -->
  <path d="${frontPath}" fill="#ffffff" opacity="0.96"></path>

  <!-- Christmas trees along the front hill baseline -->
  <g id="snow-trees" opacity="0.95">
    ${trees}
  </g>
</svg>`.trim();
      }

      function renderHills() {
        const rect = nav.getBoundingClientRect();
        hills.innerHTML = buildHillsSVG(rect.width || 1024);
      }

      // Initial render + on resize (recompute to keep curvature/trees crisp)
      renderHills();
      // Debounced resize
      let hillsRaf = null;
      const onResize = () => {
        if (hillsRaf) return;
        hillsRaf = requestAnimationFrame(() => {
          hillsRaf = null;
          renderHills();
        });
      };
      window.addEventListener('resize', onResize);
    } catch (_) {}
  }

  function addSnowGround() {
    if (document.getElementById('snow-ground')) return;

    const ground = document.createElement('div');
    ground.id = 'snow-ground';
    // Lightweight SVG hills; preserveAspectRatio none to stretch full width
    ground.innerHTML = `
<svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <rect x="0" y="0" width="100" height="100" fill="none"></rect>
  <path d="M0,70 C15,60 30,80 45,72 C60,64 75,82 100,70 L100,100 L0,100 Z" fill="#ffffff" opacity="0.95"></path>
  <path d="M0,78 C20,70 35,86 52,80 C70,74 85,88 100,80 L100,100 L0,100 Z" fill="#ffffff" opacity="0.85"></path>
</svg>
    `.trim();
    document.body.appendChild(ground);
  }

  function addSnowman() {
    if (document.getElementById('snowman-container')) return;

    const wrap = document.createElement('div');
    wrap.id = 'snowman-container';
    // Inline SVG snowman; classes used by CSS for animation
    wrap.innerHTML = `
<svg width="100%" height="100%" viewBox="0 0 160 200" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <!-- Ground snow -->
  <ellipse cx="120" cy="190" rx="120" ry="22" fill="rgba(255,255,255,0.75)"></ellipse>

  <!-- Body -->
  <circle cx="80" cy="140" r="42" fill="#ffffff" stroke="#e2e8f0" stroke-width="3"></circle>
  <circle cx="80" cy="85" r="32" fill="#ffffff" stroke="#e2e8f0" stroke-width="3"></circle>

  <!-- Buttons -->
  <circle class="coal" cx="80" cy="120" r="3.5" fill="#333"></circle>
  <circle class="coal" cx="80" cy="140" r="3.5" fill="#333"></circle>
  <circle class="coal" cx="80" cy="160" r="3.5" fill="#333"></circle>

  <!-- Eyes -->
  <circle class="coal" cx="70" cy="80" r="3.2" fill="#222"></circle>
  <circle class="coal" cx="90" cy="80" r="3.2" fill="#222"></circle>

  <!-- Carrot nose -->
  <polygon class="carrot" points="80,86 105,92 80,98" fill="#ff7f2a"></polygon>

  <!-- Smile -->
  <path d="M67,98 Q80,108 93,98" stroke="#444" stroke-width="2" fill="none" stroke-linecap="round"></path>

  <!-- Hat -->
  <rect x="60" y="46" width="40" height="20" fill="#1f2937" rx="3"></rect>
  <rect x="52" y="64" width="56" height="6" fill="#1f2937" rx="3"></rect>
  <rect x="60" y="46" width="40" height="8" fill="#2563eb" opacity="0.9"></rect>

  <!-- Arms -->
  <g class="arm arm-left">
    <path d="M42,120 C30,110 18,105 10,100" stroke="#8b5a2b" stroke-width="4" fill="none" stroke-linecap="round"></path>
    <path d="M18,106 l-10,-6" stroke="#8b5a2b" stroke-width="3" stroke-linecap="round"></path>
    <path d="M22,100 l-9,-8" stroke="#8b5a2b" stroke-width="3" stroke-linecap="round"></path>
  </g>
  <g class="arm arm-right">
    <path d="M118,120 C130,110 142,105 150,100" stroke="#8b5a2b" stroke-width="4" fill="none" stroke-linecap="round"></path>
    <path d="M142,106 l10,-6" stroke="#8b5a2b" stroke-width="3" stroke-linecap="round"></path>
    <path d="M138,100 l9,-8" stroke="#8b5a2b" stroke-width="3" stroke-linecap="round"></path>
  </g>

  <!-- Scarf -->
  <path d="M58,98 C80,105 102,98 104,92 C92,96 68,96 56,92" fill="#ef4444" opacity="0.95"></path>
  <rect x="74" y="98" width="8" height="18" fill="#ef4444" rx="2"></rect>
</svg>
    `.trim();

    document.body.appendChild(wrap);

    // Make non-semantic and enable proximity hover while keeping pointer-events off
    try { wrap.setAttribute('aria-hidden', 'true'); } catch (e) {}

    enableSnowmanProximityHover(wrap);
  }

  // Proximity-based hover: toggles .hover-active when cursor/finger is within the snowman bounds
  function enableSnowmanProximityHover(wrap) {
    const PAD = 6; // small tolerance area around the snowman
    let wasInside = false;
    let lastGreetingTime = 0;
    let hideTimer = null;

    function getUsername() {
      try {
        const name = document.body && document.body.dataset ? document.body.dataset.username : '';
        return (name && name.trim()) ? name.trim() : 'Friend';
      } catch (_) {
        return 'Friend';
      }
    }

    function ensureGreetingEl() {
      let el = document.getElementById('snowman-greeting');
      if (!el) {
        el = document.createElement('div');
        el.id = 'snowman-greeting';
        document.body.appendChild(el);
      }
      return el;
    }

    function positionGreeting(el, rect) {
      // position above snowman centered
      const padding = 8;
      // Temporarily ensure it's measurable
      const prevDisplay = el.style.display;
      if (!el.classList.contains('show')) {
        el.style.display = 'block';
      }
      const top = Math.max(4, Math.floor(rect.top - el.offsetHeight - padding));
      const left = Math.floor(rect.left + (rect.width / 2) - (el.offsetWidth / 2));
      el.style.top = top + 'px';
      el.style.left = Math.max(4, left) + 'px';
      el.style.display = prevDisplay || '';
    }

    function showGreeting(rect) {
      const now = Date.now();
      if (now - lastGreetingTime < 20000) return; // throttle: once every 20s
      lastGreetingTime = now;

      const el = ensureGreetingEl();
      const username = getUsername();
      const message = IS_HALLOCHRISTMAS
        ? `Happy Hallo-Christmas, ${username}! Stay cozy and spooky!`
        : `Warm winter wishes, ${username}! Stay cozy out there!`;
      el.textContent = message;

      // Show and position after layout
      el.classList.add('show');
      requestAnimationFrame(() => {
        positionGreeting(el, rect);
      });

      if (hideTimer) { clearTimeout(hideTimer); }
      hideTimer = setTimeout(() => { hideGreeting(); }, 3000);
    }

    function hideGreeting() {
      const el = document.getElementById('snowman-greeting');
      if (el) el.classList.remove('show');
    }

    function onMove(clientX, clientY) {
      const rect = wrap.getBoundingClientRect();
      const inside =
        clientX >= rect.left - PAD &&
        clientX <= rect.right + PAD &&
        clientY >= rect.top - PAD &&
        clientY <= rect.bottom + PAD;
      if (inside) {
        wrap.classList.add('hover-active');
        if (!wasInside) {
          showGreeting(rect);
        }
      } else {
        wrap.classList.remove('hover-active');
      }
      wasInside = inside;
    }

    // Mouse support
    window.addEventListener('mousemove', (e) => onMove(e.clientX, e.clientY), { passive: true });

    // Touch support
    window.addEventListener('touchstart', (e) => {
      const t = e.touches && e.touches[0];
      if (t) onMove(t.clientX, t.clientY);
    }, { passive: true });

    window.addEventListener('touchmove', (e) => {
      const t = e.touches && e.touches[0];
      if (t) onMove(t.clientX, t.clientY);
    }, { passive: true });

    // Clear active state when interaction ends or window blurs
    window.addEventListener('touchend', () => { wrap.classList.remove('hover-active'); hideGreeting(); }, { passive: true });
    window.addEventListener('blur', () => { wrap.classList.remove('hover-active'); hideGreeting(); });
  }
})();

