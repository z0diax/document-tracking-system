/*
 * Chinese New Year theme: hanging lanterns, festive confetti, and lucky floaters.
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

  function isCnyTheme() {
    var body = document.body;
    if (!body || !body.dataset) return false;
    return String(body.dataset.seasonTheme || '').toLowerCase() === 'chinesenewyear';
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
    if (type === 'coin') {
      return (
        '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="presentation" focusable="false">' +
          '<circle class="cny-coin-outer" cx="32" cy="32" r="27"></circle>' +
          '<circle class="cny-coin-inner-ring" cx="32" cy="32" r="18"></circle>' +
          '<rect class="cny-coin-hole" x="24" y="24" width="16" height="16" rx="2"></rect>' +
          '<path class="cny-coin-engrave" d="M32 13c-2.8 0-5.4.5-7.8 1.4"></path>' +
        '</svg>'
      );
    }

    if (type === 'ingot') {
      return (
        '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="presentation" focusable="false">' +
          '<path class="cny-ingot-body" d="M8 39c0 8 7.4 14 24 14s24-6 24-14c0-2.8-1.8-5.6-5.2-8.2L45.5 22c-2.7-4.2-7.3-6.4-13.5-6.4s-10.8 2.2-13.5 6.4l-5.3 8.8C9.8 33.4 8 36.2 8 39z"></path>' +
          '<ellipse class="cny-ingot-top" cx="32" cy="30" rx="14" ry="6.3"></ellipse>' +
          '<ellipse class="cny-ingot-rim" cx="32" cy="30" rx="7.2" ry="3"></ellipse>' +
        '</svg>'
      );
    }

    if (type === 'firecracker') {
      return (
        '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="presentation" focusable="false">' +
          '<rect class="cny-cracker-body" x="18" y="12" width="28" height="40" rx="7"></rect>' +
          '<rect class="cny-cracker-band" x="18" y="22" width="28" height="5"></rect>' +
          '<rect class="cny-cracker-band" x="18" y="37" width="28" height="5"></rect>' +
          '<path class="cny-cracker-fuse" d="M32 12c0-6 3-8 7-9"></path>' +
          '<circle class="cny-cracker-spark" cx="41" cy="4" r="2.2"></circle>' +
        '</svg>'
      );
    }

    return '';
  }

  function renderLanterns() {
    var nav = document.querySelector('nav.navbar');
    if (!nav || !isCnyTheme()) {
      removeLayer('cny-lanterns');
      return;
    }

    var layer = document.getElementById('cny-lanterns');
    if (layer && layer.parentElement !== nav) {
      removeLayer('cny-lanterns');
      layer = null;
    }

    if (!layer) {
      layer = document.createElement('div');
      layer.id = 'cny-lanterns';
      layer.setAttribute('aria-hidden', 'true');
    }

    var durations = ['5.4s', '6.2s', '5.8s', '6.5s', '5.6s', '6.1s', '5.7s', '6.3s', '5.9s', '6.6s'];
    var delays = ['-1.0s', '-2.6s', '-3.2s', '-4.4s', '-1.8s', '-3.8s', '-2.2s', '-4.9s', '-0.7s', '-3.4s'];
    var scales = ['1.00', '0.94', '1.05', '0.98', '1.03', '0.92', '1.04', '0.96', '1.02', '0.95'];

    var items = durations.map(function(duration, idx) {
      var style =
        '--lantern-sway-duration:' + duration +
        ';--lantern-sway-delay:' + delays[idx] +
        ';--lantern-scale:' + scales[idx] + ';';
      return (
        '<span class="cny-lantern" style="' + style + '">' +
          '<span class="cny-lantern-cord"></span>' +
          '<span class="cny-lantern-cap"></span>' +
          '<span class="cny-lantern-body">' +
            '<span class="cny-lantern-emblem"></span>' +
          '</span>' +
          '<span class="cny-lantern-tassel"></span>' +
        '</span>'
      );
    });

    layer.innerHTML = '<div class="cny-lantern-track">' + items.join('') + '</div>';
    if (!layer.parentElement) {
      nav.appendChild(layer);
    }
  }

  function renderGreeting() {
    var nav = document.querySelector('nav.navbar');
    if (!nav || !isCnyTheme()) {
      removeLayer('cny-greeting-banner');
      return;
    }

    var layer = document.getElementById('cny-greeting-banner');
    if (layer && layer.parentElement !== nav) {
      removeLayer('cny-greeting-banner');
      layer = null;
    }

    if (!layer) {
      layer = document.createElement('div');
      layer.id = 'cny-greeting-banner';
      layer.setAttribute('aria-hidden', 'true');
    }

    layer.innerHTML =
      '<div class="cny-greeting-inner">' +
        '<span class="cny-greeting-text cny-greeting-text-left">Kung Hei Fat Choi!</span>' +
        '<span class="cny-greeting-spacer"></span>' +
        '<span class="cny-greeting-text cny-greeting-text-right">新年快樂</span>' +
      '</div>';

    if (!layer.parentElement) {
      nav.appendChild(layer);
    }
  }

  function renderConfetti() {
    var nav = document.querySelector('nav.navbar');
    if (!nav || !isCnyTheme() || isRspTrackerView()) {
      removeLayer('cny-confetti');
      return;
    }

    var layer = document.getElementById('cny-confetti');
    if (layer && layer.parentElement !== nav) {
      removeLayer('cny-confetti');
      layer = null;
    }

    if (!layer) {
      layer = document.createElement('div');
      layer.id = 'cny-confetti';
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
      'var(--cny-gold-1)',
      'var(--cny-gold-2)',
      'var(--cny-red-2)',
      'var(--cny-red-3)'
    ];
    var shapes = ['is-square', 'is-diamond', 'is-circle'];
    var pieces = [];

    for (var i = 0; i < count; i += 1) {
      var left = random(-4, 104).toFixed(2);
      var size = random(8, 14).toFixed(2);
      var opacity = random(0.32, 0.76).toFixed(2);
      var duration = random(prefersReducedMotion ? 12 : 9, prefersReducedMotion ? 18 : 15).toFixed(2);
      var delay = (-random(0, parseFloat(duration))).toFixed(2);
      var drift = random(-44, 44).toFixed(2);
      var spinStart = random(-40, 40).toFixed(2);
      var spinEnd = (parseFloat(spinStart) + random(-210, 210)).toFixed(2);
      var drop = (navHeight + random(26, 44)).toFixed(2);
      var color = colors[Math.floor(random(0, colors.length))];
      var shape = shapes[Math.floor(random(0, shapes.length))];

      var style =
        '--cny-left:' + left + '%;' +
        '--cny-size:' + size + 'px;' +
        '--cny-opacity:' + opacity + ';' +
        '--cny-duration:' + duration + 's;' +
        '--cny-delay:' + delay + 's;' +
        '--cny-drift:' + drift + 'px;' +
        '--cny-drop:' + drop + 'px;' +
        '--cny-rot-start:' + spinStart + 'deg;' +
        '--cny-rot-end:' + spinEnd + 'deg;' +
        '--cny-color:' + color + ';';

      pieces.push('<span class="cny-confetti-piece ' + shape + '" style="' + style + '"></span>');
    }

    layer.innerHTML = pieces.join('');
    if (!layer.parentElement) {
      nav.insertBefore(layer, nav.firstChild);
    }
  }

  function renderFloaters() {
    var body = document.body;
    if (!body || !isCnyTheme() || isRspTrackerView()) {
      removeLayer('cny-floaters');
      return;
    }

    var layer = document.getElementById('cny-floaters');
    if (layer && layer.parentElement !== body) {
      removeLayer('cny-floaters');
      layer = null;
    }

    if (!layer) {
      layer = document.createElement('div');
      layer.id = 'cny-floaters';
      layer.setAttribute('aria-hidden', 'true');
    }

    var sprites = [
      { type: 'coin', left: '9%', top: '56%', duration: '30s', delay: '-6s', size: '90px', opacity: '0.5' },
      { type: 'firecracker', left: '42%', top: '66%', duration: '28s', delay: '-2s', size: '84px', opacity: '0.48' },
      { type: 'ingot', left: '76%', top: '47%', duration: '25s', delay: '-8s', size: '78px', opacity: '0.5' },
      { type: 'coin', left: '88%', top: '61%', duration: '32s', delay: '-12s', size: '82px', opacity: '0.44' }
    ];

    var markup = sprites.map(function(sprite) {
      var style =
        '--cny-sprite-left:' + sprite.left + ';' +
        '--cny-sprite-top:' + sprite.top + ';' +
        '--cny-sprite-duration:' + sprite.duration + ';' +
        '--cny-sprite-delay:' + sprite.delay + ';' +
        '--cny-sprite-size:' + sprite.size + ';' +
        '--cny-sprite-opacity:' + sprite.opacity + ';';
      return (
        '<span class="cny-sprite cny-sprite-' + sprite.type + '" style="' + style + '">' +
          floatingSpriteMarkup(sprite.type) +
        '</span>'
      );
    }).join('');

    layer.innerHTML = markup;
    if (!layer.parentElement) {
      body.appendChild(layer);
    }
  }

  function renderAll() {
    renderLanterns();
    renderGreeting();
    renderConfetti();
    renderFloaters();
  }

  var resizeTimer = null;
  function onResize() {
    if (resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function() {
      renderConfetti();
    }, 130);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderAll);
  } else {
    renderAll();
  }

  window.addEventListener('resize', onResize, { passive: true });
})();
