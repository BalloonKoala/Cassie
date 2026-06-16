/**
 * Pi kiosk: Chromium often opens at wrong size; nudge resize after window settles.
 */
(function () {
  'use strict';
  function nudge() {
    if (typeof window.dispatchEvent === 'function') {
      window.dispatchEvent(new Event('resize'));
    }
  }
  window.addEventListener('load', nudge);
  setTimeout(nudge, 250);
  setTimeout(nudge, 1000);
  setTimeout(nudge, 3000);
})();
