(function () {
  'use strict';

  var defaults = window.CASSIE_DEFAULTS || {};
  var params = new URLSearchParams(location.search);
  var deviceId = params.get('device') || defaults.device || 'pi-home';
  var token = params.get('token') || defaults.token || 'change-me';

  function resolveServer() {
    if (params.get('server')) return params.get('server');
    if (defaults.brainServer) return defaults.brainServer;
    if (location.protocol === 'file:') return 'http://127.0.0.1:8780';
    var host = location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') return location.origin;
    // Firebase Hosting serves static files only — brain runs elsewhere until Cloud Run is wired
    return '';
  }

  var server = resolveServer();
  if (!server) {
    document.getElementById('lock-msg').textContent =
      'Set brain server: add ?server=wss://YOUR_SERVER to the URL';
    if (window.cassieOrb) window.cassieOrb.setState('locked');
    return;
  }

  var wsBase = server.replace(/^http:\/\//i, 'ws://').replace(/^https:\/\//i, 'wss://');
  var wsUrl = wsBase.replace(/\/$/, '') + '/ws?device=' + encodeURIComponent(deviceId) +
    '&role=browser&token=' + encodeURIComponent(token);

  if (location.protocol === 'https:' && wsUrl.indexOf('ws://') === 0) {
    lockMsg.textContent = 'Brain needs wss:// (HTTPS). Use Cloudflare tunnel or Cloud Run.';
    if (window.cassieOrb) window.cassieOrb.setState('locked');
    return;
  }

  var lock = document.getElementById('lock');
  var lockMsg = document.getElementById('lock-msg');
  var musicLayer = document.getElementById('music-layer');
  var musicFrame = document.getElementById('music-frame');
  var backBtn = document.getElementById('back-cassie');

  function connect() {
    var ws = new WebSocket(wsUrl);
    ws.onopen = function () {
      lockMsg.textContent = 'Say the passphrase…';
      if (window.cassieOrb) window.cassieOrb.setState('locked');
    };
    ws.onmessage = function (ev) {
      var msg = JSON.parse(ev.data);
      if (msg.type === 'hello' && msg.unlocked) unlock();
      if (msg.type === 'unlock') unlock();
      if (msg.type === 'state' && window.cassieOrb) window.cassieOrb.setState(msg.state);
      if (msg.type === 'amplitude' && window.cassieOrb) window.cassieOrb.setAmplitude(msg.amplitude);
      if (msg.type === 'command') handleCommand(msg.cmd, msg.payload || {});
      if (msg.type === 'reply') console.log('[cassie]', msg.text);
    };
    ws.onclose = function () { setTimeout(connect, 2000); };
    ws.onerror = function () { lockMsg.textContent = 'Cannot reach Cassie brain at ' + server; };
  }

  function unlock() {
    lock.classList.add('hidden');
    if (window.cassieOrb) window.cassieOrb.setState('idle');
  }

  function handleCommand(cmd, payload) {
    if (cmd === 'apple_music') {
      musicFrame.src = 'https://music.apple.com/us/search?term=' + encodeURIComponent(payload.query || '');
      musicLayer.classList.remove('hidden');
    }
    if (cmd === 'navigate' && payload.url) location.href = payload.url;
    if (cmd === 'cassie_home') {
      musicLayer.classList.add('hidden');
      musicFrame.src = 'about:blank';
    }
  }

  backBtn.addEventListener('click', function () {
    musicLayer.classList.add('hidden');
    musicFrame.src = 'about:blank';
  });

  window.cassieTest = function (text) {
    var ws = new WebSocket(wsUrl);
    ws.onopen = function () { ws.send(JSON.stringify({ type: 'text', text: text })); };
  };

  connect();
})();
