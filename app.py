"""
app.py — FastAPI server exposing SQLQueryEnv via OpenEnv HTTP spec.
Serves a beautiful interactive web UI at / and all API endpoints unchanged.
"""

from typing import Any
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from env import SQLQueryEnv, SQLAction, TASKS

app = FastAPI(
    title="SQLQueryEnv",
    description="OpenEnv environment for SQL query correctness and optimization",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_env = SQLQueryEnv()


class StepRequest(BaseModel):
    sql_query: str

class ResetRequest(BaseModel):
    task_id: str | None = None


# ── Web UI ────────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SQLQueryEnv — OpenEnv</title>
<style>
  :root {
    --bg: #0f1117; --surface: #1a1d27; --card: #21253a;
    --border: #2e3350; --accent: #4f8ef7; --green: #22c55e;
    --amber: #f59e0b; --red: #ef4444; --text: #e2e8f0;
    --muted: #8892a4; --mono: 'JetBrains Mono', monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; min-height: 100vh; }

  /* Header */
  header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 16px 32px; display: flex; align-items: center; justify-content: space-between; }
  .logo { display: flex; align-items: center; gap: 12px; }
  .logo-icon { width: 36px; height: 36px; background: var(--accent); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 18px; }
  .logo-text { font-size: 18px; font-weight: 600; letter-spacing: -0.3px; }
  .logo-sub { font-size: 12px; color: var(--muted); }
  .status-pill { display: flex; align-items: center; gap: 6px; background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); border-radius: 20px; padding: 4px 12px; font-size: 12px; color: var(--green); }
  .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--green); animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

  /* Layout */
  main { max-width: 1200px; margin: 0 auto; padding: 32px 24px; display: grid; grid-template-columns: 340px 1fr; gap: 24px; }

  /* Cards */
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
  .card-header { padding: 14px 18px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 8px; }
  .card-title { font-size: 13px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: var(--muted); }
  .card-body { padding: 18px; }

  /* Task selector */
  .task-btn { width: 100%; text-align: left; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; margin-bottom: 8px; cursor: pointer; transition: all 0.15s; color: var(--text); }
  .task-btn:hover { border-color: var(--accent); background: rgba(79,142,247,0.05); }
  .task-btn.active { border-color: var(--accent); background: rgba(79,142,247,0.1); }
  .task-name { font-size: 14px; font-weight: 500; margin-bottom: 4px; }
  .task-meta { display: flex; align-items: center; gap: 8px; }
  .badge { font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 500; }
  .badge-easy { background: rgba(34,197,94,0.15); color: var(--green); }
  .badge-medium { background: rgba(245,158,11,0.15); color: var(--amber); }
  .badge-hard { background: rgba(239,68,68,0.15); color: var(--red); }
  .badge-steps { background: rgba(139,148,163,0.15); color: var(--muted); }

  /* Schema viewer */
  .schema-box { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px; font-family: var(--mono); font-size: 12px; color: #a5b4fc; line-height: 1.6; max-height: 200px; overflow-y: auto; white-space: pre-wrap; margin-bottom: 14px; }

  /* Question */
  .question-box { background: rgba(79,142,247,0.07); border: 1px solid rgba(79,142,247,0.2); border-radius: 8px; padding: 12px 14px; font-size: 13px; line-height: 1.6; margin-bottom: 14px; }
  .hint-box { background: rgba(245,158,11,0.07); border: 1px solid rgba(245,158,11,0.2); border-radius: 8px; padding: 10px 14px; font-size: 12px; color: var(--amber); line-height: 1.5; margin-bottom: 14px; }

  /* SQL editor */
  textarea { width: 100%; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px; font-family: var(--mono); font-size: 13px; color: var(--text); resize: vertical; min-height: 100px; transition: border-color 0.15s; outline: none; }
  textarea:focus { border-color: var(--accent); }

  /* Buttons */
  .btn-row { display: flex; gap: 8px; margin-top: 10px; }
  button { padding: 9px 18px; border-radius: 7px; font-size: 13px; font-weight: 500; cursor: pointer; border: none; transition: all 0.15s; }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-primary:hover { background: #3b7de8; }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-secondary { background: var(--surface); color: var(--text); border: 1px solid var(--border); }
  .btn-secondary:hover { border-color: var(--accent); }

  /* Score bar */
  .score-section { margin-top: 16px; }
  .score-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
  .score-label { font-size: 12px; color: var(--muted); width: 90px; flex-shrink: 0; }
  .bar-wrap { flex: 1; height: 6px; background: var(--surface); border-radius: 3px; overflow: hidden; }
  .bar { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
  .bar-green { background: var(--green); }
  .bar-amber { background: var(--amber); }
  .bar-blue { background: var(--accent); }
  .score-val { font-size: 12px; font-weight: 600; width: 36px; text-align: right; }

  /* Result panel */
  .result-box { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 14px; font-family: var(--mono); font-size: 12px; line-height: 1.7; min-height: 80px; white-space: pre-wrap; color: var(--muted); }
  .result-success { border-color: rgba(34,197,94,0.4); color: var(--green); }
  .result-error { border-color: rgba(239,68,68,0.4); color: var(--red); }
  .result-partial { border-color: rgba(245,158,11,0.4); color: var(--amber); }

  /* Steps log */
  .step-log { margin-top: 12px; max-height: 200px; overflow-y: auto; }
  .step-item { display: flex; align-items: flex-start; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 12px; }
  .step-item:last-child { border-bottom: none; }
  .step-num { color: var(--accent); font-family: var(--mono); min-width: 50px; }
  .step-reward { font-weight: 600; }
  .reward-high { color: var(--green); }
  .reward-mid { color: var(--amber); }
  .reward-low { color: var(--red); }

  /* Big score */
  .big-score { text-align: center; padding: 20px 0; }
  .big-num { font-size: 52px; font-weight: 700; letter-spacing: -2px; }
  .big-label { font-size: 13px; color: var(--muted); margin-top: 4px; }

  /* API docs section */
  .api-endpoint { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; display: flex; align-items: center; gap: 10px; font-family: var(--mono); font-size: 12px; }
  .method { padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 11px; }
  .method-get { background: rgba(34,197,94,0.15); color: var(--green); }
  .method-post { background: rgba(79,142,247,0.15); color: var(--accent); }
  .ep-path { color: var(--text); }
  .ep-desc { color: var(--muted); margin-left: auto; font-size: 11px; font-family: sans-serif; }

  /* Footer */
  footer { text-align: center; padding: 24px; color: var(--muted); font-size: 12px; border-top: 1px solid var(--border); margin-top: 20px; }

  /* Loading spinner */
  .spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  @media (max-width: 768px) { main { grid-template-columns: 1fr; } }
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-icon">🧠</div>
    <div>
      <div class="logo-text">SQLQueryEnv</div>
      <div class="logo-sub">OpenEnv · Real-world SQL Environment for RL Agents</div>
    </div>
  </div>
  <div class="status-pill"><div class="dot"></div> Live · 3 Tasks Ready</div>
</header>

<main>
  <!-- Left panel: task selector + API docs -->
  <div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-header"><span class="card-title">Select Task</span></div>
      <div class="card-body" id="task-list">
        <div style="color:var(--muted);font-size:13px">Loading tasks...</div>
      </div>
    </div>

    <div class="card" style="margin-bottom:16px">
      <div class="card-header"><span class="card-title">API Endpoints</span></div>
      <div class="card-body">
        <div class="api-endpoint"><span class="method method-get">GET</span><span class="ep-path">/</span><span class="ep-desc">Environment info</span></div>
        <div class="api-endpoint"><span class="method method-post">POST</span><span class="ep-path">/reset</span><span class="ep-desc">Start episode</span></div>
        <div class="api-endpoint"><span class="method method-post">POST</span><span class="ep-path">/step</span><span class="ep-desc">Submit SQL</span></div>
        <div class="api-endpoint"><span class="method method-get">GET</span><span class="ep-path">/state</span><span class="ep-desc">Current state</span></div>
        <div class="api-endpoint"><span class="method method-get">GET</span><span class="ep-path">/tasks</span><span class="ep-desc">List tasks</span></div>
        <div class="api-endpoint"><span class="method method-get">GET</span><span class="ep-path">/health</span><span class="ep-desc">Health check</span></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><span class="card-title">Reward Breakdown</span></div>
      <div class="card-body">
        <div class="score-row"><span class="score-label">Correctness</span><div class="bar-wrap"><div class="bar bar-green" style="width:70%"></div></div><span class="score-val" style="color:var(--green)">70%</span></div>
        <div class="score-row"><span class="score-label">Efficiency</span><div class="bar-wrap"><div class="bar bar-blue" style="width:20%"></div></div><span class="score-val" style="color:var(--accent)">20%</span></div>
        <div class="score-row"><span class="score-label">Style</span><div class="bar-wrap"><div class="bar bar-amber" style="width:10%"></div></div><span class="score-val" style="color:var(--amber)">10%</span></div>
        <div style="font-size:12px;color:var(--muted);margin-top:10px;line-height:1.6">Partial credit for partially correct rows. SQL errors return 0.05 to avoid reward cliffs.</div>
      </div>
    </div>
  </div>

  <!-- Right panel: interactive playground -->
  <div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-header"><span class="card-title">📋 Task</span><span id="task-badge" style="margin-left:auto"></span></div>
      <div class="card-body">
        <div id="schema-box" class="schema-box">Select a task to begin...</div>
        <div id="question-box" class="question-box" style="display:none"></div>
        <div id="hint-box" class="hint-box" style="display:none"></div>

        <label style="font-size:12px;color:var(--muted);font-weight:500;display:block;margin-bottom:6px">Your SQL Query</label>
        <textarea id="sql-input" placeholder="SELECT ...&#10;FROM ...&#10;WHERE ...;" spellcheck="false"></textarea>

        <div class="btn-row">
          <button class="btn-primary" id="run-btn" onclick="runStep()" disabled>▶ Run Query</button>
          <button class="btn-secondary" onclick="resetTask()">↺ Reset</button>
          <button class="btn-secondary" onclick="clearLog()">Clear Log</button>
        </div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
      <div class="card">
        <div class="card-header"><span class="card-title">Score</span></div>
        <div class="card-body">
          <div class="big-score">
            <div class="big-num" id="big-score">—</div>
            <div class="big-label" id="big-label">No submission yet</div>
          </div>
          <div class="score-section" id="score-bars" style="display:none">
            <div class="score-row"><span class="score-label">Correctness</span><div class="bar-wrap"><div class="bar bar-green" id="bar-correct" style="width:0%"></div></div><span class="score-val" id="val-correct">0</span></div>
            <div class="score-row"><span class="score-label">Efficiency</span><div class="bar-wrap"><div class="bar bar-blue" id="bar-eff" style="width:0%"></div></div><span class="score-val" id="val-eff">0</span></div>
            <div class="score-row"><span class="score-label">Style</span><div class="bar-wrap"><div class="bar bar-amber" id="bar-style" style="width:0%"></div></div><span class="score-val" id="val-style">0</span></div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Feedback</span></div>
        <div class="card-body">
          <div id="result-box" class="result-box">Run a query to see feedback...</div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><span class="card-title">Step Log</span><span id="step-count" style="margin-left:auto;font-size:12px;color:var(--muted)">0 steps</span></div>
      <div class="card-body">
        <div class="step-log" id="step-log">
          <div style="color:var(--muted);font-size:12px">Steps will appear here...</div>
        </div>
      </div>
    </div>
  </div>
</main>

<footer>
  SQLQueryEnv · OpenEnv Round 1 · Built by Aditya Agrawal · <a href="/docs" style="color:var(--accent);text-decoration:none">API Docs</a>
</footer>

<script>
const BASE = '';
let currentTaskId = null;
let stepCount = 0;
let totalSteps = 5;

async function loadTasks() {
  const res = await fetch(BASE + '/tasks');
  const data = await res.json();
  const el = document.getElementById('task-list');
  el.innerHTML = '';
  data.tasks.forEach(t => {
    const btn = document.createElement('button');
    btn.className = 'task-btn';
    btn.dataset.id = t.task_id;
    const diffClass = 'badge-' + t.difficulty;
    btn.innerHTML = `<div class="task-name">${t.name}</div>
      <div class="task-meta">
        <span class="badge ${diffClass}">${t.difficulty}</span>
        <span class="badge badge-steps">${t.max_steps} steps</span>
      </div>`;
    btn.onclick = () => selectTask(t.task_id);
    el.appendChild(btn);
  });
}

async function selectTask(taskId) {
  document.querySelectorAll('.task-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`[data-id="${taskId}"]`)?.classList.add('active');
  currentTaskId = taskId;
  stepCount = 0;
  updateStepCount();
  document.getElementById('run-btn').disabled = false;
  document.getElementById('sql-input').value = '';
  clearResultBox();
  clearStepLog();

  const res = await fetch(BASE + '/reset', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({task_id: taskId})
  });
  const data = await res.json();
  const obs = data.observation;

  totalSteps = obs.max_steps;
  document.getElementById('schema-box').textContent = obs.schema_ddl.trim();
  document.getElementById('question-box').textContent = obs.business_question;
  document.getElementById('question-box').style.display = 'block';

  const badge = document.getElementById('task-badge');
  const diffClass = 'badge-' + obs.difficulty;
  badge.innerHTML = `<span class="badge ${diffClass}">${obs.difficulty}</span>`;

  if (obs.hint) {
    document.getElementById('hint-box').textContent = '💡 ' + obs.hint;
    document.getElementById('hint-box').style.display = 'block';
  } else {
    document.getElementById('hint-box').style.display = 'none';
  }

  document.getElementById('big-score').textContent = '—';
  document.getElementById('big-label').textContent = 'Task ready — write your SQL';
  document.getElementById('score-bars').style.display = 'none';
}

async function resetTask() {
  if (currentTaskId) await selectTask(currentTaskId);
}

async function runStep() {
  const sql = document.getElementById('sql-input').value.trim();
  if (!sql) return;

  const btn = document.getElementById('run-btn');
  btn.innerHTML = '<span class="spinner"></span>';
  btn.disabled = true;

  try {
    const res = await fetch(BASE + '/step', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({sql_query: sql})
    });
    const data = await res.json();
    const reward = data.reward || 0;
    const info = data.info || {};
    stepCount++;
    updateStepCount();

    // Update score
    const score = reward;
    const scoreEl = document.getElementById('big-score');
    const labelEl = document.getElementById('big-label');
    scoreEl.textContent = (score * 100).toFixed(0) + '%';
    scoreEl.style.color = score >= 0.95 ? 'var(--green)' : score >= 0.5 ? 'var(--amber)' : 'var(--red)';

    if (data.done && score >= 0.95) {
      labelEl.textContent = '✅ Perfect! Episode complete';
    } else if (data.done) {
      labelEl.textContent = '⏱ Episode ended · ' + stepCount + '/' + totalSteps + ' steps';
    } else {
      labelEl.textContent = 'Step ' + stepCount + '/' + totalSteps;
    }

    // Update bars
    const correctness = info.correctness || 0;
    const efficiency  = info.efficiency  || 0;
    const style       = info.style       || 0;
    document.getElementById('score-bars').style.display = 'block';
    setBar('correct', correctness);
    setBar('eff', efficiency);
    setBar('style', style);

    // Feedback box
    const rb = document.getElementById('result-box');
    rb.textContent = info.feedback || 'No feedback';
    rb.className = 'result-box ' + (score >= 0.95 ? 'result-success' : score >= 0.5 ? 'result-partial' : 'result-error');

    // Step log
    addStepLog(stepCount, sql, reward, data.done);

    // Update hint if error
    const obs = data.observation;
    if (obs?.previous_error) {
      document.getElementById('hint-box').textContent = '⚠️ ' + obs.previous_error;
      document.getElementById('hint-box').style.display = 'block';
    }

    if (data.done) {
      btn.innerHTML = '↺ Reset to continue';
      btn.disabled = false;
      btn.onclick = resetTask;
    } else {
      btn.innerHTML = '▶ Run Query';
      btn.disabled = false;
      btn.onclick = runStep;
    }
  } catch(e) {
    document.getElementById('result-box').textContent = 'Error: ' + e.message;
    document.getElementById('result-box').className = 'result-box result-error';
    btn.innerHTML = '▶ Run Query';
    btn.disabled = false;
  }
}

function setBar(id, val) {
  const pct = Math.round(val * 100);
  document.getElementById('bar-' + id).style.width = pct + '%';
  document.getElementById('val-' + id).textContent = pct + '%';
}

function addStepLog(step, sql, reward, done) {
  const log = document.getElementById('step-log');
  if (log.querySelector('.muted-placeholder')) log.innerHTML = '';
  const cls = reward >= 0.9 ? 'reward-high' : reward >= 0.5 ? 'reward-mid' : 'reward-low';
  const item = document.createElement('div');
  item.className = 'step-item';
  item.innerHTML = `<span class="step-num">Step ${step}</span>
    <span style="flex:1;color:var(--muted);font-family:var(--mono);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${sql.replace(/\n/g,' ')}</span>
    <span class="step-reward ${cls}">${(reward*100).toFixed(0)}%</span>
    ${done ? '<span style="color:var(--green)">done</span>' : ''}`;
  log.appendChild(item);
  log.scrollTop = log.scrollHeight;
}

function clearResultBox() {
  const rb = document.getElementById('result-box');
  rb.textContent = 'Run a query to see feedback...';
  rb.className = 'result-box';
}

function clearStepLog() {
  const log = document.getElementById('step-log');
  log.innerHTML = '<div class="muted-placeholder" style="color:var(--muted);font-size:12px">Steps will appear here...</div>';
  stepCount = 0;
  updateStepCount();
}

function clearLog() {
  clearStepLog();
  clearResultBox();
  document.getElementById('big-score').textContent = '—';
  document.getElementById('big-label').textContent = 'No submission yet';
  document.getElementById('score-bars').style.display = 'none';
}

function updateStepCount() {
  document.getElementById('step-count').textContent = stepCount + ' steps';
}

loadTasks();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # If client wants JSON (API call), return JSON
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        from fastapi.responses import JSONResponse
        return JSONResponse({
            "name": "SQLQueryEnv",
            "version": "1.0.0",
            "description": "Real-world SQL query environment for RL agents",
            "tasks": list(TASKS.keys()),
            "status": "ready",
        })
    return HTMLResponse(HTML)


@app.get("/api/info")
async def api_info():
    return {
        "name": "SQLQueryEnv",
        "version": "1.0.0",
        "description": "Real-world SQL query environment for RL agents",
        "tasks": list(TASKS.keys()),
        "status": "ready",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/reset")
async def reset(req: ResetRequest = ResetRequest()):
    result = await _env.reset(task_id=req.task_id)
    obs = result.observation
    return {
        "observation": obs.model_dump(),
        "reward": result.reward,
        "done": result.done,
        "info": result.info,
    }


@app.post("/step")
async def step(req: StepRequest):
    action = SQLAction(sql_query=req.sql_query)
    result = await _env.step(action)
    obs = result.observation
    return {
        "observation": obs.model_dump(),
        "reward": result.reward,
        "done": result.done,
        "info": result.info,
    }


@app.get("/state")
async def state():
    return await _env.state()


@app.get("/tasks")
async def list_tasks():
    return {
        "tasks": [
            {
                "task_id": tid,
                "name": t["name"],
                "difficulty": t["difficulty"],
                "max_steps": t["max_steps"],
            }
            for tid, t in TASKS.items()
        ]
    }


def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
