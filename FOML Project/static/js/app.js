/* ── State ─────────────────────────────────────────────────── */
const state = {
  genre: null,
  language: null,
  imdbMin: 6.0,
  imdbMax: 8.0,
  yearMin: 2010,
  yearMax: 2022,
};

/* ── DOM refs ──────────────────────────────────────────────── */
const imdbMinInput  = document.getElementById('imdb-min');
const imdbMaxInput  = document.getElementById('imdb-max');
const imdbDisplay   = document.getElementById('imdb-display');
const imdbFill      = document.getElementById('imdb-fill');

const yearMinInput  = document.getElementById('year-min');
const yearMaxInput  = document.getElementById('year-max');
const yearDisplay   = document.getElementById('year-display');
const yearFill      = document.getElementById('year-fill');

const recommendBtn  = document.getElementById('recommend-btn');
const container     = document.getElementById('results-container');
const loader        = document.getElementById('loader');
const resultsTitle  = document.getElementById('results-title');
const resultsCount  = document.getElementById('results-count');

/* ── Genre chips ────────────────────────────────────────────── */
document.querySelectorAll('.genre-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.genre-chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    state.genre = chip.dataset.genre;
  });
});

/* ── Language chips ─────────────────────────────────────────── */
document.querySelectorAll('.lang-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.lang-chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    state.language = chip.dataset.lang;
  });
});

/* ── Dual range helper ──────────────────────────────────────── */
function updateDualRange(minEl, maxEl, fillEl, displayEl, fmt) {
  const min  = parseFloat(minEl.min);
  const max  = parseFloat(minEl.max);
  let   lo   = parseFloat(minEl.value);
  let   hi   = parseFloat(maxEl.value);

  const gap = fmt === 'year' ? 1 : 0.1;
  if (lo > hi - gap) { lo = hi - gap; minEl.value = lo; }
  if (hi < lo + gap) { hi = lo + gap; maxEl.value = hi; }

  const pctLo = ((lo - min) / (max - min)) * 100;
  const pctHi = ((hi - min) / (max - min)) * 100;

  fillEl.style.left  = pctLo + '%';
  fillEl.style.width = (pctHi - pctLo) + '%';

  if (fmt === 'year') {
    displayEl.textContent = `${Math.round(lo)} – ${Math.round(hi)}`;
  } else {
    displayEl.textContent = `${lo.toFixed(1)} – ${hi.toFixed(1)}`;
  }
}

/* IMDb sliders */
function onImdbChange() {
  updateDualRange(imdbMinInput, imdbMaxInput, imdbFill, imdbDisplay, 'imdb');
  state.imdbMin = parseFloat(imdbMinInput.value);
  state.imdbMax = parseFloat(imdbMaxInput.value);
}
imdbMinInput.addEventListener('input', onImdbChange);
imdbMaxInput.addEventListener('input', onImdbChange);

/* Year sliders */
function onYearChange() {
  updateDualRange(yearMinInput, yearMaxInput, yearFill, yearDisplay, 'year');
  state.yearMin = parseInt(yearMinInput.value);
  state.yearMax = parseInt(yearMaxInput.value);
}
yearMinInput.addEventListener('input', onYearChange);
yearMaxInput.addEventListener('input', onYearChange);

/* Init fill positions on load */
onImdbChange();
onYearChange();

/* ── Recommend ─────────────────────────────────────────────── */
recommendBtn.addEventListener('click', async () => {
  if (!state.genre) {
    flashMissing('.genre-grid'); return;
  }
  if (!state.language) {
    flashMissing('.lang-grid'); return;
  }

  showLoader(true);

  try {
    const res = await fetch('/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        genre:    state.genre,
        language: state.language,
        imdb_min: state.imdbMin,
        imdb_max: state.imdbMax,
        year_min: state.yearMin,
        year_max: state.yearMax,
      }),
    });
    const data = await res.json();
    renderResults(data);
  } catch (err) {
    container.innerHTML = `<div class="no-results"><strong>Error</strong>${err.message}</div>`;
  } finally {
    showLoader(false);
  }
});

/* ── Render ─────────────────────────────────────────────────── */
function renderResults({ movies, message }) {
  resultsTitle.textContent =
    movies.length > 0
      ? `${state.genre} · ${state.language}`
      : 'No results';
  resultsCount.textContent = message;

  if (movies.length === 0) {
    container.innerHTML = `
      <div class="no-results">
        <strong>No movies found</strong>
        Try widening your IMDb range or year range.
      </div>`;
    return;
  }

  container.innerHTML = movies.map((m, i) => buildCard(m, i + 1)).join('');

  // Animate score bars
  requestAnimationFrame(() => {
    document.querySelectorAll('.score-bar').forEach(bar => {
      bar.style.width = bar.dataset.width + '%';
    });
  });
}

function buildCard(m, rank) {
  const rfPct = Math.round(m.rf_score * 100);
  const ratingStars = ratingBar(m.rating);
  const sideGenres = m.side_genre
    ? m.side_genre.split(',').map(g => g.trim()).filter(Boolean)
    : [];

  const sideTagsHtml = sideGenres.slice(0, 3).map(g =>
    `<span class="genre-tag">${g}</span>`
  ).join('');

  const runtime = m.runtime > 0 ? `${m.runtime} min` : '';

  return `
  <div class="movie-card">
    <span class="card-rank">#${rank}</span>
    <div class="card-top">
      <h3 class="card-title">${escHtml(m.title)}</h3>
      <div class="card-meta">
        <span class="meta-year">${m.year}</span>
        <span class="meta-dot">•</span>
        <span class="meta-lang">${escHtml(m.language)}</span>
        <span class="meta-dot">•</span>
        <span class="meta-censor">${escHtml(m.censor)}</span>
        ${runtime ? `<span class="meta-dot">•</span><span class="meta-lang">${runtime}</span>` : ''}
      </div>
    </div>
    <div class="card-bottom">
      <div class="card-rating-row">
        <div class="imdb-badge">
          <span class="imdb-label">IMDb</span>
          <span class="imdb-score">★ ${m.rating}</span>
        </div>
        <span class="rf-score">RF Score: <span>${rfPct}%</span></span>
      </div>
      <div class="score-bar-wrap">
        <div class="score-bar" style="width:0%" data-width="${rfPct}"></div>
      </div>
      <div class="card-genres">
        <span class="genre-tag main">${escHtml(m.genre)}</span>
        ${sideTagsHtml}
      </div>
      <p class="card-director">Dir. <strong>${escHtml(m.director)}</strong></p>
    </div>
  </div>`;
}

/* ── Helpers ────────────────────────────────────────────────── */
function showLoader(show) {
  loader.classList.toggle('hidden', !show);
  if (show) container.innerHTML = '';
}

function flashMissing(selector) {
  const el = document.querySelector(selector);
  el.style.outline = '2px solid var(--accent)';
  el.style.borderRadius = '8px';
  setTimeout(() => { el.style.outline = 'none'; }, 1400);
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function ratingBar(r) {
  const full = Math.floor(r / 2);
  const half = (r / 2) % 1 >= 0.5 ? 1 : 0;
  return '★'.repeat(full) + (half ? '½' : '') + '☆'.repeat(5 - full - half);
}
