/*
 * National Women's Month theme: hanging blooms, petal fall, and celebratory floaters.
 */
(function() {
  function removeLayer(id) {
    var el = document.getElementById(id);
    if (!el) return;
    if (typeof el.remove === 'function') {
      el.remove();
    } else if (el.parentNode) {
      el.parentNode.removeChild(el);
    }
  }

  function random(min, max) {
    return Math.random() * (max - min) + min;
  }

  function isWomensMonthTheme() {
    var body = document.body;
    if (!body || !body.dataset) return false;
    return String(body.dataset.seasonTheme || '').toLowerCase() === 'womensmonth';
  }

  function isRspTrackerView() {
    try {
      var params = new URLSearchParams(window.location.search || '');
      return String(params.get('view') || '').toLowerCase() === 'rsp';
    } catch (err) {
      return false;
    }
  }

  function floatingSpriteMarkup(type) {
    if (type === 'flower') {
      return (
        '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="presentation" focusable="false">' +
          '<circle class="wm-flower-petal wm-flower-petal-a" cx="32" cy="15" r="8"></circle>' +
          '<circle class="wm-flower-petal wm-flower-petal-b" cx="48" cy="27" r="8"></circle>' +
          '<circle class="wm-flower-petal wm-flower-petal-c" cx="42" cy="46" r="8"></circle>' +
          '<circle class="wm-flower-petal wm-flower-petal-d" cx="22" cy="46" r="8"></circle>' +
          '<circle class="wm-flower-petal wm-flower-petal-e" cx="16" cy="27" r="8"></circle>' +
          '<circle class="wm-flower-core" cx="32" cy="32" r="8.5"></circle>' +
          '<circle class="wm-flower-core-dot" cx="32" cy="32" r="3"></circle>' +
        '</svg>'
      );
    }

    if (type === 'venus') {
      return (
        '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="presentation" focusable="false">' +
          '<circle class="wm-venus-ring" cx="32" cy="24" r="15"></circle>' +
          '<path class="wm-venus-stem" d="M32 39v14"></path>' +
          '<path class="wm-venus-cross" d="M24 47h16"></path>' +
          '<circle class="wm-venus-core" cx="32" cy="24" r="5"></circle>' +
        '</svg>'
      );
    }

    if (type === 'spark') {
      return (
        '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="presentation" focusable="false">' +
          '<path class="wm-spark-shape" d="M32 7l5.4 16.6L54 32l-16.6 8.4L32 57l-5.4-16.6L10 32l16.6-8.4L32 7z"></path>' +
          '<circle class="wm-spark-core" cx="32" cy="32" r="4"></circle>' +
        '</svg>'
      );
    }

    return '';
  }

  function renderBlooms() {
    var nav = document.querySelector('nav.navbar');
    if (!nav || !isWomensMonthTheme()) {
      removeLayer('wm-blooms');
      return;
    }

    var layer = document.getElementById('wm-blooms');
    if (layer && layer.parentElement !== nav) {
      removeLayer('wm-blooms');
      layer = null;
    }

    if (!layer) {
      layer = document.createElement('div');
      layer.id = 'wm-blooms';
      layer.setAttribute('aria-hidden', 'true');
    }

    var durations = ['5.2s', '5.8s', '6.3s', '5.4s', '6.1s', '5.6s', '6.4s', '5.3s', '6.0s', '5.7s'];
    var delays = ['-0.8s', '-2.9s', '-3.7s', '-1.9s', '-4.3s', '-2.2s', '-3.1s', '-4.8s', '-1.2s', '-3.9s'];
    var scales = ['1.00', '0.95', '1.05', '0.97', '1.03', '0.92', '1.06', '0.96', '1.02', '0.94'];

    var items = durations.map(function(duration, idx) {
      var style =
        '--wm-sway-duration:' + duration +
        ';--wm-sway-delay:' + delays[idx] +
        ';--wm-bloom-scale:' + scales[idx] + ';';
      return (
        '<span class="wm-bloom" style="' + style + '">' +
          '<span class="wm-bloom-cord"></span>' +
          '<span class="wm-bloom-cap"></span>' +
          '<span class="wm-bloom-body">' +
            '<span class="wm-bloom-core"></span>' +
          '</span>' +
          '<span class="wm-bloom-tail"></span>' +
        '</span>'
      );
    });

    layer.innerHTML = '<div class="wm-bloom-track">' + items.join('') + '</div>';
    if (!layer.parentElement) {
      nav.appendChild(layer);
    }
  }

  function renderGreeting() {
    var nav = document.querySelector('nav.navbar');
    if (!nav || !isWomensMonthTheme()) {
      removeLayer('wm-greeting-banner');
      return;
    }

    var layer = document.getElementById('wm-greeting-banner');
    if (layer && layer.parentElement !== nav) {
      removeLayer('wm-greeting-banner');
      layer = null;
    }

    if (!layer) {
      layer = document.createElement('div');
      layer.id = 'wm-greeting-banner';
      layer.setAttribute('aria-hidden', 'true');
    }

    layer.innerHTML =
      '<div class="wm-greeting-inner">' +
        '<span class="wm-greeting-text wm-greeting-text-left">National Women&#39;s Month</span>' +
        '<span class="wm-greeting-spacer"></span>' +
        '<span class="wm-greeting-text wm-greeting-text-right">Celebrating Every Woman</span>' +
      '</div>';

    if (!layer.parentElement) {
      nav.appendChild(layer);
    }
  }

  function renderPetals() {
    var nav = document.querySelector('nav.navbar');
    if (!nav || !isWomensMonthTheme() || isRspTrackerView()) {
      removeLayer('wm-petals');
      return;
    }

    var layer = document.getElementById('wm-petals');
    if (layer && layer.parentElement !== nav) {
      removeLayer('wm-petals');
      layer = null;
    }

    if (!layer) {
      layer = document.createElement('div');
      layer.id = 'wm-petals';
      layer.setAttribute('aria-hidden', 'true');
    }

    var prefersReducedMotion = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    var width = Math.max(320, nav.clientWidth || window.innerWidth || 1280);
    var navHeight = Math.max(56, nav.clientHeight || 60);
    var count = prefersReducedMotion
      ? Math.round(width / 180)
      : Math.round(width / 110);

    if (prefersReducedMotion) {
      count = Math.max(8, Math.min(14, count));
    } else {
      count = Math.max(10, Math.min(22, count));
    }

    var colors = [
      'var(--wm-rose-2)',
      'var(--wm-rose-1)',
      'var(--wm-plum-2)',
      'var(--wm-gold-1)',
      'var(--wm-sage-1)'
    ];
    var shapes = ['is-petal', 'is-dot', 'is-leaf'];
    var pieces = [];

    for (var i = 0; i < count; i += 1) {
      var left = random(-4, 104).toFixed(2);
      var size = random(8, 14).toFixed(2);
      var opacity = random(0.34, 0.78).toFixed(2);
      var duration = random(prefersReducedMotion ? 12 : 8, prefersReducedMotion ? 18 : 14).toFixed(2);
      var delay = (-random(0, parseFloat(duration))).toFixed(2);
      var drift = random(-40, 40).toFixed(2);
      var spinStart = random(-35, 35).toFixed(2);
      var spinEnd = (parseFloat(spinStart) + random(-180, 180)).toFixed(2);
      var drop = (navHeight + random(26, 44)).toFixed(2);
      var color = colors[Math.floor(random(0, colors.length))];
      var shape = shapes[Math.floor(random(0, shapes.length))];

      var style =
        '--wm-left:' + left + '%;' +
        '--wm-size:' + size + 'px;' +
        '--wm-opacity:' + opacity + ';' +
        '--wm-duration:' + duration + 's;' +
        '--wm-delay:' + delay + 's;' +
        '--wm-drift:' + drift + 'px;' +
        '--wm-drop:' + drop + 'px;' +
        '--wm-rot-start:' + spinStart + 'deg;' +
        '--wm-rot-end:' + spinEnd + 'deg;' +
        '--wm-color:' + color + ';';

      pieces.push('<span class="wm-petal ' + shape + '" style="' + style + '"></span>');
    }

    layer.innerHTML = pieces.join('');
    if (!layer.parentElement) {
      nav.insertBefore(layer, nav.firstChild);
    }
  }

  function renderFloaters() {
    var body = document.body;
    if (!body || !isWomensMonthTheme() || isRspTrackerView()) {
      removeLayer('wm-floaters');
      return;
    }

    var layer = document.getElementById('wm-floaters');
    if (layer && layer.parentElement !== body) {
      removeLayer('wm-floaters');
      layer = null;
    }

    if (!layer) {
      layer = document.createElement('div');
      layer.id = 'wm-floaters';
      layer.setAttribute('aria-hidden', 'true');
      body.appendChild(layer);
    }

    var sprites = [
      { type: 'flower', left: '10%', top: '58%', duration: '30s', delay: '-6s', size: '92px', opacity: '0.54' },
      { type: 'venus', left: '38%', top: '66%', duration: '28s', delay: '-3s', size: '84px', opacity: '0.48' },
      { type: 'spark', left: '58%', top: '42%', duration: '24s', delay: '-9s', size: '72px', opacity: '0.42' },
      { type: 'flower', left: '80%', top: '52%', duration: '32s', delay: '-12s', size: '86px', opacity: '0.46' },
      { type: 'venus', left: '88%', top: '68%', duration: '29s', delay: '-5s', size: '76px', opacity: '0.4' }
    ];

    var markup = sprites.map(function(sprite) {
      var style =
        '--wm-sprite-left:' + sprite.left + ';' +
        '--wm-sprite-top:' + sprite.top + ';' +
        '--wm-sprite-duration:' + sprite.duration + ';' +
        '--wm-sprite-delay:' + sprite.delay + ';' +
        '--wm-sprite-size:' + sprite.size + ';' +
        '--wm-sprite-opacity:' + sprite.opacity + ';';

      return (
        '<span class="wm-sprite wm-sprite-' + sprite.type + '" style="' + style + '">' +
          floatingSpriteMarkup(sprite.type) +
        '</span>'
      );
    }).join('');

    layer.innerHTML = markup;
  }

  function renderAll() {
    renderBlooms();
    renderGreeting();
    renderPetals();
    renderFloaters();
  }

  var resizeTimer = null;
  function onResize() {
    if (resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function() {
      renderPetals();
    }, 130);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderAll);
  } else {
    renderAll();
  }

  window.addEventListener('resize', onResize, { passive: true });
})();
