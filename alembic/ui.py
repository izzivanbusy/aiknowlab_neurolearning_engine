"""Serve the learner-facing UI as a single HTML page."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

HTML = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>aiknowlab · Deutsch lernen</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0f1117;
      color: #e8eaf0;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }

    .card {
      background: #1a1d27;
      border: 1px solid #2a2d3a;
      border-radius: 16px;
      padding: 40px;
      width: 100%;
      max-width: 620px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }

    .brand {
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.12em;
      color: #6c63ff;
      text-transform: uppercase;
      margin-bottom: 32px;
    }

    h1 { font-size: 26px; font-weight: 700; line-height: 1.3; }
    h2 { font-size: 18px; font-weight: 600; color: #a8aab8; margin-bottom: 8px; }

    .subtitle {
      font-size: 15px;
      color: #6b6e80;
      margin-top: 8px;
      margin-bottom: 32px;
    }

    label {
      display: block;
      font-size: 13px;
      font-weight: 600;
      color: #8b8fa8;
      margin-bottom: 8px;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }

    select, textarea {
      width: 100%;
      background: #0f1117;
      border: 1px solid #2a2d3a;
      border-radius: 10px;
      color: #e8eaf0;
      font-size: 15px;
      font-family: inherit;
      padding: 12px 16px;
      margin-bottom: 20px;
      outline: none;
      transition: border-color 0.2s;
    }
    select:focus, textarea:focus { border-color: #6c63ff; }
    textarea { min-height: 120px; resize: vertical; line-height: 1.6; }

    .btn {
      display: inline-block;
      background: #6c63ff;
      color: #fff;
      border: none;
      border-radius: 10px;
      padding: 13px 28px;
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s, transform 0.1s;
      width: 100%;
    }
    .btn:hover { background: #7c73ff; }
    .btn:active { transform: scale(0.98); }
    .btn:disabled { background: #2a2d3a; color: #6b6e80; cursor: not-allowed; }

    .btn-secondary {
      background: #2a2d3a;
      color: #e8eaf0;
      margin-top: 12px;
    }
    .btn-secondary:hover { background: #3a3d4a; }

    /* Progress bar */
    .progress-wrap {
      margin-bottom: 28px;
    }
    .progress-label {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: #6b6e80;
      margin-bottom: 8px;
    }
    .progress-bar {
      height: 4px;
      background: #2a2d3a;
      border-radius: 4px;
      overflow: hidden;
    }
    .progress-fill {
      height: 100%;
      background: #6c63ff;
      border-radius: 4px;
      transition: width 0.5s ease;
    }

    /* Skill badge */
    .skill-badge {
      display: inline-block;
      background: rgba(108,99,255,0.15);
      border: 1px solid rgba(108,99,255,0.3);
      color: #9d96ff;
      font-size: 12px;
      font-weight: 600;
      border-radius: 20px;
      padding: 4px 12px;
      margin-bottom: 20px;
      letter-spacing: 0.04em;
    }

    /* Task prompt */
    .prompt-box {
      background: #0f1117;
      border: 1px solid #2a2d3a;
      border-radius: 10px;
      padding: 20px;
      margin-bottom: 24px;
      font-size: 15px;
      line-height: 1.7;
      color: #c8cad8;
      white-space: pre-wrap;
    }

    /* Feedback */
    .feedback-box {
      border-radius: 12px;
      padding: 20px 24px;
      margin-bottom: 24px;
      font-size: 15px;
      line-height: 1.7;
    }
    .feedback-positive { background: rgba(52,211,153,0.08); border: 1px solid rgba(52,211,153,0.2); color: #34d399; }
    .feedback-neutral  { background: rgba(251,191,36,0.08);  border: 1px solid rgba(251,191,36,0.2);  color: #fbbf24; }
    .feedback-negative { background: rgba(239,68,68,0.08);   border: 1px solid rgba(239,68,68,0.2);   color: #ef4444; }

    /* Acquisition meter */
    .meter-wrap {
      background: #0f1117;
      border: 1px solid #2a2d3a;
      border-radius: 10px;
      padding: 16px 20px;
      margin-bottom: 20px;
    }
    .meter-label {
      font-size: 12px;
      font-weight: 600;
      color: #6b6e80;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 10px;
    }
    .meter-bar {
      height: 8px;
      background: #2a2d3a;
      border-radius: 8px;
      overflow: hidden;
      margin-bottom: 6px;
    }
    .meter-fill {
      height: 100%;
      background: linear-gradient(90deg, #6c63ff, #34d399);
      border-radius: 8px;
      transition: width 0.8s ease;
    }
    .meter-value {
      font-size: 13px;
      color: #a8aab8;
    }

    /* Context tag */
    .context-tag {
      display: inline-block;
      font-size: 11px;
      color: #6b6e80;
      border: 1px solid #2a2d3a;
      border-radius: 6px;
      padding: 2px 8px;
      margin-bottom: 12px;
    }

    .done-icon { font-size: 48px; margin-bottom: 16px; }
    .hidden { display: none !important; }

    .spinner {
      display: inline-block;
      width: 18px; height: 18px;
      border: 2px solid rgba(255,255,255,0.2);
      border-top-color: #fff;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
      vertical-align: middle;
      margin-right: 8px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>

<!-- ── START SCREEN ─────────────────────────────── -->
<div class="card" id="screen-start">
  <div class="brand">aiknowlab</div>
  <h1>Deutsch für das Vorstellungsgespräch</h1>
  <p class="subtitle">Ein KI-System beobachtet, was du wirklich kannst — und entscheidet, was als nächstes kommt.</p>

  <label>Muttersprache</label>
  <select id="l1">
    <option value="ru">Russisch</option>
    <option value="en">Englisch</option>
    <option value="tr">Türkisch</option>
    <option value="ar">Arabisch</option>
    <option value="uk">Ukrainisch</option>
    <option value="es">Spanisch</option>
    <option value="fr">Französisch</option>
    <option value="zh">Chinesisch</option>
  </select>

  <label>Dein Deutschniveau</label>
  <select id="proficiency">
    <option value="A1">A1 – Anfänger</option>
    <option value="A2" selected>A2 – Grundkenntnisse</option>
    <option value="B1">B1 – Mittelstufe</option>
    <option value="B2">B2 – Fortgeschritten</option>
  </select>

  <button class="btn" id="btn-start" onclick="startSession()">Jetzt beginnen →</button>
</div>

<!-- ── TASK SCREEN ──────────────────────────────── -->
<div class="card hidden" id="screen-task">
  <div class="brand">aiknowlab</div>

  <div class="progress-wrap">
    <div class="progress-label">
      <span id="task-counter">Aufgabe 1</span>
      <span id="skill-name-label">SK-08 · Sich vorstellen</span>
    </div>
    <div class="progress-bar"><div class="progress-fill" id="progress-fill" style="width:0%"></div></div>
  </div>

  <div class="skill-badge" id="skill-badge">SK-08 · Sich vorstellen</div>
  <div class="context-tag" id="context-tag">Situation: Übung</div>

  <div class="prompt-box" id="task-prompt">Lädt…</div>

  <label for="answer">Deine Antwort auf Deutsch</label>
  <textarea id="answer" placeholder="Schreibe hier auf Deutsch…"></textarea>

  <button class="btn" id="btn-submit" onclick="submitAttempt()">Abschicken</button>
</div>

<!-- ── FEEDBACK SCREEN ─────────────────────────── -->
<div class="card hidden" id="screen-feedback">
  <div class="brand">aiknowlab</div>

  <h2>Auswertung</h2>

  <div class="feedback-box" id="feedback-text"></div>

  <div class="meter-wrap">
    <div class="meter-label">Erwerbswahrscheinlichkeit · Sich vorstellen</div>
    <div class="meter-bar"><div class="meter-fill" id="acq-fill" style="width:10%"></div></div>
    <div class="meter-value" id="acq-value">10%</div>
  </div>

  <button class="btn" id="btn-next" onclick="loadNextTask()">Nächste Aufgabe →</button>
  <button class="btn btn-secondary hidden" id="btn-done-final">Fertig</button>
</div>

<!-- ── DONE SCREEN ──────────────────────────────── -->
<div class="card hidden" id="screen-done">
  <div class="brand">aiknowlab</div>
  <div class="done-icon">🎯</div>
  <h1>Gut gemacht!</h1>
  <p class="subtitle">Du hast alle Aufgaben für <strong>Sich vorstellen</strong> absolviert. Das Engine hat deine Leistung beobachtet und deinen Lernpfad aktualisiert.</p>

  <div class="meter-wrap" style="margin-top:24px">
    <div class="meter-label">Finale Erwerbswahrscheinlichkeit</div>
    <div class="meter-bar"><div class="meter-fill" id="final-acq-fill" style="width:10%"></div></div>
    <div class="meter-value" id="final-acq-value">10%</div>
  </div>

  <button class="btn" style="margin-top:24px" onclick="location.reload()">Neue Sitzung</button>
</div>

<script>
const API = '';  // same origin
let learnerId = null;
let currentItem = null;
let taskCount = 0;
let lastAcqP = 0.1;

const CONTEXT_LABELS = {
  controlled_exercise: 'Kontrollierte Übung',
  scenario_guided: 'Geführtes Szenario',
  scenario_free: 'Freies Szenario',
  unexpected_transfer: 'Transfer in neuen Kontext',
};

function show(id) {
  ['screen-start','screen-task','screen-feedback','screen-done'].forEach(s => {
    document.getElementById(s).classList.add('hidden');
  });
  document.getElementById(id).classList.remove('hidden');
}

async function startSession() {
  const btn = document.getElementById('btn-start');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Verbinde…';

  const l1 = document.getElementById('l1').value;
  const proficiency = document.getElementById('proficiency').value;

  try {
    const res = await fetch(`${API}/session/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ l1_language: l1, proficiency }),
    });
    const data = await res.json();
    learnerId = data.id;
    await loadNextTask();
  } catch (e) {
    btn.disabled = false;
    btn.textContent = 'Fehler – bitte erneut versuchen';
  }
}

async function loadNextTask() {
  show('screen-task');
  document.getElementById('task-prompt').textContent = 'Lädt…';
  document.getElementById('answer').value = '';
  document.getElementById('btn-submit').disabled = false;
  document.getElementById('btn-submit').textContent = 'Abschicken';

  try {
    const res = await fetch(`${API}/loop/${learnerId}/next`);
    if (res.status === 404) { showDone(); return; }
    const item = await res.json();
    currentItem = item;
    taskCount++;

    document.getElementById('task-prompt').textContent = item.prompt_for_learner;
    document.getElementById('skill-badge').textContent = `${item.skill_code} · ${item.skill_name}`;
    document.getElementById('skill-name-label').textContent = `${item.skill_code} · ${item.skill_name}`;
    document.getElementById('task-counter').textContent = `Aufgabe ${taskCount}`;
    document.getElementById('context-tag').textContent =
      'Situation: ' + (CONTEXT_LABELS[item.context_label] || item.context_label);

    // Progress: transfer_distance 0–3 mapped to 5 tasks
    const pct = Math.min(100, (item.transfer_distance / 3) * 100);
    document.getElementById('progress-fill').style.width = pct + '%';
  } catch (e) {
    document.getElementById('task-prompt').textContent = 'Fehler beim Laden. Bitte neu laden.';
  }
}

async function submitAttempt() {
  const answer = document.getElementById('answer').value.trim();
  if (!answer) { document.getElementById('answer').focus(); return; }

  const btn = document.getElementById('btn-submit');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>KI bewertet…';

  try {
    const res = await fetch(`${API}/loop/attempt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        learner_id: learnerId,
        item_id: currentItem.item_id,
        stage: currentItem.context_label === 'controlled_exercise' ? 'retrieve' : 'generate',
        input_text: answer,
      }),
    });

    const data = await res.json();
    showFeedback(data);
  } catch (e) {
    btn.disabled = false;
    btn.textContent = 'Fehler – bitte erneut versuchen';
  }
}

function showFeedback(data) {
  show('screen-feedback');

  // Feedback text
  const feedbackEl = document.getElementById('feedback-text');
  feedbackEl.textContent = data.feedback;

  const score = data.signals?.performance_score ?? 0;
  feedbackEl.className = 'feedback-box';
  if (score >= 0.75) feedbackEl.classList.add('feedback-positive');
  else if (score >= 0.45) feedbackEl.classList.add('feedback-neutral');
  else feedbackEl.classList.add('feedback-negative');

  // Acquisition probability
  if (data.skill_states_updated && data.skill_states_updated.length > 0) {
    lastAcqP = data.skill_states_updated[0].acquisition_probability;
  }
  const pct = Math.round(lastAcqP * 100);
  document.getElementById('acq-fill').style.width = pct + '%';
  document.getElementById('acq-value').textContent = `${pct}% Erwerbswahrscheinlichkeit`;
}

function showDone() {
  show('screen-done');
  const pct = Math.round(lastAcqP * 100);
  document.getElementById('final-acq-fill').style.width = pct + '%';
  document.getElementById('final-acq-value').textContent = `${pct}% Erwerbswahrscheinlichkeit`;
}
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_ui() -> HTMLResponse:
    return HTMLResponse(content=HTML)
