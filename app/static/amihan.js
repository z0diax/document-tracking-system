/*
 * Amihan Bloom theme: light breeze/petal animation layer.
 * Uses CSS variables for randomized drift and duration.
 */
(function() {
  function rand(min, max) {
    return Math.random() * (max - min) + min;
  }

  function removeLayer(id) {
    var el = document.getElementById(id);
    if (!el) return;
    if (typeof el.remove === 'function') {
      el.remove();
    } else if (el.parentNode) {
      el.parentNode.removeChild(el);
    }
  }

  function initAmihanDecor() {
    var body = document.body;
    if (!body || !body.dataset) return;

    var theme = String(body.dataset.seasonTheme || '').toLowerCase();
    if (theme !== 'amihan') {
      removeLayer('amihan-petals');
      removeLayer('amihan-garland');
      return;
    }

    addAmihanGarland();

    var prefersReduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) {
      removeLayer('amihan-petals');
      return;
    }

    addPetals();
  }

  function addAmihanGarland() {
    var nav = document.querySelector('nav.navbar');
    if (!nav) return;

    var garland = document.getElementById('amihan-garland');
    if (garland && garland.parentElement !== nav) {
      removeLayer('amihan-garland');
      garland = null;
    }

    if (!garland) {
      garland = document.createElement('div');
      garland.id = 'amihan-garland';
      garland.setAttribute('aria-hidden', 'true');
    }

    var types = [
      'rose', 'sun', 'mint', 'sky', 'lilac',
      'sky', 'mint', 'sun', 'rose'
    ];

    garland.innerHTML = (
      '<div class="amihan-garland-track">' +
      types.map(function(type) {
        return '<span class="amihan-kite amihan-kite-' + type + '">' +
          '<span class="amihan-kite-body"></span>' +
          '<span class="amihan-kite-tail"></span>' +
          '</span>';
      }).join('') +
      '</div>'
    );

    if (!garland.parentElement) {
      if (nav.firstChild) {
        nav.insertBefore(garland, nav.firstChild);
      } else {
        nav.appendChild(garland);
      }
    }
  }

  function addPetals() {
    if (document.getElementById('amihan-petals')) return;

    var container = document.createElement('div');
    container.id = 'amihan-petals';
    container.setAttribute('aria-hidden', 'true');

    var count = Math.max(14, Math.min(30, Math.floor(window.innerWidth / 60)));
    var petalPalette = [
      { fill: 'var(--amihan-kite-rose)', edge: 'var(--amihan-kite-rose-tail)' },
      { fill: 'var(--amihan-kite-sun)', edge: 'var(--amihan-kite-sun-tail)' },
      { fill: 'var(--amihan-kite-mint)', edge: 'var(--amihan-kite-mint-tail)' },
      { fill: 'var(--amihan-kite-sky)', edge: 'var(--amihan-kite-sky-tail)' },
      { fill: 'var(--amihan-kite-lilac)', edge: 'var(--amihan-kite-lilac-tail)' }
    ];
    for (var i = 0; i < count; i++) {
      var wind = document.createElement('span');
      wind.className = 'amihan-petal-wind';
      var petal = document.createElement('span');
      petal.className = 'amihan-petal';
      var shape = document.createElement('span');
      shape.className = 'amihan-petal-shape';

      var left = rand(-5, 105);
      var width = rand(6, 11);
      var height = width * rand(0.55, 0.9);
      var delay = rand(0, 12);
      var baseDuration = rand(18, 30);
      var duration = Math.max(14, baseDuration - (width - 8) * 0.6);
      var spinDuration = rand(4.5, 9.5);
      var windDuration = rand(7, 13);
      var rotate = rand(0, 360);
      var wobble = rand(8, 18);
      var opacity = rand(0.3, 0.7);
      var scaleX = rand(0.85, 1.15);
      var scaleY = rand(0.85, 1.2);
      var originX = rand(20, 55);
      var originY = rand(40, 70);
      var drift1 = rand(-32, 32);
      var drift2 = drift1 + rand(-18, 18);
      var drift3 = drift2 + rand(-18, 18);
      var drift4 = drift3 + rand(-18, 18);
      var windPush = rand(12, 42);
      var windPull = -windPush * rand(0.6, 1);
      var color = petalPalette[Math.floor(rand(0, petalPalette.length))];

      wind.style.setProperty('--petal-left', left.toFixed(2) + '%');
      wind.style.setProperty('--petal-width', width.toFixed(2) + 'px');
      wind.style.setProperty('--petal-height', height.toFixed(2) + 'px');
      wind.style.setProperty('--petal-delay', delay.toFixed(2) + 's');
      wind.style.setProperty('--petal-duration', duration.toFixed(2) + 's');
      wind.style.setProperty('--petal-spin-duration', spinDuration.toFixed(2) + 's');
      wind.style.setProperty('--petal-wind-duration', windDuration.toFixed(2) + 's');
      wind.style.setProperty('--petal-rotate', rotate.toFixed(2) + 'deg');
      wind.style.setProperty('--petal-wobble', wobble.toFixed(2) + 'deg');
      wind.style.setProperty('--petal-opacity', opacity.toFixed(2));
      wind.style.setProperty('--petal-scale-x', scaleX.toFixed(2));
      wind.style.setProperty('--petal-scale-y', scaleY.toFixed(2));
      wind.style.setProperty('--petal-origin-x', originX.toFixed(2) + '%');
      wind.style.setProperty('--petal-origin-y', originY.toFixed(2) + '%');
      wind.style.setProperty('--petal-drift-1', drift1.toFixed(2) + 'px');
      wind.style.setProperty('--petal-drift-2', drift2.toFixed(2) + 'px');
      wind.style.setProperty('--petal-drift-3', drift3.toFixed(2) + 'px');
      wind.style.setProperty('--petal-drift-4', drift4.toFixed(2) + 'px');
      wind.style.setProperty('--petal-wind', windPush.toFixed(2) + 'px');
      wind.style.setProperty('--petal-wind-neg', windPull.toFixed(2) + 'px');
      wind.style.setProperty('--petal-color', color.fill);
      wind.style.setProperty('--petal-edge', color.edge);

      petal.appendChild(shape);
      wind.appendChild(petal);
      container.appendChild(wind);
    }

    document.body.appendChild(container);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAmihanDecor);
  } else {
    initAmihanDecor();
  }
})();
