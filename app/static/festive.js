/**
 * Festive Theme (festive) - Client-side Interactivity Script.
 * Dynamically injects swaying Philippine festival banderitas (bunting) into the navbar
 * and floats colorful falling confetti across the background.
 */
(function() {
  function removeBanderitas() {
    var container = document.getElementById('festive-banderitas');
    if (container) {
      if (typeof container.remove === 'function') {
        container.remove();
      } else if (container.parentNode) {
        container.parentNode.removeChild(container);
      }
    }
  }

  function removeBottomDeco() {
    var container = document.getElementById('festive-bottom-deco');
    if (container) {
      if (typeof container.remove === 'function') {
        container.remove();
      } else if (container.parentNode) {
        container.parentNode.removeChild(container);
      }
    }
  }

  function removeConfetti() {
    var container = document.getElementById('festive-confetti');
    if (container) {
      if (typeof container.remove === 'function') {
        container.remove();
      } else if (container.parentNode) {
        container.parentNode.removeChild(container);
      }
    }
  }

  function addConfetti() {
    if (document.getElementById('festive-confetti')) return;

    var nav = document.querySelector('nav.navbar');
    if (!nav) return;

    var container = document.createElement('div');
    container.id = 'festive-confetti';
    container.setAttribute('aria-hidden', 'true');

    var prefersReduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;

    // Responsive confetti density
    var count = Math.max(16, Math.min(45, Math.floor(window.innerWidth / 40)));
    var colors = ['#ffd700', '#00e5ff', '#ff3d00', '#ff007f', '#00e676', '#a020f0'];
    var shapes = ['is-square', 'is-diamond', 'is-circle', 'is-star'];

    for (var i = 0; i < count; i++) {
      var piece = document.createElement('span');
      piece.className = 'festive-confetti-piece ' + shapes[Math.floor(Math.random() * shapes.length)];
      
      var left = Math.random() * 100;
      var size = Math.random() * 6 + 4; // slightly smaller: 4px to 10px
      var delay = Math.random() * -4; // start immediately at random height offset
      var duration = Math.random() * 2 + 1.5; // faster fall for navbar: 1.5s to 3.5s
      var opacity = Math.random() * 0.45 + 0.3; // 0.3 to 0.75

      piece.style.left = left + '%';
      piece.style.width = size + 'px';
      piece.style.height = size + 'px';
      piece.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
      piece.style.animationDelay = delay + 's';
      piece.style.animationDuration = duration + 's';
      piece.style.opacity = opacity;

      container.appendChild(piece);
    }

    nav.appendChild(container);
  }

  function initFestiveTheme() {
    var body = document.body;
    if (!body) return;

    var theme = String(body.dataset.seasonTheme || '').toLowerCase();
    if (theme !== 'festive') {
      removeBanderitas();
      removeBottomDeco();
      removeConfetti();
      return;
    }

    // Initialize banderitas
    if (!document.getElementById('festive-banderitas')) {
      var nav = document.querySelector('nav.navbar');
      if (nav) {
        var container = document.createElement('div');
        container.id = 'festive-banderitas';
        container.setAttribute('aria-hidden', 'true');

        var width = window.innerWidth;
        var flagCount = Math.floor(width / 16) + 2;

        var flagsHTML = '';
        for (var i = 0; i < flagCount; i++) {
          flagsHTML += '<span class="banderitas-flag"></span>';
        }
        container.innerHTML = flagsHTML;
        nav.appendChild(container);
      }
    }

    // Initialize bottom decorations (twinkling lights and kiping leaves)
    if (!document.getElementById('festive-bottom-deco')) {
      var nav = document.querySelector('nav.navbar');
      if (nav) {
        var container = document.createElement('div');
        container.id = 'festive-bottom-deco';
        container.setAttribute('aria-hidden', 'true');

        var width = window.innerWidth;
        // Place an element every 24px
        var elementCount = Math.floor(width / 24) + 2;

        var decoHTML = '';
        for (var i = 0; i < elementCount; i++) {
          if (i % 2 === 0) {
            decoHTML += '<span class="festive-light-bulb"></span>';
          } else {
            decoHTML += '<span class="festive-kiping-leaf"></span>';
          }
        }
        container.innerHTML = decoHTML;
        nav.appendChild(container);
      }
    }

    // Initialize falling confetti particles
    addConfetti();
  }

  // Set up observer to watch for theme changes on body
  function setupThemeObserver() {
    var observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        if (mutation.type === 'attributes' && mutation.attributeName === 'data-season-theme') {
          initFestiveTheme();
        }
      });
    });

    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ['data-season-theme']
    });
  }

  // Handle window resizing to adjust elements
  var resizeTimeout;
  window.addEventListener('resize', function() {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(function() {
      var body = document.body;
      if (body && String(body.dataset.seasonTheme || '').toLowerCase() === 'festive') {
        removeBanderitas();
        removeBottomDeco();
        removeConfetti();
        initFestiveTheme();
      }
    }, 250);
  });

  // Initialize on load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      initFestiveTheme();
      setupThemeObserver();
    });
  } else {
    initFestiveTheme();
    setupThemeObserver();
  }
})();
