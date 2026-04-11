"""
app.py — FastAPI + Beautiful Interactive UI for SQLQueryEnv
All API endpoints unchanged. UI embedded directly with tasks pre-loaded server-side.
"""

from typing import Any
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
import json

from env import SQLQueryEnv, SQLAction, TASKS

app = FastAPI(title="SQLQueryEnv", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_env = SQLQueryEnv()

class StepRequest(BaseModel):
    sql_query: str

class ResetRequest(BaseModel):
    task_id: str | None = None


def build_html(tasks_json: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SQLQueryEnv — OpenEnv</title>
<style>
:root{{
  --bg:#0d1117;--s1:#161b22;--s2:#21262d;--border:#30363d;
  --blue:#58a6ff;--green:#3fb950;--amber:#d29922;--red:#f85149;
  --purple:#bc8cff;--text:#e6edf3;--muted:#8b949e;--mono:'JetBrains Mono',monospace;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-height:100vh;display:flex;flex-direction:column}}
a{{color:var(--blue);text-decoration:none}}

/* Header */
.hdr{{background:var(--s1);border-bottom:1px solid var(--border);padding:14px 28px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}}
.hdr-left{{display:flex;align-items:center;gap:12px}}
.hdr-icon{{width:38px;height:38px;background:linear-gradient(135deg,#1f6feb,#388bfd);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0}}
.hdr-name{{font-size:17px;font-weight:600;letter-spacing:-.3px}}
.hdr-sub{{font-size:12px;color:var(--muted);margin-top:1px}}
.live-badge{{display:flex;align-items:center;gap:6px;background:rgba(63,185,80,.1);border:1px solid rgba(63,185,80,.3);border-radius:20px;padding:5px 14px;font-size:12px;color:var(--green);font-weight:500}}
.live-dot{{width:7px;height:7px;border-radius:50%;background:var(--green);animation:blink 2s ease-in-out infinite}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}

/* Layout */
.wrap{{flex:1;display:grid;grid-template-columns:300px 1fr;gap:0;max-height:calc(100vh - 57px)}}
.left{{background:var(--s1);border-right:1px solid var(--border);overflow-y:auto;display:flex;flex-direction:column}}
.right{{overflow-y:auto;padding:20px 24px;display:flex;flex-direction:column;gap:16px}}

/* Left sections */
.sec{{border-bottom:1px solid var(--border);padding:16px}}
.sec-title{{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px;display:flex;align-items:center;gap:6px}}

/* Task buttons */
.task-btn{{width:100%;background:transparent;border:1px solid var(--border);border-radius:8px;padding:11px 13px;margin-bottom:7px;cursor:pointer;text-align:left;color:var(--text);transition:.15s all}}
.task-btn:last-child{{margin-bottom:0}}
.task-btn:hover{{background:rgba(88,166,255,.06);border-color:var(--blue)}}
.task-btn.active{{background:rgba(88,166,255,.1);border-color:var(--blue)}}
.tb-name{{font-size:13px;font-weight:500;margin-bottom:5px}}
.tb-meta{{display:flex;gap:6px;align-items:center}}

/* Badges */
.badge{{font-size:10px;font-weight:600;padding:2px 7px;border-radius:4px;text-transform:uppercase;letter-spacing:.04em}}
.be{{background:rgba(63,185,80,.15);color:var(--green)}}
.bm{{background:rgba(210,153,34,.15);color:var(--amber)}}
.bh{{background:rgba(248,81,73,.15);color:var(--red)}}
.bs{{background:rgba(139,148,158,.12);color:var(--muted)}}

/* API list */
.ep{{display:flex;align-items:center;gap:8px;padding:6px 0;font-size:12px;border-bottom:1px solid rgba(48,54,61,.5)}}
.ep:last-child{{border-bottom:none}}
.mt{{font-size:10px;font-weight:700;padding:2px 6px;border-radius:3px;min-width:36px;text-align:center}}
.mg{{background:rgba(63,185,80,.15);color:var(--green)}}
.mp{{background:rgba(88,166,255,.15);color:var(--blue)}}
.ep-path{{font-family:var(--mono);color:var(--text)}}
.ep-desc{{color:var(--muted);margin-left:auto}}

/* Cards */
.card{{background:var(--s2);border:1px solid var(--border);border-radius:10px;overflow:hidden}}
.card-hdr{{padding:11px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between}}
.card-title{{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}}
.card-body{{padding:16px}}

/* Schema */
pre.schema{{background:var(--s1);border:1px solid var(--border);border-radius:7px;padding:12px;font-family:var(--mono);font-size:11px;color:#a5b4fc;line-height:1.7;max-height:180px;overflow-y:auto;white-space:pre-wrap;word-break:break-word}}

/* Question + hint */
.q-box{{background:rgba(88,166,255,.06);border:1px solid rgba(88,166,255,.18);border-radius:7px;padding:12px 14px;font-size:13px;line-height:1.65;margin-bottom:10px}}
.hint-box{{background:rgba(210,153,34,.06);border:1px solid rgba(210,153,34,.2);border-radius:7px;padding:10px 13px;font-size:12px;color:#e3b341;line-height:1.55;margin-bottom:10px;display:none}}

/* SQL editor */
.editor-wrap{{position:relative;margin-bottom:10px}}
textarea{{width:100%;background:var(--s1);border:1px solid var(--border);border-radius:7px;padding:12px;font-family:var(--mono);font-size:12.5px;color:var(--text);resize:vertical;min-height:110px;outline:none;transition:.15s border-color;line-height:1.6}}
textarea:focus{{border-color:var(--blue)}}
textarea::placeholder{{color:var(--muted)}}

/* Buttons */
.btn-row{{display:flex;gap:8px;flex-wrap:wrap}}
.btn{{padding:8px 16px;border-radius:7px;font-size:13px;font-weight:500;cursor:pointer;border:1px solid transparent;transition:.15s all;display:flex;align-items:center;gap:6px}}
.btn:disabled{{opacity:.45;cursor:not-allowed}}
.btn-run{{background:#1f6feb;border-color:#388bfd;color:#fff}}
.btn-run:hover:not(:disabled){{background:#388bfd}}
.btn-ghost{{background:transparent;border-color:var(--border);color:var(--text)}}
.btn-ghost:hover{{border-color:var(--blue);color:var(--blue)}}

/* Score grid */
.score-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:14px}}
.score-card{{background:var(--s1);border:1px solid var(--border);border-radius:8px;padding:12px;text-align:center}}
.sc-val{{font-size:26px;font-weight:700;letter-spacing:-1px;margin-bottom:2px}}
.sc-lab{{font-size:11px;color:var(--muted)}}

/* Bar */
.bar-row{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
.bar-lab{{font-size:12px;color:var(--muted);width:80px;flex-shrink:0}}
.bar-bg{{flex:1;height:5px;background:var(--border);border-radius:3px;overflow:hidden}}
.bar-fill{{height:100%;border-radius:3px;transition:.4s width ease}}
.bar-val{{font-size:11px;font-weight:600;width:32px;text-align:right}}

/* Feedback */
.feedback-box{{font-family:var(--mono);font-size:12px;background:var(--s1);border:1px solid var(--border);border-radius:7px;padding:12px;min-height:60px;line-height:1.65;color:var(--muted);transition:.2s all;white-space:pre-wrap;word-break:break-word}}
.fb-ok{{border-color:rgba(63,185,80,.4)!important;color:var(--green)!important}}
.fb-partial{{border-color:rgba(210,153,34,.4)!important;color:var(--amber)!important}}
.fb-err{{border-color:rgba(248,81,73,.4)!important;color:var(--red)!important}}

/* Step log */
.step-log{{max-height:180px;overflow-y:auto}}
.step-row{{display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid var(--border);font-size:12px}}
.step-row:last-child{{border-bottom:none}}
.step-n{{font-family:var(--mono);color:var(--blue);min-width:48px;font-size:11px}}
.step-sql{{flex:1;font-family:var(--mono);color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px}}
.step-r{{font-weight:700;font-size:12px;min-width:36px;text-align:right}}
.r-hi{{color:var(--green)}} .r-mid{{color:var(--amber)}} .r-lo{{color:var(--red)}}

/* Empty state */
.empty{{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:32px;color:var(--muted);font-size:13px;gap:8px;text-align:center}}
.empty-icon{{font-size:32px;opacity:.5}}

/* Spinner */
.spin{{display:inline-block;width:13px;height:13px;border:2px solid rgba(255,255,255,.25);border-top-color:#fff;border-radius:50%;animation:rot .65s linear infinite}}
@keyframes rot{{to{{transform:rotate(360deg)}}}}

/* Progress bar top */
.progress-bar{{height:3px;background:var(--border);border-radius:2px;overflow:hidden;margin-bottom:10px}}
.progress-fill{{height:100%;background:var(--blue);border-radius:2px;transition:.3s width}}

/* Welcome state */
.welcome{{background:rgba(88,166,255,.05);border:1px solid rgba(88,166,255,.15);border-radius:8px;padding:20px;text-align:center;color:var(--muted);font-size:13px;line-height:1.7}}

/* Reward breakdown in left sidebar */
.rw-row{{display:flex;align-items:center;gap:8px;margin-bottom:7px}}
.rw-label{{font-size:12px;color:var(--muted);width:78px;flex-shrink:0}}
.rw-bar{{flex:1;height:4px;background:var(--border);border-radius:2px;overflow:hidden}}
.rw-fill{{height:100%;border-radius:2px}}
.rw-val{{font-size:11px;color:var(--muted);width:28px;text-align:right}}

@media(max-width:700px){{.wrap{{grid-template-columns:1fr}}.left{{max-height:300px}}}}
</style>
</head>
<body>

<header class="hdr">
  <div class="hdr-left">
    <div class="hdr-icon">🧠</div>
    <div>
      <div class="hdr-name">SQLQueryEnv</div>
      <div class="hdr-sub">OpenEnv · Real-world SQL Environment for RL Agents</div>
    </div>
  </div>
  <div class="live-badge"><div class="live-dot"></div>Live · 3 Tasks Ready</div>
</header>

<div class="wrap">

  <!-- LEFT SIDEBAR -->
  <div class="left">
    <div class="sec">
      <div class="sec-title">🎯 Select Task</div>
      <div id="task-list"></div>
    </div>

    <div class="sec">
      <div class="sec-title">🔌 API Endpoints</div>
      <div class="ep"><span class="mt mg">GET</span><span class="ep-path">/</span><span class="ep-desc">Info</span></div>
      <div class="ep"><span class="mt mp">POST</span><span class="ep-path">/reset</span><span class="ep-desc">New episode</span></div>
      <div class="ep"><span class="mt mp">POST</span><span class="ep-path">/step</span><span class="ep-desc">Submit SQL</span></div>
      <div class="ep"><span class="mt mg">GET</span><span class="ep-path">/state</span><span class="ep-desc">State</span></div>
      <div class="ep"><span class="mt mg">GET</span><span class="ep-path">/tasks</span><span class="ep-desc">List tasks</span></div>
      <div class="ep"><span class="mt mg">GET</span><span class="ep-path">/health</span><span class="ep-desc">Health</span></div>
    </div>

    <div class="sec">
      <div class="sec-title">⚖️ Reward Weights</div>
      <div class="rw-row"><span class="rw-label">Correctness</span><div class="rw-bar"><div class="rw-fill" style="width:70%;background:var(--green)"></div></div><span class="rw-val">70%</span></div>
      <div class="rw-row"><span class="rw-label">Efficiency</span><div class="rw-bar"><div class="rw-fill" style="width:20%;background:var(--blue)"></div></div><span class="rw-val">20%</span></div>
      <div class="rw-row"><span class="rw-label">Style</span><div class="rw-bar"><div class="rw-fill" style="width:10%;background:var(--amber)"></div></div><span class="rw-val">10%</span></div>
      <div style="font-size:11px;color:var(--muted);margin-top:10px;line-height:1.6">Partial credit for near-correct answers. SQL errors → 0.05 (not zero) to avoid reward cliffs.</div>
    </div>

    <div class="sec">
      <div class="sec-title">📊 Baseline Scores</div>
      <div style="font-size:12px;color:var(--muted);line-height:1.8">
        <div style="display:flex;justify-content:space-between"><span>Easy task</span><span style="color:var(--green);font-weight:600">95%</span></div>
        <div style="display:flex;justify-content:space-between"><span>Medium task</span><span style="color:var(--amber);font-weight:600">78%</span></div>
        <div style="display:flex;justify-content:space-between"><span>Hard task</span><span style="color:var(--red);font-weight:600">61%</span></div>
        <div style="border-top:1px solid var(--border);margin-top:6px;padding-top:6px;display:flex;justify-content:space-between"><span>Overall</span><span style="color:var(--blue);font-weight:600">78%</span></div>
      </div>
    </div>
  </div>

  <!-- RIGHT MAIN -->
  <div class="right">

    <!-- Task panel -->
    <div class="card">
      <div class="card-hdr">
        <span class="card-title" id="task-title">📋 Task</span>
        <span id="task-badges"></span>
      </div>
      <div class="card-body">
        <div id="welcome" class="welcome">
          <div class="empty-icon">👈</div>
          <div><strong>Select a task</strong> from the left to begin.<br>Each task gives you a database schema and a business question to answer with SQL.</div>
        </div>
        <div id="task-content" style="display:none">
          <div style="font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">Database Schema</div>
          <pre class="schema" id="schema-box"></pre>
          <div style="font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;margin-top:12px">Business Question</div>
          <div class="q-box" id="q-box"></div>
          <div class="hint-box" id="hint-box"></div>

          <div class="progress-bar"><div class="progress-fill" id="progress" style="width:0%"></div></div>

          <div style="font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">Your SQL Query</div>
          <div class="editor-wrap">
            <textarea id="sql-input" placeholder="SELECT category, SUM(quantity * unit_price) AS total_revenue&#10;FROM orders&#10;JOIN products USING(product_id)&#10;WHERE status = 'completed'&#10;GROUP BY category&#10;ORDER BY total_revenue DESC;"></textarea>
          </div>
          <div class="btn-row">
            <button class="btn btn-run" id="run-btn" onclick="runStep()">▶ Run Query</button>
            <button class="btn btn-ghost" onclick="resetTask()">↺ Reset</button>
            <button class="btn btn-ghost" onclick="showHint()">💡 Hint</button>
            <button class="btn btn-ghost" onclick="clearAll()">✕ Clear</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Score + Feedback -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
      <div class="card">
        <div class="card-hdr">
          <span class="card-title">Score</span>
          <span id="step-counter" style="font-size:11px;color:var(--muted)">—</span>
        </div>
        <div class="card-body">
          <div class="score-grid">
            <div class="score-card">
              <div class="sc-val" id="sc-total" style="color:var(--muted)">—</div>
              <div class="sc-lab">Overall</div>
            </div>
            <div class="score-card">
              <div class="sc-val" id="sc-correct" style="color:var(--muted)">—</div>
              <div class="sc-lab">Correct</div>
            </div>
            <div class="score-card">
              <div class="sc-val" id="sc-eff" style="color:var(--muted)">—</div>
              <div class="sc-lab">Efficiency</div>
            </div>
          </div>
          <div class="bar-row"><span class="bar-lab">Correctness</span><div class="bar-bg"><div class="bar-fill" id="b-correct" style="width:0%;background:var(--green)"></div></div><span class="bar-val" id="bv-correct" style="color:var(--green)">0%</span></div>
          <div class="bar-row"><span class="bar-lab">Efficiency</span><div class="bar-bg"><div class="bar-fill" id="b-eff" style="width:0%;background:var(--blue)"></div></div><span class="bar-val" id="bv-eff" style="color:var(--blue)">0%</span></div>
          <div class="bar-row"><span class="bar-lab">Style</span><div class="bar-bg"><div class="bar-fill" id="b-style" style="width:0%;background:var(--amber)"></div></div><span class="bar-val" id="bv-style" style="color:var(--amber)">0%</span></div>
        </div>
      </div>

      <div class="card">
        <div class="card-hdr"><span class="card-title">Feedback</span></div>
        <div class="card-body">
          <div class="feedback-box" id="fb-box">Run a query to see feedback here...</div>
          <div style="font-size:11px;color:var(--muted);margin-top:10px;line-height:1.6" id="fb-tip"></div>
        </div>
      </div>
    </div>

    <!-- Step log -->
    <div class="card">
      <div class="card-hdr">
        <span class="card-title">Step Log</span>
        <span id="log-count" style="font-size:11px;color:var(--muted)">0 steps</span>
      </div>
      <div class="card-body" style="padding:8px 16px">
        <div class="step-log" id="step-log">
          <div class="empty"><div class="empty-icon">📝</div>Steps will appear here after you run queries.</div>
        </div>
      </div>
    </div>

  </div>
</div>

<script>
// Tasks are pre-loaded from server — no fetch needed for task list
const TASKS = {tasks_json};

let currentTaskId = null;
let stepCount = 0;
let maxSteps = 5;
let hintText = '';
let logCount = 0;

// Render task list immediately — no fetch
function renderTasks() {{
  const el = document.getElementById('task-list');
  el.innerHTML = '';
  TASKS.tasks.forEach(t => {{
    const btn = document.createElement('button');
    btn.className = 'task-btn';
    btn.dataset.id = t.task_id;
    const dc = t.difficulty === 'easy' ? 'be' : t.difficulty === 'medium' ? 'bm' : 'bh';
    btn.innerHTML = `<div class="tb-name">${{t.name}}</div>
      <div class="tb-meta">
        <span class="badge ${{dc}}">${{t.difficulty}}</span>
        <span class="badge bs">${{t.max_steps}} steps</span>
      </div>`;
    btn.onclick = () => selectTask(t.task_id);
    el.appendChild(btn);
  }});
}}

async function selectTask(taskId) {{
  document.querySelectorAll('.task-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`[data-id="${{taskId}}"]`)?.classList.add('active');
  currentTaskId = taskId;
  stepCount = 0;
  logCount = 0;
  document.getElementById('log-count').textContent = '0 steps';

  const runBtn = document.getElementById('run-btn');
  runBtn.innerHTML = '<span class="spin"></span> Loading...';
  runBtn.disabled = true;

  try {{
    const res = await fetch('/reset', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{task_id: taskId}})
    }});
    const data = await res.json();
    const obs = data.observation;

    maxSteps = obs.max_steps;
    hintText = obs.hint || '';

    // Show task content
    document.getElementById('welcome').style.display = 'none';
    document.getElementById('task-content').style.display = 'block';

    // Task header
    const task = TASKS.tasks.find(t => t.task_id === taskId);
    document.getElementById('task-title').textContent = '📋 ' + obs.task_name;
    const dc = obs.difficulty === 'easy' ? 'be' : obs.difficulty === 'medium' ? 'bm' : 'bh';
    document.getElementById('task-badges').innerHTML =
      `<span class="badge ${{dc}}">${{obs.difficulty}}</span>`;

    // Schema + question
    document.getElementById('schema-box').textContent = obs.schema_ddl.trim();
    document.getElementById('q-box').textContent = obs.business_question.trim();

    // Hide hint initially
    document.getElementById('hint-box').style.display = 'none';

    // Reset UI
    document.getElementById('sql-input').value = '';
    document.getElementById('progress').style.width = '0%';
    document.getElementById('step-counter').textContent = `0 / ${{maxSteps}} steps`;
    resetScores();
    document.getElementById('fb-box').textContent = 'Write a SQL query above and click Run Query.';
    document.getElementById('fb-box').className = 'feedback-box';
    document.getElementById('fb-tip').textContent = '';
    document.getElementById('step-log').innerHTML = '<div class="empty"><div class="empty-icon">📝</div>Steps will appear here after you run queries.</div>';

    runBtn.innerHTML = '▶ Run Query';
    runBtn.disabled = false;
    runBtn.onclick = runStep;

  }} catch(e) {{
    runBtn.innerHTML = '▶ Run Query';
    runBtn.disabled = false;
    document.getElementById('fb-box').textContent = 'Error connecting: ' + e.message;
    document.getElementById('fb-box').className = 'feedback-box fb-err';
  }}
}}

function showHint() {{
  const hb = document.getElementById('hint-box');
  if (hintText) {{
    hb.textContent = '💡 Hint: ' + hintText;
    hb.style.display = 'block';
  }} else {{
    hb.textContent = '💡 No additional hint available for this task.';
    hb.style.display = 'block';
  }}
}}

async function resetTask() {{
  if (currentTaskId) await selectTask(currentTaskId);
}}

async function runStep() {{
  const sql = document.getElementById('sql-input').value.trim();
  if (!sql) {{
    document.getElementById('fb-box').textContent = '⚠️ Please enter a SQL query first.';
    document.getElementById('fb-box').className = 'feedback-box fb-partial';
    return;
  }}

  const runBtn = document.getElementById('run-btn');
  runBtn.innerHTML = '<span class="spin"></span> Running...';
  runBtn.disabled = true;

  try {{
    const res = await fetch('/step', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{sql_query: sql}})
    }});
    const data = await res.json();

    const reward = parseFloat(data.reward || 0);
    const done = data.done;
    const info = data.info || {{}};
    const obs = data.observation || {{}};

    stepCount++;
    logCount++;
    document.getElementById('step-counter').textContent = `${{stepCount}} / ${{maxSteps}} steps`;
    document.getElementById('log-count').textContent = logCount + ' step' + (logCount !== 1 ? 's' : '');
    document.getElementById('progress').style.width = (stepCount / maxSteps * 100) + '%';

    // Update scores
    const correctness = parseFloat(info.correctness || 0);
    const efficiency  = parseFloat(info.efficiency  || 0);
    const style       = parseFloat(info.style       || 0);

    setScore('sc-total',   reward,      reward >= .95 ? 'var(--green)' : reward >= .5 ? 'var(--amber)' : 'var(--red)');
    setScore('sc-correct', correctness, 'var(--green)');
    setScore('sc-eff',     efficiency,  'var(--blue)');
    setBar('correct', correctness, 'var(--green)');
    setBar('eff',     efficiency,  'var(--blue)');
    setBar('style',   style,       'var(--amber)');

    // Feedback
    const fb = document.getElementById('fb-box');
    const feedback = info.feedback || '';
    fb.textContent = feedback || (reward >= .95 ? '✅ Perfect answer!' : '');
    fb.className = 'feedback-box ' + (reward >= .95 ? 'fb-ok' : reward >= .5 ? 'fb-partial' : 'fb-err');

    // Tips
    const tip = document.getElementById('fb-tip');
    if (reward < 0.5 && stepCount < maxSteps) {{
      tip.textContent = '💡 Tip: Check your WHERE clause, JOIN conditions, and column aliases. Use the Hint button for more guidance.';
    }} else if (reward >= .95) {{
      tip.textContent = '🎉 Excellent SQL! Try the next task for a bigger challenge.';
    }} else if (done) {{
      tip.textContent = '⏱ Episode ended. Click Reset to try again.';
    }} else {{
      tip.textContent = '';
    }}

    // Error hint update
    if (obs.previous_error && reward < 0.5) {{
      const hb = document.getElementById('hint-box');
      hb.textContent = '⚠️ ' + obs.previous_error;
      hb.style.display = 'block';
    }}

    // Add to step log
    addStep(stepCount, sql, reward, done);

    // Done state
    if (done) {{
      if (reward >= .95) {{
        runBtn.innerHTML = '🎉 Done! Reset?';
      }} else {{
        runBtn.innerHTML = '↺ Reset to retry';
      }}
      runBtn.disabled = false;
      runBtn.onclick = resetTask;
    }} else {{
      runBtn.innerHTML = '▶ Run Query';
      runBtn.disabled = false;
      runBtn.onclick = runStep;
    }}

  }} catch(e) {{
    document.getElementById('fb-box').textContent = 'Request failed: ' + e.message;
    document.getElementById('fb-box').className = 'feedback-box fb-err';
    runBtn.innerHTML = '▶ Run Query';
    runBtn.disabled = false;
  }}
}}

function setScore(id, val, color) {{
  const el = document.getElementById(id);
  el.textContent = Math.round(val * 100) + '%';
  el.style.color = color;
}}

function setBar(id, val, color) {{
  const pct = Math.round(val * 100);
  document.getElementById('b-' + id).style.width = pct + '%';
  document.getElementById('b-' + id).style.background = color;
  document.getElementById('bv-' + id).textContent = pct + '%';
  document.getElementById('bv-' + id).style.color = color;
}}

function resetScores() {{
  ['sc-total','sc-correct','sc-eff'].forEach(id => {{
    document.getElementById(id).textContent = '—';
    document.getElementById(id).style.color = 'var(--muted)';
  }});
  ['correct','eff','style'].forEach(id => {{
    document.getElementById('b-' + id).style.width = '0%';
    document.getElementById('bv-' + id).textContent = '0%';
  }});
}}

function addStep(step, sql, reward, done) {{
  const log = document.getElementById('step-log');
  if (log.querySelector('.empty')) log.innerHTML = '';
  const cls = reward >= .9 ? 'r-hi' : reward >= .5 ? 'r-mid' : 'r-lo';
  const row = document.createElement('div');
  row.className = 'step-row';
  row.innerHTML = `
    <span class="step-n">Step ${{step}}</span>
    <span class="step-sql" title="${{sql.replace(/"/g,'&quot;')}}">${{sql.replace(/\n/g,' ')}}</span>
    <span class="step-r ${{cls}}">${{Math.round(reward*100)}}%</span>
    ${{done ? '<span style="color:var(--green);font-size:11px">done</span>' : ''}}`;
  log.appendChild(row);
  log.scrollTop = log.scrollHeight;
}}

function clearAll() {{
  document.getElementById('sql-input').value = '';
  document.getElementById('fb-box').textContent = 'Run a query to see feedback...';
  document.getElementById('fb-box').className = 'feedback-box';
  document.getElementById('fb-tip').textContent = '';
  document.getElementById('step-log').innerHTML = '<div class="empty"><div class="empty-icon">📝</div>Steps will appear here after you run queries.</div>';
  resetScores();
  stepCount = 0; logCount = 0;
  document.getElementById('step-counter').textContent = `0 / ${{maxSteps}} steps`;
  document.getElementById('log-count').textContent = '0 steps';
  document.getElementById('progress').style.width = '0%';
}}

// Keyboard shortcut: Ctrl+Enter to run
document.addEventListener('keydown', e => {{
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {{
    const btn = document.getElementById('run-btn');
    if (!btn.disabled) runStep();
  }}
}});

renderTasks();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return JSONResponse({
            "name": "SQLQueryEnv", "version": "1.0.0",
            "description": "Real-world SQL query environment for RL agents",
            "tasks": list(TASKS.keys()), "status": "ready",
        })
    tasks_data = {
        "tasks": [
            {"task_id": tid, "name": t["name"], "difficulty": t["difficulty"], "max_steps": t["max_steps"]}
            for tid, t in TASKS.items()
        ]
    }
    return HTMLResponse(build_html(json.dumps(tasks_data)))


@app.get("/api/info")
async def api_info():
    return {"name": "SQLQueryEnv", "version": "1.0.0",
            "description": "Real-world SQL query environment for RL agents",
            "tasks": list(TASKS.keys()), "status": "ready"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/reset")
async def reset(req: ResetRequest = ResetRequest()):
    result = await _env.reset(task_id=req.task_id)
    obs = result.observation
    return {"observation": obs.model_dump(), "reward": result.reward, "done": result.done, "info": result.info}


@app.post("/step")
async def step(req: StepRequest):
    action = SQLAction(sql_query=req.sql_query)
    result = await _env.step(action)
    obs = result.observation
    return {"observation": obs.model_dump(), "reward": result.reward, "done": result.done, "info": result.info}


@app.get("/state")
async def state():
    return await _env.state()


@app.get("/tasks")
async def list_tasks():
    return {"tasks": [
        {"task_id": tid, "name": t["name"], "difficulty": t["difficulty"], "max_steps": t["max_steps"]}
        for tid, t in TASKS.items()
    ]}


def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
