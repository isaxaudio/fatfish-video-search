/* FF Video Platform — Find Your Video — Script */
/* Edit this file, then run: python3 webflow-push.py */

(function () {
  // ── Inject HTML ────────────────────────────────────────────
  document.body.insertAdjacentHTML('beforeend', [
    '<div class="fyv-overlay" id="fyv-overlay">',
    '  <div style="position:relative;width:min(92vw,960px)">',
    '    <button id="fyv-close" aria-label="Close"',
    '      style="position:absolute;top:12px;right:12px;z-index:2;width:36px;height:36px;',
    '             border:none;border-radius:999px;background:rgba(255,255,255,.12);',
    '             color:#fff;font-size:22px;cursor:pointer;">&times;</button>',
    '    <video id="fyv-modal-video" controls playsinline',
    '      style="width:100%;display:block;border-radius:16px;background:#000;"></video>',
    '  </div>',
    '</div>',
    '<div class="fyv-page">',
    '  <div class="fyv-hero">',
    '    <h1 class="fyv-headline">Find Your<br>Commencement<br>Moment.</h1>',
    '    <p class="fyv-subhead">Search your name to watch and download your graduation video.</p>',
    '    <input class="fyv-input" id="fyv-input" placeholder="Search your name..."',
    '      autocomplete="off" spellcheck="false" />',
    '  </div>',
    '  <div class="fyv-results">',
    '    <div id="fyv-status" style="text-align:center;font-size:11px;color:#A8A29E;margin-bottom:20px;"></div>',
    '    <div class="fyv-grid" id="fyv-grid"></div>',
    '  </div>',
    '</div>'
  ].join('\n'));

  // ── Config ─────────────────────────────────────────────────
  var SUPABASE_URL      = 'https://uqfxjqkwicoljgztkijw.supabase.co';
  var SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVxZnhqcWt3aWNvbGpnenRraWp3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU4NDk4NDEsImV4cCI6MjA5MTQyNTg0MX0.IIsnmrSB4uBhGxf_N4q1krhKp0i9KFwm917e5NYgHxQ';

  var input    = document.getElementById('fyv-input');
  var grid     = document.getElementById('fyv-grid');
  var status   = document.getElementById('fyv-status');
  var overlay  = document.getElementById('fyv-overlay');
  var video    = document.getElementById('fyv-modal-video');
  var closeBtn = document.getElementById('fyv-close');
  var timer    = null;

  // ── Helpers ────────────────────────────────────────────────
  function esc(s) {
    return String(s || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // ── Modal ──────────────────────────────────────────────────
  function openModal(url) {
    if (!url) return;
    video.src = url;
    overlay.classList.add('is-open');
    overlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    video.play().catch(function () {});
  }

  function closeModal() {
    video.pause();
    video.src = '';
    overlay.classList.remove('is-open');
    overlay.style.display = 'none';
    document.body.style.overflow = '';
  }

  closeBtn.addEventListener('click', closeModal);
  overlay.addEventListener('click', function (e) { if (e.target === overlay) closeModal(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeModal(); });

  // ── Card ───────────────────────────────────────────────────
  function renderCard(v) {
    var name        = esc(v.student_name || '');
    var school      = esc(v.school_name  || '');
    var eventText   = esc([v.event_name, v.event_year].filter(Boolean).join(' \u2022 '));
    var thumb       = v.thumbnail_url  || '';
    var videoUrl    = v.video_file_url || '';
    var smugUrl     = v.smugmug_url    || '#';
    var downloadUrl = v.download_url   || smugUrl;

    var thumbHtml = thumb
      ? '<img class="fyv-thumb ' + (videoUrl ? 'has-preview' : '') + '" src="' + esc(thumb) + '" alt="' + name + '" onerror="this.remove()">'
      : '<div class="fyv-thumb-fallback">\u25b6</div>';

    var previewHtml = videoUrl
      ? '<video class="fyv-preview" data-src="' + esc(videoUrl) + '" muted loop playsinline></video>'
      : '';

    var watchBtn = videoUrl
      ? '<button class="fyv-btn fyv-btn-watch" data-video="' + esc(videoUrl) + '">Watch</button>'
      : '<a class="fyv-btn fyv-btn-watch" href="' + esc(smugUrl) + '" target="_blank" rel="noopener">Watch</a>';

    var dlBtn = '<a class="fyv-btn fyv-btn-download" href="' + esc(downloadUrl) + '" target="_blank" rel="noopener">Download</a>';

    return '<div class="fyv-card">'
      + '<div class="fyv-thumb-wrap">' + thumbHtml + previewHtml + '</div>'
      + '<div class="fyv-card-body">'
      +   '<div class="fyv-name">' + name + '</div>'
      +   (school    ? '<div class="fyv-meta">' + school + '</div>' : '')
      +   (eventText ? '<div class="fyv-meta" style="margin-bottom:14px;">' + eventText + '</div>' : '')
      +   '<div class="fyv-actions">' + watchBtn + dlBtn + '</div>'
      + '</div>'
      + '</div>';
  }

  function wireButtons() {
    grid.querySelectorAll('.fyv-btn-watch[data-video]').forEach(function (btn) {
      btn.addEventListener('click', function () { openModal(btn.getAttribute('data-video')); });
    });
  }

  function wireHoverVideo() {
    grid.querySelectorAll('.fyv-card').forEach(function (card) {
      var preview   = card.querySelector('.fyv-preview');
      var thumbWrap = card.querySelector('.fyv-thumb-wrap');
      if (!preview || !thumbWrap) return;

      thumbWrap.addEventListener('mouseenter', function () {
        if (!preview.src && preview.dataset.src) preview.src = preview.dataset.src;
        preview.currentTime = 0;
        preview.play().catch(function () {});
      });
      thumbWrap.addEventListener('mouseleave', function () { preview.pause(); });
    });
  }

  // ── Search ─────────────────────────────────────────────────
  async function search() {
    var q = input.value.trim();
    if (q.length < 2) {
      grid.innerHTML     = '';
      status.textContent = q.length ? 'Type at least 2 characters' : '';
      return;
    }

    status.textContent = 'Searching...';

    var url = SUPABASE_URL
      + '/rest/v1/videos?search_name=ilike.%25' + encodeURIComponent(q) + '%25'
      + '&is_active=eq.true'
      + '&select=student_name,school_name,event_name,event_year,thumbnail_url,smugmug_url,download_url,video_file_url'
      + '&limit=50';

    try {
      var res = await fetch(url, {
        headers: { apikey: SUPABASE_ANON_KEY, Authorization: 'Bearer ' + SUPABASE_ANON_KEY }
      });

      if (!res.ok) throw new Error('API ' + res.status);
      var data = await res.json();

      status.textContent = data.length ? (data.length + ' result' + (data.length !== 1 ? 's' : '')) : '';

      if (!data.length) {
        grid.innerHTML = '<div class="fyv-empty">No results found</div>';
        return;
      }

      grid.innerHTML = data.map(renderCard).join('');
      wireButtons();
      wireHoverVideo();
    } catch (e) {
      console.error('[FYV]', e);
      status.textContent = '';
      grid.innerHTML = '<div class="fyv-empty">Something went wrong — please try again.</div>';
    }
  }

  input.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(search, 250);
  });

})();
