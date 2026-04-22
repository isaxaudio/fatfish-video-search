/* FF Video Platform — Find Your Video */
/* Edit then run: python3 webflow-push.py  */

(function () {

  // ── Inject HTML ────────────────────────────────────────────
  document.body.insertAdjacentHTML('afterbegin',
    '<div class="fyv-bg-photo">'
    + '<img src="https://raw.githack.com/isaxaudio/fatfish-video-search/main/hero-bg.png" alt="" aria-hidden="true">'
    + '</div>'
    + '<header class="fyv-header">'
    + '<img class="fyv-logo" src="https://raw.githack.com/isaxaudio/fatfish-video-search/main/uopx-logo.png" alt="University of Phoenix">'
    + '<a class="fyv-header-btn" href="mailto:uopxcommencement@phoenix.edu">Questions</a>'
    + '</header>'
    + '<div class="fyv-subheader"><span class="fyv-subheader-year">2026</span><span class="fyv-subheader-divider"></span><span class="fyv-subheader-label">Commencement</span></div>'
  );

  document.body.insertAdjacentHTML('beforeend', [
    '<div class="fyv-overlay" id="fyv-overlay">',
    '  <div style="position:relative;width:min(92vw,960px)">',
    '    <button id="fyv-close" aria-label="Close"',
    '      style="position:absolute;top:12px;right:12px;z-index:2;width:36px;height:36px;',
    '             border:none;border-radius:999px;background:rgba(255,255,255,.1);',
    '             color:#fff;font-size:22px;cursor:pointer;display:flex;align-items:center;justify-content:center;">&times;</button>',
    '    <video id="fyv-modal-video" controls playsinline',
    '      style="width:100%;display:block;border-radius:16px;background:#000;"></video>',
    '  </div>',
    '</div>',

    '<div class="fyv-page">',
    '  <div class="fyv-hero">',
    '    <h1 class="fyv-headline">Find Your<br><em>Commencement</em><br>Moment.</h1>',
    '    <p class="fyv-subhead">Search your name to watch and download your graduation video.</p>',
    '    <div class="fyv-search-wrap">',
    '      <span class="fyv-search-icon">',
    '        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">',
    '          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>',
    '        </svg>',
    '      </span>',
    '      <input class="fyv-input" id="fyv-input" placeholder="Search archive..."',
    '        autocomplete="off" spellcheck="false" />',
    '    </div>',
    '    <div class="fyv-scroll-hint">',
    '      <span class="fyv-scroll-hint-label">Scroll to explore</span>',
    '      <svg class="fyv-scroll-hint-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">',
    '        <polyline points="6 9 12 15 18 9"/>',
    '      </svg>',
    '      <div class="fyv-status" id="fyv-status"></div>',
    '    </div>',
    '  </div>',

    '  <div class="fyv-results">',
    '    <div class="fyv-grid" id="fyv-grid"></div>',
    '  </div>',
    '  <div class="fyv-congrats-section">',
    '    <div class="fyv-congrats-card">',
    '      <div class="fyv-congrats-left">',
    '        <h2 class="fyv-congrats-headline">Congratulations,<br><em>Graduates!</em></h2>',
    '        <div class="fyv-congrats-body">',
    '          <p>You believed &mdash; and you achieved. Get your personalized commencement video below and celebrate this milestone with friends, classmates, and family. Type your name in the search bar above to find your moment. Can&rsquo;t find it? <a href="mailto:uopxcommencement@phoenix.edu">Email us</a> and we&rsquo;ll get back to you as soon as possible.</p>',
    '          <p>Don&rsquo;t forget your <strong>digital commencement program</strong> &mdash; select <strong>&ldquo;Virtual-May2026&rdquo;</strong> in the drop-down to view or download. Available until <strong>June 2, 2026</strong>. Continue to soar, Phoenixes!</p>',
    '        </div>',
    '        <div class="fyv-congrats-pills">',
    '          <span class="fyv-congrats-pill fyv-congrats-pill--dark">Class of 2026</span>',
    '          <span class="fyv-congrats-pill fyv-congrats-pill--dark">University of Phoenix</span>',
    '          <span class="fyv-congrats-pill fyv-congrats-pill--red">Find Your Moment</span>',
    '        </div>',
    '      </div>',
    '      <div class="fyv-congrats-right">',
    '        <img class="fyv-congrats-photo" src="https://raw.githack.com/isaxaudio/fatfish-video-search/main/grad-photo.png" alt="Commencement">',
    '      </div>',
    '    </div>',
    '  </div>',

    '  <footer class="fyv-footer">',
    '    <img class="fyv-footer-logo" src="https://raw.githack.com/isaxaudio/fatfish-video-search/main/uopx-logo.png" alt="University of Phoenix">',
    '    <span class="fyv-footer-copy">&copy; 2026 University of Phoenix. All Rights Reserved.</span>',
    '    <div class="fyv-footer-links">',
    '      <a class="fyv-footer-link" href="mailto:uopxcommencement@phoenix.edu">Need Help</a>',
    '      <a class="fyv-footer-link" href="mailto:uopxcommencement@phoenix.edu">Contact Us</a>',
    '    </div>',
    '  </footer>',
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
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
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
  function playIcon() {
    return '<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">'
      + '<polygon points="5 3 19 12 5 21 5 3"/></svg>';
  }

  function downloadIcon() {
    return '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">'
      + '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
      + '<polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>';
  }

  function renderCard(v) {
    var name        = esc(v.student_name || '');
    var school      = esc(v.school_name  || '');
    var year        = v.event_year   ? 'Class of ' + v.event_year : '';
    var eventLabel  = esc(v.event_name || '');
    var thumb       = v.thumbnail_url  || '';
    var videoUrl    = v.video_file_url || '';
    var smugUrl     = esc(v.smugmug_url    || '#');
    var downloadUrl = esc(v.download_url   || v.smugmug_url || '#');

    // Thumbnail area
    var thumbContent = thumb
      ? '<img class="fyv-thumb ' + (videoUrl ? 'has-preview' : '') + '" src="' + esc(thumb) + '" alt="' + name + '" onerror="this.remove()">'
      : '<div class="fyv-thumb-fallback"><svg width="32" height="32" viewBox="0 0 24 24" fill="rgba(255,255,255,0.2)"><polygon points="5 3 19 12 5 21 5 3"/></svg></div>';

    var previewEl = videoUrl
      ? '<video class="fyv-preview" data-src="' + esc(videoUrl) + '" muted loop playsinline></video>'
      : '';

    // Click thumbnail → open modal or SmugMug
    var thumbClick = videoUrl
      ? 'onclick="(function(){var v=document.getElementById(\'fyv-modal-video\');v.src=\'' + esc(videoUrl) + '\';document.getElementById(\'fyv-overlay\').classList.add(\'is-open\');document.getElementById(\'fyv-overlay\').style.display=\'flex\';document.body.style.overflow=\'hidden\';v.play().catch(function(){});})()"'
      : 'onclick="window.open(\'' + smugUrl + '\',\'_blank\')"';

    // Watch button
    var watchBtn = videoUrl
      ? '<button class="fyv-btn-watch" data-video="' + esc(videoUrl) + '">'
          + playIcon() + ' Watch Video</button>'
      : '<a class="fyv-btn-watch" href="' + smugUrl + '" target="_blank" rel="noopener">'
          + playIcon() + ' Watch Video</a>';

    // Meta row
    var metaParts = [];
    if (year)       metaParts.push('<span class="fyv-card-year">' + esc(year) + '</span>');
    if (eventLabel) metaParts.push('<span class="fyv-card-event-label">' + eventLabel + '</span>');
    var metaHtml = metaParts.length
      ? '<div class="fyv-card-meta">' + metaParts.join('<span class="fyv-card-meta-dot">&middot;</span>') + '</div>'
      : '';

    return '<div class="fyv-card">'
      + '<div class="fyv-thumb-wrap" ' + thumbClick + '>'
      +   thumbContent + previewEl
      + '</div>'
      + '<div class="fyv-card-body">'
      +   metaHtml
      +   '<div class="fyv-card-name">' + name + '</div>'
      +   (school ? '<div class="fyv-card-school">' + school + '</div>' : '')
      +   watchBtn
      +   '<div class="fyv-card-links">'
      +     '<a class="fyv-link" href="' + downloadUrl + '" target="_blank" rel="noopener">'
      +       downloadIcon() + ' Download'
      +     '</a>'
      +   '</div>'
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

    status.textContent = 'Searching\u2026';

    var url = SUPABASE_URL
      + '/rest/v1/videos?search_name=ilike.%25' + encodeURIComponent(q) + '%25'
      + '&is_active=eq.true'
      + '&select=student_name,school_name,event_name,event_year,thumbnail_url,smugmug_url,download_url,video_file_url'
      + '&order=last_name.asc,first_name.asc'
      + '&limit=50';

    try {
      var res = await fetch(url, {
        headers: { apikey: SUPABASE_ANON_KEY, Authorization: 'Bearer ' + SUPABASE_ANON_KEY }
      });
      if (!res.ok) throw new Error('API ' + res.status);
      var data = await res.json();

      status.textContent = data.length
        ? data.length + ' result' + (data.length !== 1 ? 's' : '')
        : '';

      if (!data.length) {
        grid.innerHTML = '<div class="fyv-empty">No results found for &ldquo;' + esc(q) + '&rdquo;</div>';
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
