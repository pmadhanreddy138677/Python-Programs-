(function () {
  // Replaces inline handlers (blocked by our Content Security Policy)
  document.addEventListener('submit', function (e) {
    var f = e.target, msg = f.getAttribute && f.getAttribute('data-confirm');
    if (msg && !window.confirm(msg)) { e.preventDefault(); e.stopImmediatePropagation(); }
  }, true);
  document.addEventListener('change', function (e) { if (e.target.hasAttribute && e.target.hasAttribute('data-autosubmit') && e.target.form) e.target.form.submit(); });
  document.addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('[data-back]'); if (b) { e.preventDefault(); history.back(); } });
  // Theme toggle (initial theme is applied by an inline script in <head> to avoid flashing)
  document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var dark = document.documentElement.classList.toggle('dark');
      try { localStorage.setItem('circliq-theme', dark ? 'dark' : 'light'); } catch (e) {}
    });
  });
  // Show/hide password
  document.querySelectorAll('[data-toggle-password]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var input = document.getElementById(btn.dataset.togglePassword);
      var show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      btn.textContent = show ? 'Hide' : 'Show';
    });
  });
  // Auto-dismiss toasts
  document.querySelectorAll('.toast').forEach(function (t) {
    setTimeout(function () { t.style.opacity = '0'; setTimeout(function () { t.remove(); }, 300); }, 6000);
  });
  // Mobile drawer
  var drawer = document.getElementById('drawer');
  document.querySelectorAll('[data-drawer-open]').forEach(function (b) { b.addEventListener('click', function () { drawer.classList.remove('hidden'); }); });
  document.querySelectorAll('[data-drawer-close]').forEach(function (b) { b.addEventListener('click', function () { drawer.classList.add('hidden'); }); });
})();

(function () {
  // Scroll reveal
  var els = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { threshold: 0.12 });
    els.forEach(function (el) { io.observe(el); });
  } else { els.forEach(function (el) { el.classList.add('in'); }); }

  // Count-up numbers
  document.querySelectorAll('[data-count-up]').forEach(function (el) {
    var end = parseInt(el.dataset.countUp, 10) || 0, suffix = el.dataset.suffix || '', t0 = null;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || end === 0) { el.textContent = end + suffix; return; }
    function step(ts) { t0 = t0 || ts; var p = Math.min((ts - t0) / 700, 1); el.textContent = Math.round(end * p) + suffix; if (p < 1) requestAnimationFrame(step); }
    requestAnimationFrame(step);
  });

  // Reactions / bookmarks without a page reload (forms still work without JS)
  document.addEventListener('submit', function (e) {
    var f = e.target;
    if (!f.matches || !f.matches('[data-toggle]')) return;
    e.preventDefault();
    var btn = f.querySelector('button');
    fetch(f.action, { method: 'POST', credentials: 'same-origin',
      headers: { 'X-Requested-With': 'fetch', 'X-CSRFToken': f.querySelector('[name=csrfmiddlewaretoken]').value } })
      .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(function (d) {
        btn.classList.toggle('on', d.active);
        var c = f.querySelector('[data-count]'); if (c) c.textContent = d.count;
        btn.classList.remove('pop'); void btn.offsetWidth; btn.classList.add('pop');
      })
      .catch(function () { f.submit(); });
  });

  // Copy link buttons
  document.querySelectorAll('[data-copy]').forEach(function (b) {
    b.addEventListener('click', function () {
      var url = location.origin + b.dataset.copy, label = b.querySelector('span');
      (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(function () {
        if (label) { var old = label.textContent; label.textContent = 'Copied!'; setTimeout(function () { label.textContent = old; }, 1500); }
      }).catch(function () { window.prompt('Copy this link', url); });
    });
  });

  // Show reply form
  document.querySelectorAll('[data-reply-toggle]').forEach(function (b) {
    b.addEventListener('click', function () { document.getElementById(b.dataset.replyToggle).classList.toggle('hidden'); });
  });
})();

(function () {
  // Kanban drag & drop (buttons on each card work without JS)
  var dragging = null;
  function csrf() { var m = document.querySelector('meta[name=csrf-token]'); if (m && m.content) return m.content; var i = document.querySelector('[name=csrfmiddlewaretoken]'); return i ? i.value : ''; }
  document.addEventListener('dragstart', function (e) {
    var c = e.target.closest && e.target.closest('[data-task]'); if (!c) return;
    dragging = c; c.classList.add('drag'); e.dataTransfer.effectAllowed = 'move'; try { e.dataTransfer.setData('text/plain', c.dataset.task); } catch (x) {}
  });
  document.addEventListener('dragend', function () { if (dragging) dragging.classList.remove('drag'); document.querySelectorAll('.kb-drop.over').forEach(function (d) { d.classList.remove('over'); }); dragging = null; });
  document.addEventListener('dragover', function (e) { var d = e.target.closest && e.target.closest('[data-drop]'); if (d && dragging) { e.preventDefault(); d.classList.add('over'); } });
  document.addEventListener('dragleave', function (e) { var d = e.target.closest && e.target.closest('[data-drop]'); if (d) d.classList.remove('over'); });
  document.addEventListener('drop', function (e) {
    var d = e.target.closest && e.target.closest('[data-drop]'); if (!d || !dragging) return;
    e.preventDefault(); d.classList.remove('over');
    var card = dragging, fd = new FormData(); fd.append('status', d.dataset.drop);
    d.appendChild(card);
    fetch(card.dataset.move, { method: 'POST', body: fd, credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch', 'X-CSRFToken': csrf() } })
      .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(function (j) {
        document.querySelectorAll('[data-progress-bar]').forEach(function (b) { b.style.width = j.progress + '%'; });
        document.querySelectorAll('[data-progress-text]').forEach(function (t) { t.textContent = j.progress + '%'; });
        document.querySelectorAll('[data-drop]').forEach(function (z) { var n = z.parentElement.querySelector('[data-colcount]'); if (n) n.textContent = z.querySelectorAll('[data-task]').length; });
        card.querySelectorAll('form[data-movebtns]').forEach(function (f) { f.remove(); });
      })
      .catch(function () { location.reload(); });
  });
})();
