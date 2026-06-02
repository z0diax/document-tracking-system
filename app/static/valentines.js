/*
 * Valentine's theme: hanging heart lanterns, falling hearts, and floating sprites.
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

  function isValentineTheme() {
    var body = document.body;
    if (!body || !body.dataset) return false;
    return String(body.dataset.seasonTheme || '').toLowerCase() === 'valentines';
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
    if (type === 'heart') {
      return (
        '<svg class="vf-heart-shape" viewBox="0 0 24 22" xmlns="http://www.w3.org/2000/svg" role="presentation" focusable="false">' +
          '<path class="vf-heart-core" d="M12 21s-1.1-.9-2.6-2.2C5.1 15.2 1 11.8 1 7.6 1 4.5 3.5 2 6.6 2c1.9 0 3.8.9 4.9 2.3C12.6 2.9 14.5 2 16.4 2 19.5 2 22 4.5 22 7.6c0 4.2-4.1 7.6-8.4 11.2C13.1 20.1 12 21 12 21z"></path>' +
          '<path class="vf-heart-gloss" d="M9.3 4.9c-.8-.7-2.2-.7-3 .1-.7.7-1 1.8-.7 2.8.2.5.8.8 1.3.6.5-.2.8-.8.6-1.3-.2-.4-.1-.9.2-1.2.3-.3.9-.3 1.3-.1.5.3 1.1.1 1.4-.3.3-.5.1-1.1-.3-1.4-.2-.1-.4-.2-.8-.4z"></path>' +
          '<path class="vf-heart-outline" d="M12 21s-1.1-.9-2.6-2.2C5.1 15.2 1 11.8 1 7.6 1 4.5 3.5 2 6.6 2c1.9 0 3.8.9 4.9 2.3C12.6 2.9 14.5 2 16.4 2 19.5 2 22 4.5 22 7.6c0 4.2-4.1 7.6-8.4 11.2C13.1 20.1 12 21 12 21z"></path>' +
        '</svg>'
      );
    }
    if (type === 'flower') {
      return (
        '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="presentation" focusable="false">' +
          '<circle class="vfloat-flower-petal vfloat-flower-petal-outer" cx="32" cy="15" r="8"></circle>' +
          '<circle class="vfloat-flower-petal vfloat-flower-petal-outer" cx="49" cy="27" r="8"></circle>' +
          '<circle class="vfloat-flower-petal vfloat-flower-petal-outer" cx="43" cy="47" r="8"></circle>' +
          '<circle class="vfloat-flower-petal vfloat-flower-petal-outer" cx="21" cy="47" r="8"></circle>' +
          '<circle class="vfloat-flower-petal vfloat-flower-petal-outer" cx="15" cy="27" r="8"></circle>' +
          '<circle class="vfloat-flower-petal vfloat-flower-petal-inner" cx="40" cy="20" r="6.4"></circle>' +
          '<circle class="vfloat-flower-petal vfloat-flower-petal-inner" cx="46" cy="37" r="6.4"></circle>' +
          '<circle class="vfloat-flower-petal vfloat-flower-petal-inner" cx="32" cy="49" r="6.4"></circle>' +
          '<circle class="vfloat-flower-petal vfloat-flower-petal-inner" cx="18" cy="37" r="6.4"></circle>' +
          '<circle class="vfloat-flower-petal vfloat-flower-petal-inner" cx="24" cy="20" r="6.4"></circle>' +
          '<circle class="vfloat-flower-center" cx="32" cy="32" r="8"></circle>' +
          '<circle class="vfloat-flower-center-dot" cx="32" cy="32" r="2.8"></circle>' +
        '</svg>'
      );
    }
    return '';
  }

  function renderLanterns() {
    var nav = document.querySelector('nav.navbar');
    if (!nav || !isValentineTheme()) {
      removeLayer('valentine-lanterns');
      return;
    }

    var layer = document.getElementById('valentine-lanterns');
    if (layer && layer.parentElement !== nav) {
      removeLayer('valentine-lanterns');
      layer = null;
    }

    if (!layer) {
      layer = document.createElement('div');
      layer.id = 'valentine-lanterns';
      layer.setAttribute('aria-hidden', 'true');
    }

    var durations = ['5.1s', '5.8s', '6.2s', '5.4s', '6.6s', '5.3s', '6.0s', '5.6s', '6.4s', '5.2s'];
    var delays = ['-1.1s', '-3.0s', '-2.2s', '-4.1s', '-1.8s', '-3.7s', '-2.8s', '-4.6s', '-0.9s', '-2.4s'];
    var scales = ['1.00', '0.94', '1.06', '0.97', '1.04', '0.92', '1.03', '0.96', '1.05', '0.95'];

    var items = durations.map(function(duration, idx) {
      var style =
        '--sway-duration:' + duration +
        ';--sway-delay:' + delays[idx] +
        ';--lantern-scale:' + scales[idx] + ';';
      return (
        '<span class="valentine-lantern" style="' + style + '">' +
          '<span class="valentine-cord"></span>' +
          '<span class="valentine-cap"></span>' +
          '<span class="valentine-lantern-body">' +
            '<span class="valentine-heart-emblem"></span>' +
          '</span>' +
          '<span class="valentine-tassel"></span>' +
        '</span>'
      );
    });

    layer.innerHTML = '<div class="valentine-lantern-track">' + items.join('') + '</div>';

    if (!layer.parentElement) {
      nav.appendChild(layer);
    }
  }

  function renderGreeting() {
    var nav = document.querySelector('nav.navbar');
    if (!nav || !isValentineTheme()) {
      removeLayer('valentine-greeting-banner');
      return;
    }

    var layer = document.getElementById('valentine-greeting-banner');
    if (layer && layer.parentElement !== nav) {
      removeLayer('valentine-greeting-banner');
      layer = null;
    }

    if (!layer) {
      layer = document.createElement('div');
      layer.id = 'valentine-greeting-banner';
      layer.setAttribute('aria-hidden', 'true');
    }

    layer.innerHTML =
      '<div class="valentine-greeting-inner">' +
        '<span class="valentine-greeting-text valentine-greeting-text-left">Happy Valentine&rsquo;s Day!</span>' +
        '<span class="valentine-greeting-spacer"></span>' +
        '<span class="valentine-greeting-text valentine-greeting-text-right">Be my Valentine!</span>' +
      '</div>';

    if (!layer.parentElement) {
      nav.appendChild(layer);
    }
  }

  function renderHeartFall() {
    var nav = document.querySelector('nav.navbar');
    if (!nav || !isValentineTheme() || isRspTrackerView()) {
      removeLayer('valentine-heartfall');
      return;
    }

    var layer = document.getElementById('valentine-heartfall');
    if (layer && layer.parentElement !== nav) {
      removeLayer('valentine-heartfall');
      layer = null;
    }

    if (!layer) {
      layer = document.createElement('div');
      layer.id = 'valentine-heartfall';
      layer.setAttribute('aria-hidden', 'true');
    }

    var prefersReducedMotion = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    var width = Math.max(320, nav.clientWidth || window.innerWidth || 1280);
    var navHeight = Math.max(56, nav.clientHeight || 60);
    var count = prefersReducedMotion
      ? Math.round(width / 180)
      : Math.round(width / 105);

    if (prefersReducedMotion) {
      count = Math.max(8, Math.min(14, count));
    } else {
      count = Math.max(10, Math.min(22, count));
    }

    var hearts = [];
    for (var i = 0; i < count; i += 1) {
      var left = random(-3, 103).toFixed(2);
      var size = random(10, 16).toFixed(2);
      var opacity = random(0.35, 0.82).toFixed(2);
      var duration = random(prefersReducedMotion ? 9 : 6, prefersReducedMotion ? 14 : 11).toFixed(2);
      var delay = (-random(0, parseFloat(duration))).toFixed(2);
      var drift = random(-26, 26).toFixed(2);
      var spinStart = random(-25, 25).toFixed(2);
      var spinEnd = (parseFloat(spinStart) + random(-120, 120)).toFixed(2);
      var drop = (navHeight + random(26, 44)).toFixed(2);

      var style =
        '--heart-left:' + left + '%;' +
        '--heart-size:' + size + 'px;' +
        '--heart-opacity:' + opacity + ';' +
        '--heart-duration:' + duration + 's;' +
        '--heart-delay:' + delay + 's;' +
        '--heart-drift:' + drift + 'px;' +
        '--heart-drop:' + drop + 'px;' +
        '--heart-rot-start:' + spinStart + 'deg;' +
        '--heart-rot-end:' + spinEnd + 'deg;';

      hearts.push(
        '<span class="valentine-falling-heart" style="' + style + '">' +
          '<svg class="vf-heart-shape" viewBox="0 0 24 22" aria-hidden="true" focusable="false">' +
            '<path class="vf-heart-core" d="M12 21s-1.1-.9-2.6-2.2C5.1 15.2 1 11.8 1 7.6 1 4.5 3.5 2 6.6 2c1.9 0 3.8.9 4.9 2.3C12.6 2.9 14.5 2 16.4 2 19.5 2 22 4.5 22 7.6c0 4.2-4.1 7.6-8.4 11.2C13.1 20.1 12 21 12 21z"></path>' +
            '<path class="vf-heart-gloss" d="M9.3 4.9c-.8-.7-2.2-.7-3 .1-.7.7-1 1.8-.7 2.8.2.5.8.8 1.3.6.5-.2.8-.8.6-1.3-.2-.4-.1-.9.2-1.2.3-.3.9-.3 1.3-.1.5.3 1.1.1 1.4-.3.3-.5.1-1.1-.3-1.4-.2-.1-.4-.2-.8-.4z"></path>' +
            '<path class="vf-heart-outline" d="M12 21s-1.1-.9-2.6-2.2C5.1 15.2 1 11.8 1 7.6 1 4.5 3.5 2 6.6 2c1.9 0 3.8.9 4.9 2.3C12.6 2.9 14.5 2 16.4 2 19.5 2 22 4.5 22 7.6c0 4.2-4.1 7.6-8.4 11.2C13.1 20.1 12 21 12 21z"></path>' +
          '</svg>' +
        '</span>'
      );
    }

    layer.innerHTML = hearts.join('');
    if (!layer.parentElement) {
      nav.insertBefore(layer, nav.firstChild);
    }
  }

  function renderFloatingSprites() {
    var body = document.body;
    if (!body || !isValentineTheme() || isRspTrackerView()) {
      removeLayer('valentine-floating-sprites');
      return;
    }

    var layer = document.getElementById('valentine-floating-sprites');
    if (layer && layer.parentElement !== body) {
      removeLayer('valentine-floating-sprites');
      layer = null;
    }

    if (!layer) {
      layer = document.createElement('div');
      layer.id = 'valentine-floating-sprites';
      layer.setAttribute('aria-hidden', 'true');
      body.appendChild(layer);
    }

    var sprites = [
      { type: 'heart', left: '8%', top: '54%', duration: '29s', delay: '-6s', size: '92px', opacity: '0.56' },
      { type: 'flower', left: '36%', top: '64%', duration: '27s', delay: '-3s', size: '88px', opacity: '0.5' },
      { type: 'heart', left: '74%', top: '46%', duration: '24s', delay: '-8s', size: '78px', opacity: '0.5' },
      { type: 'flower', left: '86%', top: '60%', duration: '31s', delay: '-11s', size: '84px', opacity: '0.46' },
      { type: 'heart', left: '57%', top: '40%', duration: '26s', delay: '-4s', size: '74px', opacity: '0.44' }
    ];

    var spriteMarkup = sprites.map(function(sprite) {
      var style =
        '--sprite-left:' + sprite.left + ';' +
        '--sprite-top:' + sprite.top + ';' +
        '--sprite-duration:' + sprite.duration + ';' +
        '--sprite-delay:' + sprite.delay + ';' +
        '--sprite-size:' + sprite.size + ';' +
        '--sprite-opacity:' + sprite.opacity + ';';

      return (
        '<span class="valentine-sprite valentine-sprite-' + sprite.type + '" style="' + style + '">' +
          floatingSpriteMarkup(sprite.type) +
        '</span>'
      );
    }).join('');

    layer.innerHTML = spriteMarkup;
  }

  function renderAll() {
    renderLanterns();
    renderGreeting();
    renderHeartFall();
    renderFloatingSprites();
  }

  var resizeTimer = null;
  function onResize() {
    if (resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function() {
      renderHeartFall();
    }, 120);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderAll);
  } else {
    renderAll();
  }

  window.addEventListener('resize', onResize, { passive: true });
})();
