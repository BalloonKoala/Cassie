/**
 * WebSocket client — connects to Cassie backend for state + amplitude.
 */
(function () {
  'use strict';

  var WS_URL = 'ws://127.0.0.1:8765';
  var reconnectDelay = 2000;

  function connect() {
    var ws;
    try {
      ws = new WebSocket(WS_URL);
    } catch (e) {
      setTimeout(connect, reconnectDelay);
      return;
    }

    ws.onopen = function () {
      console.log('[cassie] WebSocket connected');
    };

    ws.onmessage = function (event) {
      try {
        var msg = JSON.parse(event.data);
        if (msg.type === 'state' && typeof window.setSphereState === 'function') {
          window.setSphereState(msg.state);
        }
        if (msg.type === 'amplitude' || (msg.type === 'state' && msg.amplitude != null)) {
          var amp = msg.amplitude != null ? msg.amplitude : 0;
          if (typeof window.setMicLevel === 'function') {
            window.setMicLevel(amp);
          }
          if (typeof window.setSphereAmplitude === 'function') {
            window.setSphereAmplitude(amp);
          }
        }
      } catch (e) {
        console.warn('[cassie] Bad WS message', e);
      }
    };

    ws.onclose = function () {
      setTimeout(connect, reconnectDelay);
    };

    ws.onerror = function () {
      ws.close();
    };
  }

  connect();
})();
