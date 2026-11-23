/* Circliq chat: WebSocket first, automatic reconnect, HTTP polling fallback. Message text is always inserted with textContent (never innerHTML). */
(function () {
  var box = document.getElementById('msgs'); if (!box) return;
  var form = document.getElementById('chat-form'), input = document.getElementById('chat-input'), pill = document.getElementById('conn'), typing = document.getElementById('typing');
  var me = parseInt(box.dataset.me, 10), isGroup = box.dataset.group === '1', lastId = parseInt(box.dataset.last, 10) || 0;
  var seen = {}; box.querySelectorAll('[data-id]').forEach(function (m) { seen[m.dataset.id] = true; });
  var ws = null, tries = 0, pollTimer = null, typingTimer = null, lastTypingSent = 0;
  function csrf() { var f = form && form.querySelector('[name=csrfmiddlewaretoken]'); return f ? f.value : ''; }
  function status(text, cls) { if (pill) { pill.textContent = text; pill.className = 'conn-pill ' + cls; } }
  function scrollDown() { box.scrollTop = box.scrollHeight; }
  function dayLabel(d) { return d.toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short' }); }
  var lastDay = (function () { var s = box.querySelectorAll('.sep'); return s.length ? s[s.length - 1].textContent : ''; })();

  function addMessage(m) {
    if (seen[m.id]) return; seen[m.id] = true; lastId = Math.max(lastId, m.id);
    var empty = document.getElementById('empty-chat'); if (empty) empty.remove();
    var d = new Date(m.created_at), label = dayLabel(d);
    if (label !== lastDay) { var sep = document.createElement('div'); sep.className = 'sep'; sep.textContent = label; box.appendChild(sep); lastDay = label; }
    var el = document.createElement('div'); el.className = 'msg ' + (m.sender_id === me ? 'me' : 'them'); el.dataset.id = m.id;
    if (isGroup && m.sender_id !== me) { var w = document.createElement('span'); w.className = 'who'; w.textContent = m.sender; el.appendChild(w); }
    var lines = String(m.body).split('\n');
    lines.forEach(function (ln, i) { if (i) el.appendChild(document.createElement('br')); el.appendChild(document.createTextNode(ln)); });
    var t = document.createElement('time'); t.textContent = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }); el.appendChild(t);
    var nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 160 || m.sender_id === me;
    box.appendChild(el); if (nearBottom) scrollDown();
    if (m.sender_id !== me && !document.hidden) markRead();
  }

  function markRead() {
    if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: 'read' }));
    else fetch(box.dataset.read, { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': csrf() } });
  }

  function startPolling() {
    if (pollTimer) return; status('Live updates paused · checking every few seconds', 'poll');
    pollTimer = setInterval(function () {
      fetch(box.dataset.poll + '?after=' + lastId, { credentials: 'same-origin' }).then(function (r) { return r.json(); })
        .then(function (j) { j.messages.forEach(addMessage); }).catch(function () {});
    }, 4000);
  }
  function stopPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } }

  function catchUp() { // fetch anything missed while the socket was down
    fetch(box.dataset.poll + '?after=' + lastId, { credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (j) { j.messages.forEach(addMessage); }).catch(function () {});
  }

  function connect() {
    if (!('WebSocket' in window)) { startPolling(); return; }
    ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + box.dataset.ws);
    ws.onopen = function () { var was = tries > 0; tries = 0; stopPolling(); status('Live', 'on'); if (was) catchUp(); };
    ws.onmessage = function (e) {
      var d = JSON.parse(e.data);
      if (d.type === 'message') addMessage(d.message);
      else if (d.type === 'typing') { typing.textContent = d.name + ' is typing…'; clearTimeout(typingTimer); typingTimer = setTimeout(function () { typing.textContent = ''; }, 2500); }
      else if (d.type === 'error') { typing.textContent = d.message; setTimeout(function () { typing.textContent = ''; }, 4000); }
    };
    ws.onclose = function (e) {
      if (e.code === 4401 || e.code === 4403) { status('Not available', 'off'); return; }
      tries++; status('Reconnecting…', 'off');
      if (tries >= 3) startPolling();
      setTimeout(connect, Math.min(1000 * Math.pow(2, tries), 15000));
    };
  }

  function send() {
    var body = input.value.trim(); if (!body) return;
    input.value = ''; input.style.height = 'auto';
    if (ws && ws.readyState === 1) { ws.send(JSON.stringify({ type: 'message', body: body })); return; }
    var fd = new FormData(); fd.append('body', body);   // WebSocket is down: send over HTTP instead
    fetch(box.dataset.send, { method: 'POST', body: fd, credentials: 'same-origin', headers: { 'X-CSRFToken': csrf() } })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (x) { if (x.ok) addMessage(x.j.message); else { typing.textContent = x.j.error || 'Could not send.'; input.value = body; } })
      .catch(function () { typing.textContent = 'Could not send. Check your connection.'; input.value = body; });
  }

  if (form) {
    form.addEventListener('submit', function (e) { e.preventDefault(); send(); });
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });
    input.addEventListener('input', function () {
      input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 128) + 'px';
      var now = Date.now(); if (ws && ws.readyState === 1 && now - lastTypingSent > 2000) { lastTypingSent = now; ws.send(JSON.stringify({ type: 'typing' })); }
    });
  }
  document.addEventListener('visibilitychange', function () { if (!document.hidden) markRead(); });
  scrollDown(); connect();
})();
