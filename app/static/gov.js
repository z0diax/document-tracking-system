/**
 * Government Official Theme - Dynamic Interaction script
 * Injects a premium official verification banner at the top of the viewport
 * and maintains a live, high-precision UTC/local date-time clock.
 */
(function() {
  'use strict';

  function removeElement(id) {
    var el = document.getElementById(id);
    if (el && el.parentNode) {
      el.parentNode.removeChild(el);
    }
  }

  function isGovTheme() {
    var body = document.body;
    return body && body.dataset && String(body.dataset.seasonTheme).toLowerCase() === 'gov';
  }

  function updateGovClock() {
    var clockEl = document.getElementById('govClock');
    if (!clockEl) return;
    
    var now = new Date();
    // Executive administrative format: e.g. "Thursday, Jul 2, 2026, 1:35:10 PM"
    var options = {
      weekday: 'long',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    };
    clockEl.textContent = now.toLocaleDateString('en-US', options);
  }

  function injectGovBanner() {
    if (!isGovTheme()) {
      removeElement('govHeaderBanner');
      document.body.classList.remove('gov-theme-active');
      return;
    }

    // Check if it already exists
    if (document.getElementById('govHeaderBanner')) {
      return;
    }

    var banner = document.createElement('div');
    banner.id = 'govHeaderBanner';
    banner.className = 'gov-header-banner';
    banner.setAttribute('aria-label', 'Official administrative portal banner');
    
    banner.innerHTML = 
      '<div class="gov-banner-left">' +
        '<i class="fas fa-university gov-banner-icon"></i>' +
        '<span class="gov-banner-text">Official Administrative Portal of the HR Document Tracking System</span>' +
      '</div>' +
      '<div class="gov-banner-right">' +
        '<span class="gov-clock-wrapper">' +
          '<i class="far fa-clock"></i> ' +
          '<span id="govClock" class="gov-clock">Loading Clock...</span>' +
        '</span>' +
        '<span class="gov-verified-badge">' +
          '<i class="fas fa-shield-alt"></i> SECURE PORTAL' +
        '</span>' +
      '</div>';

    document.body.insertBefore(banner, document.body.firstChild);
    document.body.classList.add('gov-theme-active');
    
    // Initial clock update and set interval
    updateGovClock();
    var clockInterval = setInterval(function() {
      if (!isGovTheme() || !document.getElementById('govClock')) {
        clearInterval(clockInterval);
        return;
      }
      updateGovClock();
    }, 1000);
  }

  // Run on DOMContentLoaded and check theme immediately
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectGovBanner);
  } else {
    injectGovBanner();
  }

  // Expose function in case theme switcher changes dataset theme dynamically before reloading
  window.initGovTheme = injectGovBanner;
})();
