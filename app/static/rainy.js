/**
 * Rainy Season Theme - Client-side Interactivity Script
 * Features drifting premium glassmorphic clouds, canvas-based falling raindrops,
 * and a param-driven realistic cloud-discharge lightning flicker sequence.
 * Includes automated background storms, hover drips, and decorative mascot wiggling.
 */
(function() {
  'use strict';

  function removeLayer(id) {
    var el = document.getElementById(id);
    if (el && el.parentNode) {
      el.parentNode.removeChild(el);
    }
  }

  var stormActive = false;

  function isRainyTheme() {
    var body = document.body;
    var isWeatherAuto = body && body.dataset && body.dataset.themeMode === 'weather_auto';
    return body && body.dataset && String(body.dataset.seasonTheme).toLowerCase() === 'rainy' && !isWeatherAuto;
  }

  function spawnDrip(x, y) {
    var deco = document.getElementById('rainy-navbar-deco');
    if (!deco) return;
    
    var drip = document.createElement('span');
    drip.className = 'rainy-drip';
    drip.style.left = x + 'px';
    drip.style.top = y + 'px';
    drip.style.animationDuration = (0.4 + Math.random() * 0.3) + 's';
    
    deco.appendChild(drip);
    
    setTimeout(function() {
      if (drip.parentNode) {
        drip.parentNode.removeChild(drip);
      }
    }, 700);
  }

  function initRainyTheme() {
    if (!isRainyTheme()) {
      removeLayer('rainy-navbar-deco');
      removeLayer('rainy-brand-mascot');
      return;
    }

    var nav = document.querySelector('nav.navbar');
    if (!nav) return;

    // 1. Inject Mascot (🐸 Frog) as a static/hover-wiggle decorative icon
    var brand = nav.querySelector('.navbar-brand');
    if (brand && !document.getElementById('rainy-brand-mascot')) {
      var mascot = document.createElement('span');
      mascot.id = 'rainy-brand-mascot';
      mascot.className = 'rainy-mascot';
      mascot.innerHTML = '🐸';
      brand.insertBefore(mascot, brand.firstChild);
    }

    // 2. Inject Deco wrapper & global SVG defs if missing
    var deco = document.getElementById('rainy-navbar-deco');
    if (!deco) {
      deco = document.createElement('div');
      deco.id = 'rainy-navbar-deco';
      deco.setAttribute('aria-hidden', 'true');
      
      deco.innerHTML = 
        '<svg style="position: absolute; width: 0; height: 0; overflow: hidden;" xmlns="http://www.w3.org/2000/svg">' +
          '<defs>' +
            '<linearGradient id="cloudGrad" x1="0%" y1="0%" x2="0%" y2="100%">' +
              '<stop offset="0%" stop-color="rgba(255, 255, 255, 0.36)" />' +
              '<stop offset="100%" stop-color="rgba(255, 255, 255, 0.08)" />' +
            '</linearGradient>' +
            '<linearGradient id="stormCloudGrad" x1="0%" y1="0%" x2="0%" y2="100%">' +
              '<stop offset="0%" stop-color="rgba(69, 85, 99, 0.85)" />' +
              '<stop offset="100%" stop-color="rgba(27, 38, 48, 0.7)" />' +
            '</linearGradient>' +
          '</defs>' +
        '</svg>';
      
      nav.appendChild(deco);
    }

    // Ensure lightning flash overlay exists
    var flashEl = document.getElementById('rainyLightningFlash');
    if (deco && !flashEl) {
      flashEl = document.createElement('div');
      flashEl.id = 'rainyLightningFlash';
      flashEl.className = 'rainy-lightning-flash';
      deco.appendChild(flashEl);
    }

    // 3. Inject Premium SVG Clouds
    if (deco.querySelectorAll('.rainy-navbar-cloud').length === 0) {
      var svgCloudMarkup = 
        '<svg viewBox="0 0 64 40" class="rainy-navbar-cloud-svg" style="width:100%; height:100%;" xmlns="http://www.w3.org/2000/svg">' +
          '<path d="M18 30h28a10 10 0 0 0 0-20 9.5 9.5 0 0 0-6.5 2.5 13 13 0 0 0-23.5 7.5 10 10 0 0 0 2 10z" fill="url(#cloudGrad)" />' +
        '</svg>';

      var delays = ['0s', '-14s', '-28s'];
      var tops = ['2px', '14px', '8px'];
      var scales = ['1.0', '0.7', '0.85'];
      var speeds = ['45s', '58s', '50s'];

      for (var i = 0; i < 3; i++) {
        var cloud = document.createElement('span');
        cloud.className = 'rainy-navbar-cloud';
        cloud.innerHTML = svgCloudMarkup;
        cloud.style.animationDelay = delays[i];
        cloud.style.animationDuration = speeds[i];
        cloud.style.top = tops[i];
        cloud.style.transform = 'scale(' + scales[i] + ')';
        deco.appendChild(cloud);
      }
    }

    // 4. Canvas rain overlay
    var canvas = document.getElementById('rainyNavbarCanvas');
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.id = 'rainyNavbarCanvas';
      canvas.className = 'rainy-navbar-canvas';
      deco.appendChild(canvas);
    }

    var ctx = canvas.getContext('2d');
    var width = canvas.width = nav.offsetWidth;
    var height = canvas.height = nav.offsetHeight;

    window.addEventListener('resize', function() {
      if (isRainyTheme() && canvas) {
        width = canvas.width = nav.offsetWidth;
        height = canvas.height = nav.offsetHeight;
      }
    });

    var particles = [];
    var maxParticles = 30;
    var stormTicks = 0;

    function initParticles() {
      particles = [];
      for (var j = 0; j < maxParticles; j++) {
        particles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vy: 2.2 + Math.random() * 2,
          len: 4 + Math.random() * 6,
          opacity: 0.12 + Math.random() * 0.18
        });
      }
    }

    /**
     * Executes a realistic high-frequency lightning discharge flicker sequence
     * @param {number} intensityFactor Scales peak brightness (0.0 to 1.0)
     * @param {number} durationFactor Scales delay speeds and decay duration
     * @param {function} callback Optional hook to execute after lightning finishes
     */
    function triggerRealisticFlash(intensityFactor, durationFactor, callback) {
      var clouds = deco.querySelectorAll('.rainy-navbar-cloud');
      
      // Step values represent: [brightness intensity, duration step in ms]
      var sequence = [
        [0.45 * intensityFactor, 40],
        [0.08 * intensityFactor, 40],
        [0.65 * intensityFactor, 50],
        [0.15 * intensityFactor, 40],
        [0.90 * intensityFactor, 90],
        [0.30 * intensityFactor, 70],
        [0.60 * intensityFactor, 60],
        [0.0, 750 * durationFactor] // analog decay segment
      ];

      // Shake clouds and shimmer border
      clouds.forEach(function(c) {
        c.classList.add('lightning-strike');
        c.classList.add('rumble');
      });
      nav.classList.add('navbar-rumbling');

      var idx = 0;
      function step() {
        if (!isRainyTheme() || !document.getElementById('rainyLightningFlash')) {
          return;
        }

        if (idx >= sequence.length) {
          clouds.forEach(function(c) {
            c.classList.remove('lightning-strike');
            if (!stormActive) {
              c.classList.remove('rumble');
            }
          });
          if (!stormActive) {
            nav.classList.remove('navbar-rumbling');
          }
          if (callback) callback();
          return;
        }

        var current = sequence[idx];
        var intensity = current[0];
        var ms = current[1];

        if (flashEl) {
          if (intensity === 0.0) {
            // Apply analog opacity release transition on final decay
            flashEl.style.transition = 'opacity ' + (0.6 * durationFactor) + 's ease-out';
            flashEl.classList.remove('active');
          } else {
            flashEl.style.transition = 'none';
            var posX = 15 + Math.random() * 70; // organic discharge path shift
            flashEl.style.background = 'radial-gradient(circle at ' + posX + '% 50%, rgba(255, 255, 255, ' + intensity + ') 0%, rgba(15, 188, 249, ' + (intensity * 0.45) + ') 60%, transparent 100%)';
            flashEl.classList.add('active');
          }
        }

        idx++;
        setTimeout(step, ms);
      }

      step();
    }

    // Triggers full thunderstorm downpour and clouds rumble automatically
    function triggerThunderstorm() {
      if (stormActive) return;
      stormActive = true;
      stormTicks = 200; // heavy rain duration

      var clouds = deco.querySelectorAll('.rainy-navbar-cloud');
      clouds.forEach(function(c) {
        c.classList.add('stormy');
      });

      var mascotEl = document.getElementById('rainy-brand-mascot');
      if (mascotEl) {
        mascotEl.innerHTML = '⚡🐸⚡';
      }

      // Fire realistic lightning flash sequence
      triggerRealisticFlash(1.0, 1.0, function() {
        setTimeout(function() {
          // Storm settles down back to a peaceful drizzle
          clouds.forEach(function(c) {
            c.classList.remove('stormy');
            c.classList.remove('rumble');
          });
          nav.classList.remove('navbar-rumbling');
          if (mascotEl) {
            mascotEl.innerHTML = '🐸';
          }
          stormActive = false;
        }, 2500);
      });
    }

    initParticles();

    function draw() {
      if (!isRainyTheme() || !document.getElementById('rainyNavbarCanvas')) return;

      ctx.clearRect(0, 0, width, height);

      var activeMax = maxParticles;
      if (stormTicks > 0) {
        activeMax = maxParticles + 60;
        stormTicks--;
      }

      while (particles.length < activeMax) {
        particles.push({
          x: Math.random() * width,
          y: -10,
          vy: (stormTicks > 0 ? 5.5 : 2.2) + Math.random() * 3,
          len: (stormTicks > 0 ? 8 : 4) + Math.random() * 6,
          opacity: (stormTicks > 0 ? 0.35 : 0.12) + Math.random() * 0.22
        });
      }

      if (particles.length > activeMax && stormTicks === 0) {
        particles = particles.slice(0, activeMax);
      }

      ctx.lineWidth = 1;
      for (var k = 0; k < particles.length; k++) {
        var p = particles[k];
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(p.x - 0.4, p.y + p.len);
        ctx.strokeStyle = 'rgba(15, 188, 249, ' + p.opacity + ')';
        ctx.stroke();

        p.y += p.vy;
        p.x -= 0.3;

        if (p.y > height) {
          p.y = -10;
          p.x = Math.random() * width;
          p.vy = (stormTicks > 0 ? 5.5 : 2.2) + Math.random() * 3;
          p.opacity = (stormTicks > 0 ? 0.35 : 0.12) + Math.random() * 0.22;
        }
      }

      requestAnimationFrame(draw);
    }

    requestAnimationFrame(draw);

    // 5. Background Schedulers (Ambient Flashes + Occasional Major Storms)
    function triggerAmbientLightning() {
      triggerRealisticFlash(0.55, 0.4);
    }

    function scheduleAmbientLightning() {
      var delay = 8000 + Math.random() * 14000;
      setTimeout(function() {
        if (!isRainyTheme() || !document.getElementById('rainyNavbarCanvas')) {
          return;
        }
        if (!stormActive) {
          triggerAmbientLightning();
        }
        scheduleAmbientLightning();
      }, delay);
    }

    function scheduleFullThunderstorm() {
      var delay = 40000 + Math.random() * 40000; // 40 to 80 seconds
      setTimeout(function() {
        if (!isRainyTheme() || !document.getElementById('rainyNavbarCanvas')) {
          return;
        }
        if (!stormActive) {
          triggerThunderstorm();
        }
        scheduleFullThunderstorm();
      }, delay);
    }

    scheduleAmbientLightning();
    scheduleFullThunderstorm();

    // 6. Connect Hover Drips
    var navLinks = nav.querySelectorAll('.nav-link, .btn-link');
    navLinks.forEach(function(link) {
      if (link.dataset.rainyHooked) return;
      link.dataset.rainyHooked = 'true';

      link.addEventListener('mouseenter', function() {
        if (!isRainyTheme()) return;
        var r = link.getBoundingClientRect();
        var nr = nav.getBoundingClientRect();
        var startX = r.left - nr.left;
        var startY = r.bottom - nr.top;
        var w = r.width;

        for (var d = 0; d < 4; d++) {
          (function(offset) {
            setTimeout(function() {
              if (isRainyTheme()) {
                spawnDrip(startX + offset, startY - 1);
              }
            }, d * 70);
          })(Math.random() * w);
        }
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initRainyTheme);
  } else {
    initRainyTheme();
  }

  window.initRainyTheme = initRainyTheme;
})();
