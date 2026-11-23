/* Live notification badge + toast over WebSocket, with polling fallback. */
(function () {
  if (document.body.dataset.auth !== '1') return;
  var badges = function () { return document.querySelectorAll('[data-notif-badge]'); };
  function setBadge(n) {
    badges().forEach(function (b) { b.textContent = n; b.classList.toggle('hidden', !n); });
  }
  function toast(title, url) {
    var box = document.getElementById('live-toasts');
    if (!box) { box = document.createElement('div'); box.id = 'live-toasts'; box.className = 'fixed top-4 right-4 z-50 flex w-[calc(100%-2rem)] max-w-sm flex-col gap-2'; document.body.appendChild(box); }
    var t = document.createElement('a'); t.className = 'toast'; t.href = url; t.textContent = title;
    box.appendChild(t); setTimeout(function () { t.style.opacity = '0'; setTimeout(function () { t.remove(); }, 300); }, 6000);
  }
  // bell dropdown
  var bell = document.getElementById('bell'), menu = document.getElementById('notif-menu');
  function loadMenu() { fetch('/app/notifications/preview/', { credentials: 'same-origin' }).then(function (r) { return r.text(); }).then(function (h) { menu.innerHTML = h; var f = menu.querySelector('[data-markall]'); if (f) f.addEventListener('submit', function (e) { e.preventDefault(); fetch(f.action, { method: 'POST', credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch', 'X-CSRFToken': f.querySelector('[name=csrfmiddlewaretoken]').value } }).then(function () { setBadge(0); loadMenu(); }); }); }); }
  if (bell && menu) {
    bell.addEventListener('click', function (e) { e.stopPropagation(); var open = menu.classList.toggle('hidden') === false; bell.setAttribute('aria-expanded', open); if (open) loadMenu(); });
    document.addEventListener('click', function (e) { if (!menu.contains(e.target)) { menu.classList.add('hidden'); bell.setAttribute('aria-expanded', 'false'); } });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') menu.classList.add('hidden'); });
  }
  // socket with backoff, then polling
  var tries = 0, pollTimer = null;
  function poll() { if (pollTimer) return; pollTimer = setInterval(function () { fetch('/app/notifications/count/', { credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (j) { setBadge(j.unread); }).catch(function () {}); }, 30000); }
  function connect() {
    if (!('WebSocket' in window)) { poll(); return; }
    var ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/notifications/');
    ws.onopen = function () { tries = 0; };
    ws.onmessage = function (e) {
      var d = JSON.parse(e.data);
      if (d.type === 'notification') {
        setBadge(d.unread);
        if (!/\/app\/messages\/\d+\//.test(location.pathname)) toast(d.title, d.url);
        if (menu && !menu.classList.contains('hidden')) loadMenu();
      }
    };
    ws.onclose = function (e) { if (e.code === 4401) return; tries++; if (tries > 3) { poll(); return; } setTimeout(connect, Math.min(1000 * Math.pow(2, tries), 15000)); };
  }
  connect();
})();
