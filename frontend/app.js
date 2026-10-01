/* TasteLoop Agent frontend — no frameworks, no external requests except the backend. */
(function () {
  'use strict';

  var state = {
    mood: null,
    view: 'grounded',      // 'grounded' | 'baseline'
    data: null,            // last /api/plan response
    loading: false
  };

  var el = {
    week: document.getElementById('week-text'),
    city: document.getElementById('city-input'),
    chips: document.getElementById('mood-chips'),
    planBtn: document.getElementById('plan-btn'),
    warning: document.getElementById('warning'),
    error: document.getElementById('error'),
    badge: document.getElementById('mode-badge'),
    modeLabel: document.getElementById('mode-label'),
    signals: document.getElementById('signals'),
    signalsMood: document.getElementById('signals-mood'),
    signalsTags: document.getElementById('signals-tags'),
    viewBar: document.getElementById('view-bar'),
    baselineCaption: document.getElementById('baseline-caption'),
    results: document.getElementById('results')
  };

  /* ---------- helpers ---------- */
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function cap(s) {
    s = String(s == null ? '' : s);
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  /* ---------- mode badge ---------- */
  function setBadge(mode) {
    el.badge.classList.remove('live', 'mock');
    if (mode === 'live') {
      el.badge.classList.add('live');
      el.modeLabel.textContent = 'LIVE \u2014 Qloo Taste API';
    } else if (mode === 'mock') {
      el.badge.classList.add('mock');
      el.modeLabel.textContent = 'DEMO DATA \u2014 connect Qloo API key for live results';
    } else {
      el.modeLabel.textContent = 'Backend unreachable';
    }
  }

  async function checkHealth() {
    try {
      var r = await fetch('/api/health', { cache: 'no-store' });
      if (!r.ok) throw new Error('bad status');
      var h = await r.json();
      setBadge(h && h.mode);
    } catch (e) {
      setBadge(null);
    }
  }

  /* ---------- mood chips ---------- */
  el.chips.addEventListener('click', function (e) {
    var btn = e.target.closest('.chip');
    if (!btn) return;
    var chips = el.chips.querySelectorAll('.chip');
    chips.forEach(function (c) {
      c.classList.remove('selected');
      c.setAttribute('aria-checked', 'false');
    });
    if (state.mood === btn.dataset.mood) {
      state.mood = null; // toggle off
    } else {
      state.mood = btn.dataset.mood;
      btn.classList.add('selected');
      btn.setAttribute('aria-checked', 'true');
    }
  });

  /* ---------- view toggle ---------- */
  el.viewBar.addEventListener('click', function (e) {
    var btn = e.target.closest('.toggle-btn');
    if (!btn) return;
    state.view = btn.dataset.view;
    el.viewBar.querySelectorAll('.toggle-btn').forEach(function (b) {
      var on = b === btn;
      b.classList.toggle('active', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    el.baselineCaption.hidden = state.view !== 'baseline';
    if (state.data) renderResults();
  });

  /* ---------- card rendering ---------- */
  function sourceLabel(source) {
    if (source === 'qloo') return 'via Qloo Taste API';
    if (source === 'mock') return 'demo dataset';
    if (source === 'baseline') return 'simulated baseline';
    return esc(source || '');
  }

  function cardHTML(c) {
    var affinity = '';
    if (c.affinity != null && !isNaN(Number(c.affinity))) {
      var pct = Math.round(Number(c.affinity) * 100);
      affinity =
        '<div class="affinity">' +
          '<div class="affinity-top"><span>taste affinity</span><span class="val">' + pct + '%</span></div>' +
          '<div class="affinity-track"><div class="affinity-fill" style="width:' + pct + '%"></div></div>' +
        '</div>';
    }
    var tags = '';
    var list = Array.isArray(c.tags) ? c.tags.slice(0, 4) : [];
    if (list.length) {
      tags = '<div class="tags">' + list.map(function (t) {
        return '<span class="tag">' + esc(t) + '</span>';
      }).join('') + '</div>';
    }
    return '<article class="card">' +
      '<h3 class="card-name">' + esc(c.name) + '</h3>' +
      '<p class="card-category">' + esc(c.category) + '</p>' +
      affinity + tags +
      '<p class="why"><strong>Why it fits:</strong> ' + esc(c.why) + '</p>' +
      '<p class="source-line">' + esc(sourceLabel(c.source)) + '</p>' +
    '</article>';
  }

  var SECTION_ORDER = [
    ['dining', 'Dining'],
    ['music', 'Music'],
    ['film', 'Film'],
    ['going_out', 'Going out']
  ];

  function renderResults() {
    if (!state.data) return;
    var block = state.view === 'baseline' ? state.data.baseline : state.data.plan;
    var html = '';
    SECTION_ORDER.forEach(function (pair) {
      var key = pair[0], title = pair[1];
      var cards = (block && Array.isArray(block[key])) ? block[key] : [];
      html += '<section class="plan-section"><h2>' + esc(title) + '</h2><div class="cards">';
      if (!cards.length) {
        html += '<p class="source-line">No picks in this section.</p>';
      } else {
        html += cards.map(cardHTML).join('');
      }
      html += '</div></section>';
    });
    el.results.innerHTML = html;
    el.results.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function renderSignals() {
    var s = state.data && state.data.signals;
    if (!s) { el.signals.hidden = true; return; }
    var tags = [];
    if (Array.isArray(s.tag_names)) tags = tags.concat(s.tag_names);
    if (Array.isArray(s.keywords)) tags = tags.concat(s.keywords);
    el.signalsMood.textContent = s.mood ? cap(s.mood) : '';
    el.signalsMood.style.display = s.mood ? '' : 'none';
    el.signalsTags.innerHTML = tags.slice(0, 10).map(function (t) {
      return '<span class="pill">' + esc(t) + '</span>';
    }).join('');
    el.signals.hidden = false;
  }

  function showSkeleton() {
    var html = '';
    SECTION_ORDER.forEach(function (pair) {
      html += '<section class="plan-section skeleton"><h2>' + esc(pair[1]) + '</h2><div class="cards">';
      for (var i = 0; i < 2; i++) {
        html += '<article class="card"><div class="skel" style="height:20px;width:70%"></div>' +
          '<div class="skel" style="height:12px;width:40%"></div>' +
          '<div class="skel" style="height:60px"></div></article>';
      }
      html += '</div></section>';
    });
    el.results.innerHTML = html;
  }

  function showError(msg) {
    el.results.innerHTML =
      '<div class="empty-state"><span class="glyph">\uD83D\uDCE1</span>' +
      '<h2>Couldn\u2019t reach the planner</h2>' +
      '<p>' + esc(msg) + '</p></div>';
  }

  /* ---------- submit ---------- */
  function setLoading(on) {
    state.loading = on;
    el.planBtn.disabled = on;
    el.planBtn.innerHTML = on
      ? '<span class="spinner" aria-hidden="true"></span> Planning your week\u2026'
      : 'Plan my week';
  }

  async function submit() {
    if (state.loading) return;
    el.warning.hidden = true;
    el.error.hidden = true;
    setLoading(true);
    showSkeleton();
    try {
      var r = await fetch('/api/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          week_text: el.week.value.trim(),
          mood: state.mood,
          city: el.city.value.trim()
        })
      });
      if (!r.ok) throw new Error('server responded ' + r.status);
      var data = await r.json();
      if (!data || data.success !== true) {
        throw new Error('planner returned an error');
      }
      state.data = data;
      state.view = 'grounded';
      el.viewBar.querySelectorAll('.toggle-btn').forEach(function (b) {
        var on = b.dataset.view === 'grounded';
        b.classList.toggle('active', on);
        b.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      el.baselineCaption.hidden = true;
      el.viewBar.hidden = false;
      if (data.warning) {
        el.warning.textContent = data.warning;
        el.warning.hidden = false;
      }
      if (data.mode) setBadge(data.mode);
      renderSignals();
      renderResults();
    } catch (e) {
      setBadge(null);
      showError('Couldn\u2019t reach the planner \u2014 is the server running?');
    } finally {
      setLoading(false);
    }
  }

  el.planBtn.addEventListener('click', submit);
  el.week.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') submit();
  });

  /* ---------- boot ---------- */
  checkHealth();
})();
