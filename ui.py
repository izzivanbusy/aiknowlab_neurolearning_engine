"""Serve the Wortschatzmaschine UI as a single HTML page."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

HTML = r"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Wortschatzmaschine · A1</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:        #0d0f14;
      --surface:   #161820;
      --border:    #252836;
      --text:      #e2e4ef;
      --muted:     #5a5d74;
      --accent:    #7c6fff;
      --accent2:   #34d399;
      --danger:    #ef4444;
      --warn:      #f59e0b;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: flex-start;
      padding: 24px 16px 60px;
    }

    /* ── Header ── */
    .header {
      width: 100%;
      max-width: 560px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 24px;
    }
    .brand {
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.14em;
      color: var(--accent);
      text-transform: uppercase;
    }
    .word-counter {
      font-size: 12px;
      color: var(--muted);
    }

    /* ── Progress ── */
    .progress-bar {
      width: 100%;
      max-width: 560px;
      height: 3px;
      background: var(--border);
      border-radius: 3px;
      margin-bottom: 28px;
      overflow: hidden;
    }
    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, var(--accent), var(--accent2));
      border-radius: 3px;
      transition: width 0.6s ease;
    }

    /* ── Stage indicator ── */
    .stage-row {
      width: 100%;
      max-width: 560px;
      display: flex;
      gap: 6px;
      margin-bottom: 24px;
    }
    .stage-dot {
      flex: 1;
      height: 3px;
      border-radius: 3px;
      background: var(--border);
      transition: background 0.3s;
    }
    .stage-dot.active   { background: var(--accent); }
    .stage-dot.done     { background: var(--accent2); }

    /* ── Card ── */
    .card {
      width: 100%;
      max-width: 560px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 36px 32px;
    }

    /* ── Word display (ENCOUNTER) ── */
    .word-hero {
      text-align: center;
      margin-bottom: 28px;
    }
    .word-de {
      font-size: 42px;
      font-weight: 800;
      letter-spacing: -0.02em;
      line-height: 1.1;
      margin-bottom: 8px;
    }
    .word-type-pill {
      display: inline-block;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 3px 10px;
      margin-bottom: 12px;
    }
    .word-translation {
      font-size: 22px;
      color: var(--accent2);
      font-weight: 600;
    }

    /* ── Example sentences ── */
    .examples {
      margin-top: 24px;
      border-top: 1px solid var(--border);
      padding-top: 20px;
    }
    .example-label {
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 10px;
    }
    .example-item {
      font-size: 15px;
      line-height: 1.6;
      color: #b0b3c8;
      padding: 8px 0;
      border-bottom: 1px solid var(--border);
    }
    .example-item:last-child { border-bottom: none; }
    .example-item em {
      color: var(--accent);
      font-style: normal;
      font-weight: 600;
    }

    /* ── Prompt (RECOGNIZE / RECALL / PRODUCE) ── */
    .stage-label {
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: 10px;
    }
    .prompt-text {
      font-size: 20px;
      font-weight: 600;
      line-height: 1.4;
      margin-bottom: 8px;
    }
    .prompt-subtext {
      font-size: 14px;
      color: var(--muted);
      margin-bottom: 24px;
    }
    .gapped-sentence {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px 20px;
      font-size: 18px;
      line-height: 1.5;
      margin-bottom: 20px;
    }
    .blank {
      display: inline-block;
      min-width: 60px;
      border-bottom: 2px solid var(--accent);
      color: transparent;
    }

    /* ── Input ── */
    textarea, input[type=text] {
      width: 100%;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      color: var(--text);
      font-size: 17px;
      font-family: inherit;
      padding: 14px 18px;
      margin-bottom: 16px;
      outline: none;
      transition: border-color 0.2s;
      resize: none;
    }
    textarea { min-height: 100px; line-height: 1.5; }
    textarea:focus, input[type=text]:focus { border-color: var(--accent); }

    /* ── Buttons ── */
    .btn {
      display: block;
      width: 100%;
      background: var(--accent);
      color: #fff;
      border: none;
      border-radius: 12px;
      padding: 14px;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
      transition: opacity 0.15s, transform 0.1s;
      text-align: center;
    }
    .btn:hover   { opacity: 0.9; }
    .btn:active  { transform: scale(0.98); }
    .btn:disabled { opacity: 0.4; cursor: not-allowed; }
    .btn-ghost {
      background: transparent;
      border: 1px solid var(--border);
      color: var(--muted);
      margin-top: 10px;
      font-weight: 500;
    }
    .btn-ghost:hover { border-color: var(--muted); color: var(--text); }

    /* ── Feedback ── */
    .feedback-box {
      border-radius: 12px;
      padding: 18px 20px;
      margin-bottom: 20px;
      font-size: 15px;
      line-height: 1.6;
    }
    .fb-good    { background: rgba(52,211,153,0.08); border: 1px solid rgba(52,211,153,0.25); color: #4ade80; }
    .fb-ok      { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.25); color: #fbbf24; }
    .fb-wrong   { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25); color: #f87171; }

    /* ── Acquisition pill ── */
    .acq-row {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 20px;
    }
    .acq-label { font-size: 12px; color: var(--muted); white-space: nowrap; }
    .acq-bar-wrap {
      flex: 1;
      height: 6px;
      background: var(--border);
      border-radius: 6px;
      overflow: hidden;
    }
    .acq-bar-fill {
      height: 100%;
      background: linear-gradient(90deg, var(--accent), var(--accent2));
      border-radius: 6px;
      transition: width 0.8s ease;
    }
    .acq-pct { font-size: 12px; font-weight: 700; color: var(--accent2); }

    /* ── Start screen ── */
    .start-title {
      font-size: 30px;
      font-weight: 800;
      line-height: 1.2;
      margin-bottom: 8px;
    }
    .start-sub {
      font-size: 15px;
      color: var(--muted);
      margin-bottom: 28px;
      line-height: 1.6;
    }
    .level-badge {
      display: inline-block;
      background: rgba(124,111,255,0.12);
      border: 1px solid rgba(124,111,255,0.3);
      color: var(--accent);
      border-radius: 8px;
      font-size: 13px;
      font-weight: 700;
      padding: 4px 12px;
      margin-bottom: 6px;
    }
    label {
      display: block;
      font-size: 12px;
      font-weight: 600;
      color: var(--muted);
      letter-spacing: 0.07em;
      text-transform: uppercase;
      margin-bottom: 8px;
      margin-top: 20px;
    }
    select {
      width: 100%;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      color: var(--text);
      font-size: 15px;
      font-family: inherit;
      padding: 12px 16px;
      outline: none;
    }
    select:focus { border-color: var(--accent); }

    /* ── Done screen ── */
    .done-big { font-size: 56px; margin-bottom: 16px; text-align: center; }
    .done-title { font-size: 26px; font-weight: 800; text-align: center; margin-bottom: 8px; }
    .done-sub { font-size: 15px; color: var(--muted); text-align: center; margin-bottom: 28px; line-height: 1.6; }

    /* ── Utils ── */
    .hidden { display: none !important; }
    .spinner {
      display: inline-block; width: 16px; height: 16px;
      border: 2px solid rgba(255,255,255,0.2);
      border-top-color: #fff;
      border-radius: 50%;
      animation: spin 0.6s linear infinite;
      vertical-align: middle; margin-right: 6px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>

<!-- ═══════════════════ START SCREEN ═══════════════════ -->
<div id="screen-start">
  <div class="header">
    <span class="brand">aiknowlab</span>
  </div>
  <div class="card">
    <div class="level-badge">A1 Wortschatz</div>
    <h1 class="start-title">Wortschatzmaschine</h1>
    <p class="start-sub">331 Wörter aus der Goethe-Institut-A1-Liste. Von Null zu B1 — Wort für Wort.</p>

    <label>Muttersprache</label>
    <select id="l1">
      <option value="en">Englisch</option>
      <option value="ru">Russisch</option>
      <option value="tr">Türkisch</option>
      <option value="ar">Arabisch</option>
      <option value="uk">Ukrainisch</option>
      <option value="es">Spanisch</option>
      <option value="fr">Französisch</option>
      <option value="zh">Chinesisch</option>
    </select>

    <button class="btn" style="margin-top:28px" onclick="startSession()">Jetzt beginnen →</button>
  </div>
</div>

<!-- ═══════════════════ LEARNING SCREEN ═══════════════════ -->
<div id="screen-learn" class="hidden">
  <div class="header">
    <span class="brand">aiknowlab</span>
    <span class="word-counter" id="word-counter">Wort 0 / 331</span>
  </div>
  <div class="progress-bar">
    <div class="progress-fill" id="progress-fill" style="width:0%"></div>
  </div>
  <div class="stage-row" id="stage-row">
    <div class="stage-dot" id="sd-0"></div>
    <div class="stage-dot" id="sd-1"></div>
    <div class="stage-dot" id="sd-2"></div>
    <div class="stage-dot" id="sd-3"></div>
  </div>

  <div class="card" id="card-content">
    <!-- filled by JS -->
  </div>
</div>

<!-- ═══════════════════ DONE SCREEN ═══════════════════ -->
<div id="screen-done" class="hidden">
  <div class="header"><span class="brand">aiknowlab</span></div>
  <div class="card">
    <div class="done-big">🎉</div>
    <div class="done-title">Alle A1-Wörter gelernt!</div>
    <div class="done-sub">Du hast alle 331 Wörter der Goethe-Institut-A1-Liste absolviert. Das Engine hat deinen Fortschritt gespeichert.</div>
    <button class="btn" onclick="location.reload()">Neue Sitzung starten</button>
  </div>
</div>

<script>
const API = '';
let learnerId = null;
let currentItem = null;
let sessionAcq = 0;

const STAGE_LABELS = {
  vocab_encounter: 'KENNENLERNEN',
  vocab_recognize: 'ERKENNEN',
  vocab_recall:    'ABRUFEN',
  vocab_produce:   'PRODUZIEREN',
};

const STAGE_HINTS = {
  vocab_recognize: 'Ergänze das fehlende Wort in der Lücke.',
  vocab_recall:    'Schreibe das deutsche Wort.',
  vocab_produce:   'Schreibe einen eigenen Satz mit diesem Wort.',
};

function show(id) {
  ['screen-start','screen-learn','screen-done'].forEach(s =>
    document.getElementById(s).classList.add('hidden')
  );
  document.getElementById(id).classList.remove('hidden');
}

function updateStageDots(stageIndex) {
  for (let i = 0; i < 4; i++) {
    const dot = document.getElementById(`sd-${i}`);
    dot.className = 'stage-dot';
    if (i < stageIndex) dot.classList.add('done');
    else if (i === stageIndex) dot.classList.add('active');
  }
}

// ── Session start ──────────────────────────────────────────────────────────
async function startSession() {
  const btn = event.target;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Verbinde…';
  const l1 = document.getElementById('l1').value;
  try {
    const res = await fetch(`${API}/session/start`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ l1_language: l1, proficiency: 'A1' }),
    });
    const data = await res.json();
    learnerId = data.id;
    show('screen-learn');
    await loadNextItem();
  } catch(e) {
    btn.disabled = false;
    btn.textContent = 'Fehler – erneut versuchen';
  }
}

// ── Load next item ─────────────────────────────────────────────────────────
async function loadNextItem() {
  const card = document.getElementById('card-content');
  card.innerHTML = '<div style="text-align:center;padding:40px;color:var(--muted)"><span class="spinner"></span> Lädt…</div>';

  try {
    const res = await fetch(`${API}/vocab/${learnerId}/next`);
    if (res.status === 404) { show('screen-done'); return; }
    currentItem = await res.json();
    renderItem(currentItem);
  } catch(e) {
    card.innerHTML = '<p style="color:var(--danger);text-align:center">Ladefehler. Bitte neu laden.</p>';
  }
}

// ── Render item ────────────────────────────────────────────────────────────
function renderItem(item) {
  const stage = item.stage;
  updateStageDots(item.stage_index);

  // Update counters
  document.getElementById('word-counter').textContent = `Wort ${item.words_seen} / ${item.words_total}`;
  const pct = Math.min(100, (item.words_seen / item.words_total) * 100);
  document.getElementById('progress-fill').style.width = pct + '%';

  const card = document.getElementById('card-content');

  if (stage === 'vocab_encounter') {
    renderEncounter(item, card);
  } else if (stage === 'vocab_recognize') {
    renderRecognize(item, card);
  } else if (stage === 'vocab_recall') {
    renderRecall(item, card);
  } else if (stage === 'vocab_produce') {
    renderProduce(item, card);
  }
}

// ── ENCOUNTER ──────────────────────────────────────────────────────────────
function renderEncounter(item, card) {
  const examples = (item.examples || []).map(ex => {
    // highlight the target word in the example
    const re = new RegExp(`\\b(${escapeRe(item.word)}\\w*)`, 'gi');
    const hl = ex.replace(re, '<em>$1</em>');
    return `<div class="example-item">${hl}</div>`;
  }).join('');

  card.innerHTML = `
    <div class="word-hero">
      <div class="word-de">${item.word}</div>
      <div class="word-type-pill">${wordTypeLabel(item.word_type)}</div>
      <div class="word-translation">${item.translation_en}</div>
    </div>
    ${examples ? `<div class="examples"><div class="example-label">Beispiel</div>${examples}</div>` : ''}
    <button class="btn" style="margin-top:28px" onclick="markSeen()">Verstanden →</button>
  `;
}

// ── RECOGNIZE ──────────────────────────────────────────────────────────────
function renderRecognize(item, card) {
  const sentence = item.gapped_sentence || item.prompt_for_learner;
  const display = sentence.replace(/___/g, '<span class="blank">___</span>');

  card.innerHTML = `
    <div class="stage-label">${STAGE_LABELS.vocab_recognize}</div>
    <div class="prompt-text">Ergänze die Lücke</div>
    <div class="prompt-subtext">Welches Wort fehlt?</div>
    <div class="gapped-sentence">${display}</div>
    <input type="text" id="answer-input" placeholder="Wort eingeben…" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"
      onkeydown="if(event.key==='Enter') submitCheck()" />
    <button class="btn" id="btn-check" onclick="submitCheck()">Prüfen →</button>
    <button class="btn btn-ghost" onclick="skipToNext()">Überspringen</button>
  `;
  setTimeout(() => document.getElementById('answer-input')?.focus(), 50);
}

// ── RECALL ─────────────────────────────────────────────────────────────────
function renderRecall(item, card) {
  card.innerHTML = `
    <div class="stage-label">${STAGE_LABELS.vocab_recall}</div>
    <div class="prompt-text">${item.prompt_for_learner}</div>
    <div class="prompt-subtext">Schreibe das deutsche Wort.</div>
    <input type="text" id="answer-input" placeholder="Auf Deutsch…" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"
      onkeydown="if(event.key==='Enter') submitCheck()" />
    <button class="btn" id="btn-check" onclick="submitCheck()">Prüfen →</button>
    <button class="btn btn-ghost" onclick="skipToNext()">Überspringen</button>
  `;
  setTimeout(() => document.getElementById('answer-input')?.focus(), 50);
}

// ── PRODUCE ────────────────────────────────────────────────────────────────
function renderProduce(item, card) {
  card.innerHTML = `
    <div class="stage-label">${STAGE_LABELS.vocab_produce}</div>
    <div class="prompt-text">Schreibe einen eigenen Satz</div>
    <div class="prompt-subtext">Benutze das Wort <strong style="color:var(--accent)">${item.word}</strong> auf Deutsch.</div>
    <textarea id="answer-input" placeholder="Dein Satz auf Deutsch…" rows="3"></textarea>
    <button class="btn" id="btn-check" onclick="submitCheck()">Abschicken →</button>
    <button class="btn btn-ghost" onclick="skipToNext()">Überspringen</button>
  `;
  setTimeout(() => document.getElementById('answer-input')?.focus(), 50);
}

// ── Mark ENCOUNTER as seen ─────────────────────────────────────────────────
async function markSeen() {
  const btn = document.querySelector('#card-content .btn');
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>'; }
  try {
    await fetch(`${API}/vocab/seen`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ learner_id: learnerId, item_id: currentItem.item_id }),
    });
    await loadNextItem();
  } catch(e) {
    if (btn) { btn.disabled = false; btn.textContent = 'Verstanden →'; }
  }
}

// ── Submit RECOGNIZE / RECALL / PRODUCE ────────────────────────────────────
async function submitCheck() {
  const input = document.getElementById('answer-input');
  if (!input) return;
  const answer = input.value.trim();
  if (!answer) { input.focus(); return; }

  const btn = document.getElementById('btn-check');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>KI bewertet…';

  try {
    const res = await fetch(`${API}/vocab/check`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        learner_id: learnerId,
        item_id: currentItem.item_id,
        input_text: answer,
      }),
    });
    const data = await res.json();
    renderFeedback(data, answer);
  } catch(e) {
    btn.disabled = false;
    btn.textContent = 'Fehler – erneut versuchen';
  }
}

// ── Render feedback ────────────────────────────────────────────────────────
function renderFeedback(data, answer) {
  const pct = Math.round(data.acquisition_probability * 100);
  sessionAcq = data.acquisition_probability;

  const fbClass = data.correct ? 'fb-good' : (data.performance_score >= 0.4 ? 'fb-ok' : 'fb-wrong');

  const card = document.getElementById('card-content');
  card.innerHTML = `
    <div class="stage-label">${STAGE_LABELS[currentItem.stage] || ''}</div>
    <div class="feedback-box ${fbClass}">${escapeHtml(data.feedback)}</div>
    <div class="acq-row">
      <span class="acq-label">Wort beherrscht</span>
      <div class="acq-bar-wrap">
        <div class="acq-bar-fill" id="acq-fill" style="width:0%"></div>
      </div>
      <span class="acq-pct">${pct}%</span>
    </div>
    <button class="btn" onclick="loadNextItem()">Weiter →</button>
  `;
  // Animate bar
  setTimeout(() => {
    const fill = document.getElementById('acq-fill');
    if (fill) fill.style.width = pct + '%';
  }, 50);
}

// ── Skip ──────────────────────────────────────────────────────────────────
async function skipToNext() {
  await loadNextItem();
}

// ── Utils ──────────────────────────────────────────────────────────────────
function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function escapeRe(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
function wordTypeLabel(t) {
  const map = {
    noun: 'Substantiv',
    verb: 'Verb',
    adj: 'Adjektiv / Adverb',
    adv: 'Adverb',
    prep: 'Präposition',
    conj: 'Konjunktion',
    pron: 'Pronomen',
    num: 'Numerale',
    art: 'Artikel',
    part: 'Partikel',
    interj: 'Interjektion',
  };
  return map[t] || t;
}
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_ui() -> HTMLResponse:
    return HTMLResponse(content=HTML)
