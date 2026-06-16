(function () {
  'use strict';

  var params = new URLSearchParams(location.search);
  var deviceId = params.get('device') || 'pi-home';
  var token = params.get('token') || 'change-me';
  var server = params.get('server') || (location.protocol === 'file:' ? 'http://192.168.7.1:8780' : location.origin);
  var wsUrl = server.replace(/^http/, 'ws') + '/ws?device=' + encodeURIComponent(deviceId) +
    '&role=browser&token=' + encodeURIComponent(token);

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
  }

  function unlock() {
    lock.classList.add('hidden');
    if (window.cassieOrb) window.cassieOrb.setState('idle');
  }

  function handleCommand(cmd, payload) {
    if (cmd === 'apple_music') {
      var q = encodeURIComponent(payload.query || '');
      musicFrame.src = 'https://music.apple.com/us/search?term=' + q;
      musicLayer.classList.remove('hidden');
    }
    if (cmd === 'navigate' && payload.url) {
      location.href = payload.url;
    }
    if (cmd === 'cassie_home') {
      musicLayer.classList.add('hidden');
      musicFrame.src = 'about:blank';
    }
  }

  backBtn.addEventListener('click', function () {
    musicLayer.classList.add('hidden');
    musicFrame.src = 'about:blank';
  });

  // Laptop test: type passphrase or "Cassie what time is it" in console:
  // cassieTest("146 easy street")
  window.cassieTest = function (text) {
    var ws = new WebSocket(wsUrl);
    ws.onopen = function () { ws.send(JSON.stringify({ type: 'text', text: text })); };
  };

  connect();
})();
