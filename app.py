"""
app.py - SQLQueryEnv with interactive web UI
Tasks injected server-side, all API endpoints preserved.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn, json

from env import SQLQueryEnv, SQLAction, TASKS

app = FastAPI(title="SQLQueryEnv", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
_env = SQLQueryEnv()

class StepRequest(BaseModel):
    sql_query: str

class ResetRequest(BaseModel):
    task_id: str | None = None


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SQLQueryEnv</title>
<style>
:root{--bg:#0d1117;--s1:#161b22;--s2:#21262d;--bd:#30363d;--blue:#58a6ff;--green:#3fb950;--amber:#d29922;--red:#f85149;--purple:#bc8cff;--txt:#e6edf3;--muted:#8b949e;--mono:'JetBrains Mono',monospace}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;height:100vh;display:flex;flex-direction:column;overflow:hidden}
.hdr{background:var(--s1);border-bottom:1px solid var(--bd);padding:12px 24px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.hdr-l{display:flex;align-items:center;gap:10px}
.hdr-icon{width:36px;height:36px;background:linear-gradient(135deg,#1f6feb,#58a6ff);border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}
.hdr-name{font-size:16px;font-weight:600}
.hdr-sub{font-size:11px;color:var(--muted)}
.live{display:flex;align-items:center;gap:6px;background:rgba(63,185,80,.1);border:1px solid rgba(63,185,80,.3);border-radius:20px;padding:4px 12px;font-size:12px;color:var(--green);font-weight:500}
.dot{width:7px;height:7px;border-radius:50%;background:var(--green);animation:blink 2s ease-in-out infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}

.layout{flex:1;display:grid;grid-template-columns:280px 1fr;overflow:hidden}
.sidebar{background:var(--s1);border-right:1px solid var(--bd);overflow-y:auto;display:flex;flex-direction:column}
.main{overflow-y:auto;padding:18px 20px;display:flex;flex-direction:column;gap:14px}

.sec{padding:14px;border-bottom:1px solid var(--bd)}
.sec-title{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;margin-bottom:10px}

.task-btn{width:100%;background:transparent;border:1px solid var(--bd);border-radius:8px;padding:10px 12px;margin-bottom:6px;cursor:pointer;text-align:left;color:var(--txt);transition:.15s}
.task-btn:last-child{margin-bottom:0}
.task-btn:hover{background:rgba(88,166,255,.07);border-color:var(--blue)}
.task-btn.active{background:rgba(88,166,255,.12);border-color:var(--blue)}
.tb-name{font-size:13px;font-weight:500;margin-bottom:4px}
.tb-row{display:flex;gap:5px}
.badge{font-size:10px;font-weight:600;padding:2px 7px;border-radius:4px;text-transform:uppercase}
.be{background:rgba(63,185,80,.15);color:var(--green)}
.bm{background:rgba(210,153,34,.15);color:var(--amber)}
.bh{background:rgba(248,81,73,.15);color:var(--red)}
.bs{background:rgba(139,148,158,.12);color:var(--muted)}

.ep{display:flex;align-items:center;gap:7px;padding:5px 0;font-size:11px;border-bottom:1px solid rgba(48,54,61,.5)}
.ep:last-child{border-bottom:none}
.mt{font-size:9px;font-weight:700;padding:2px 5px;border-radius:3px;min-width:32px;text-align:center}
.mg{background:rgba(63,185,80,.15);color:var(--green)}
.mp{background:rgba(88,166,255,.15);color:var(--blue)}
.ep-p{font-family:var(--mono);color:var(--txt)}
.ep-d{color:var(--muted);margin-left:auto}

.rw-row{display:flex;align-items:center;gap:8px;margin-bottom:6px}
.rw-l{font-size:11px;color:var(--muted);width:70px;flex-shrink:0}
.rw-bg{flex:1;height:4px;background:var(--bd);border-radius:2px;overflow:hidden}
.rw-f{height:100%;border-radius:2px}
.rw-v{font-size:11px;color:var(--muted);width:28px;text-align:right}

.bl-row{display:flex;justify-content:space-between;font-size:12px;color:var(--muted);padding:3px 0}

.card{background:var(--s2);border:1px solid var(--bd);border-radius:10px;overflow:hidden}
.ch{padding:10px 14px;border-bottom:1px solid var(--bd);display:flex;align-items:center;justify-content:space-between}
.ct{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.cb{padding:14px}

pre.sch{background:var(--s1);border:1px solid var(--bd);border-radius:7px;padding:10px;font-family:var(--mono);font-size:11px;color:#a5b4fc;line-height:1.65;max-height:160px;overflow-y:auto;white-space:pre-wrap;word-break:break-word;margin-bottom:10px}
.q-box{background:rgba(88,166,255,.06);border:1px solid rgba(88,166,255,.18);border-radius:7px;padding:11px 13px;font-size:13px;line-height:1.6;margin-bottom:8px}
.hint-box{background:rgba(210,153,34,.06);border:1px solid rgba(210,153,34,.2);border-radius:7px;padding:9px 12px;font-size:12px;color:#e3b341;line-height:1.5;margin-bottom:8px;display:none}
.prog-bg{height:3px;background:var(--bd);border-radius:2px;overflow:hidden;margin-bottom:10px}
.prog-f{height:100%;background:var(--blue);border-radius:2px;transition:.3s}

textarea{width:100%;background:var(--s1);border:1px solid var(--bd);border-radius:7px;padding:11px;font-family:var(--mono);font-size:12px;color:var(--txt);resize:vertical;min-height:100px;outline:none;transition:.15s border-color;line-height:1.6}
textarea:focus{border-color:var(--blue)}
textarea::placeholder{color:var(--muted)}

.btn-row{display:flex;gap:7px;flex-wrap:wrap;margin-top:9px}
.btn{padding:8px 15px;border-radius:7px;font-size:13px;font-weight:500;cursor:pointer;border:1px solid transparent;transition:.15s;display:inline-flex;align-items:center;gap:5px}
.btn:disabled{opacity:.4;cursor:not-allowed}
.btn-run{background:#1f6feb;border-color:#388bfd;color:#fff}
.btn-run:hover:not(:disabled){background:#388bfd}
.btn-ghost{background:transparent;border-color:var(--bd);color:var(--txt)}
.btn-ghost:hover{border-color:var(--blue);color:var(--blue)}

.score-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px}
.sc{background:var(--s1);border:1px solid var(--bd);border-radius:8px;padding:10px;text-align:center}
.sc-v{font-size:24px;font-weight:700;letter-spacing:-1px;margin-bottom:2px}
.sc-l{font-size:10px;color:var(--muted)}
.bar-row{display:flex;align-items:center;gap:8px;margin-bottom:7px}
.bar-l{font-size:11px;color:var(--muted);width:76px;flex-shrink:0}
.bar-bg{flex:1;height:5px;background:var(--bd);border-radius:3px;overflow:hidden}
.bar-f{height:100%;border-radius:3px;transition:.4s}
.bar-v{font-size:11px;font-weight:600;width:30px;text-align:right}

.fb{font-family:var(--mono);font-size:12px;background:var(--s1);border:1px solid var(--bd);border-radius:7px;padding:12px;min-height:60px;line-height:1.65;color:var(--muted);white-space:pre-wrap;word-break:break-word;transition:.2s}
.fb-ok{border-color:rgba(63,185,80,.4)!important;color:var(--green)!important}
.fb-mid{border-color:rgba(210,153,34,.4)!important;color:var(--amber)!important}
.fb-err{border-color:rgba(248,81,73,.4)!important;color:var(--red)!important}
.tip{font-size:11px;color:var(--muted);margin-top:8px;line-height:1.6}

.slog{max-height:160px;overflow-y:auto}
.sr{display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--bd);font-size:11px}
.sr:last-child{border-bottom:none}
.sn{font-family:var(--mono);color:var(--blue);min-width:46px}
.ss{flex:1;font-family:var(--mono);color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sv{font-weight:700;min-width:34px;text-align:right}
.rv-hi{color:var(--green)}.rv-mid{color:var(--amber)}.rv-lo{color:var(--red)}

.empty{display:flex;flex-direction:column;align-items:center;gap:6px;padding:24px;color:var(--muted);font-size:12px;text-align:center}
.spin{display:inline-block;width:12px;height:12px;border:2px solid rgba(255,255,255,.2);border-top-color:#fff;border-radius:50%;animation:rot .6s linear infinite}
@keyframes rot{to{transform:rotate(360deg)}}

.welcome{background:rgba(88,166,255,.05);border:1px solid rgba(88,166,255,.12);border-radius:8px;padding:24px;text-align:center;color:var(--muted);font-size:13px;line-height:1.7}

@media(max-width:650px){.layout{grid-template-columns:1fr}.sidebar{max-height:250px}}
</style>
</head>
<body>
<header class="hdr">
  <div class="hdr-l">
    <div class="hdr-icon">🧠</div>
    <div><div class="hdr-name">SQLQueryEnv</div><div class="hdr-sub">OpenEnv · Real-world SQL Environment for RL Agents</div></div>
  </div>
  <div class="live"><div class="dot"></div>Live · 3 Tasks Ready</div>
</header>

<div class="layout">
  <div class="sidebar">
    <div class="sec">
      <div class="sec-title">🎯 Tasks</div>
      <div id="tlist"></div>
    </div>
    <div class="sec">
      <div class="sec-title">🔌 API</div>
      <div class="ep"><span class="mt mg">GET</span><span class="ep-p">/</span><span class="ep-d">Info</span></div>
      <div class="ep"><span class="mt mp">POST</span><span class="ep-p">/reset</span><span class="ep-d">New episode</span></div>
      <div class="ep"><span class="mt mp">POST</span><span class="ep-p">/step</span><span class="ep-d">Submit SQL</span></div>
      <div class="ep"><span class="mt mg">GET</span><span class="ep-p">/state</span><span class="ep-d">State</span></div>
      <div class="ep"><span class="mt mg">GET</span><span class="ep-p">/tasks</span><span class="ep-d">List tasks</span></div>
      <div class="ep"><span class="mt mg">GET</span><span class="ep-p">/health</span><span class="ep-d">Health</span></div>
    </div>
    <div class="sec">
      <div class="sec-title">⚖️ Reward</div>
      <div class="rw-row"><span class="rw-l">Correctness</span><div class="rw-bg"><div class="rw-f" style="width:70%;background:var(--green)"></div></div><span class="rw-v">70%</span></div>
      <div class="rw-row"><span class="rw-l">Efficiency</span><div class="rw-bg"><div class="rw-f" style="width:20%;background:var(--blue)"></div></div><span class="rw-v">20%</span></div>
      <div class="rw-row"><span class="rw-l">Style</span><div class="rw-bg"><div class="rw-f" style="width:10%;background:var(--amber)"></div></div><span class="rw-v">10%</span></div>
      <div style="font-size:10px;color:var(--muted);margin-top:8px;line-height:1.6">Partial credit for near-correct answers. SQL errors → 0.05 to avoid reward cliffs.</div>
    </div>
    <div class="sec">
      <div class="sec-title">📊 Baseline</div>
      <div class="bl-row"><span>Easy</span><span style="color:var(--green);font-weight:600">95%</span></div>
      <div class="bl-row"><span>Medium</span><span style="color:var(--amber);font-weight:600">78%</span></div>
      <div class="bl-row"><span>Hard</span><span style="color:var(--red);font-weight:600">61%</span></div>
      <div class="bl-row" style="border-top:1px solid var(--bd);margin-top:4px;padding-top:4px"><span>Overall</span><span style="color:var(--blue);font-weight:600">78%</span></div>
    </div>
  </div>

  <div class="main">
    <div class="card">
      <div class="ch"><span class="ct" id="ttitle">📋 Task</span><span id="tbadge"></span></div>
      <div class="cb">
        <div id="welcome" class="welcome">
          <div style="font-size:28px;margin-bottom:8px">👈</div>
          <div><strong>Select a task</strong> from the left panel to begin.<br>You'll get a database schema and a business question to answer with SQL.</div>
        </div>
        <div id="tcontent" style="display:none">
          <div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px">Database Schema</div>
          <pre class="sch" id="schema"></pre>
          <div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px">Business Question</div>
          <div class="q-box" id="qbox"></div>
          <div class="hint-box" id="hintbox"></div>
          <div class="prog-bg"><div class="prog-f" id="prog" style="width:0%"></div></div>
          <div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px">Your SQL Query <span style="font-weight:400;text-transform:none;letter-spacing:0">(Ctrl+Enter to run)</span></div>
          <textarea id="sqlinput" placeholder="SELECT ...&#10;FROM ...&#10;WHERE status = 'completed'&#10;GROUP BY ...&#10;ORDER BY ...;"></textarea>
          <div class="btn-row">
            <button class="btn btn-run" id="runbtn" onclick="runStep()">▶ Run Query</button>
            <button class="btn btn-ghost" onclick="resetTask()">↺ Reset</button>
            <button class="btn btn-ghost" onclick="showHint()">💡 Hint</button>
            <button class="btn btn-ghost" onclick="clearAll()">✕ Clear</button>
          </div>
        </div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
      <div class="card">
        <div class="ch"><span class="ct">Score</span><span id="stepctr" style="font-size:11px;color:var(--muted)">—</span></div>
        <div class="cb">
          <div class="score-grid">
            <div class="sc"><div class="sc-v" id="sv-total" style="color:var(--muted)">—</div><div class="sc-l">Overall</div></div>
            <div class="sc"><div class="sc-v" id="sv-cor" style="color:var(--muted)">—</div><div class="sc-l">Correct</div></div>
            <div class="sc"><div class="sc-v" id="sv-eff" style="color:var(--muted)">—</div><div class="sc-l">Efficiency</div></div>
          </div>
          <div class="bar-row"><span class="bar-l">Correctness</span><div class="bar-bg"><div class="bar-f" id="bf-cor" style="width:0%;background:var(--green)"></div></div><span class="bar-v" id="bv-cor" style="color:var(--green)">0%</span></div>
          <div class="bar-row"><span class="bar-l">Efficiency</span><div class="bar-bg"><div class="bar-f" id="bf-eff" style="width:0%;background:var(--blue)"></div></div><span class="bar-v" id="bv-eff" style="color:var(--blue)">0%</span></div>
          <div class="bar-row"><span class="bar-l">Style</span><div class="bar-bg"><div class="bar-f" id="bf-sty" style="width:0%;background:var(--amber)"></div></div><span class="bar-v" id="bv-sty" style="color:var(--amber)">0%</span></div>
        </div>
      </div>
      <div class="card">
        <div class="ch"><span class="ct">Feedback</span></div>
        <div class="cb">
          <div class="fb" id="fbbox">Run a query to see feedback...</div>
          <div class="tip" id="fbtip"></div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="ch"><span class="ct">Step Log</span><span id="logcnt" style="font-size:11px;color:var(--muted)">0 steps</span></div>
      <div class="cb" style="padding:8px 14px">
        <div class="slog" id="slog"><div class="empty"><span style="font-size:24px">📝</span>Steps appear here after you run queries.</div></div>
      </div>
    </div>
  </div>
</div>

<script>
var TASKS = TASKS_PLACEHOLDER;

var cur = null, steps = 0, maxS = 5, hint = '', logs = 0;

function init() {
  var el = document.getElementById('tlist');
  el.innerHTML = '';
  TASKS.tasks.forEach(function(t) {
    var b = document.createElement('button');
    b.className = 'task-btn';
    b.setAttribute('data-id', t.task_id);
    var dc = t.difficulty === 'easy' ? 'be' : t.difficulty === 'medium' ? 'bm' : 'bh';
    b.innerHTML = '<div class="tb-name">' + t.name + '</div><div class="tb-row"><span class="badge ' + dc + '">' + t.difficulty + '</span><span class="badge bs">' + t.max_steps + ' steps</span></div>';
    b.onclick = function() { selectTask(t.task_id); };
    el.appendChild(b);
  });
}

function selectTask(id) {
  cur = id; steps = 0; logs = 0;
  document.querySelectorAll('.task-btn').forEach(function(b){ b.classList.remove('active'); });
  var ab = document.querySelector('[data-id="' + id + '"]');
  if (ab) ab.classList.add('active');
  document.getElementById('logcnt').textContent = '0 steps';

  var btn = document.getElementById('runbtn');
  btn.innerHTML = '<span class="spin"></span> Loading...';
  btn.disabled = true;

  fetch('/reset', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({task_id: id})})
  .then(function(r){ return r.json(); })
  .then(function(data) {
    var obs = data.observation;
    maxS = obs.max_steps;
    hint = obs.hint || '';

    document.getElementById('welcome').style.display = 'none';
    document.getElementById('tcontent').style.display = 'block';

    var t = TASKS.tasks.find(function(x){ return x.task_id === id; });
    document.getElementById('ttitle').textContent = '📋 ' + obs.task_name;
    var dc = obs.difficulty === 'easy' ? 'be' : obs.difficulty === 'medium' ? 'bm' : 'bh';
    document.getElementById('tbadge').innerHTML = '<span class="badge ' + dc + '">' + obs.difficulty + '</span>';

    document.getElementById('schema').textContent = obs.schema_ddl.trim();
    document.getElementById('qbox').textContent = obs.business_question.trim();
    document.getElementById('hintbox').style.display = 'none';
    document.getElementById('sqlinput').value = '';
    document.getElementById('prog').style.width = '0%';
    document.getElementById('stepctr').textContent = '0 / ' + maxS + ' steps';

    resetScores();
    document.getElementById('fbbox').textContent = 'Write SQL above and click Run Query.';
    document.getElementById('fbbox').className = 'fb';
    document.getElementById('fbtip').textContent = '';
    document.getElementById('slog').innerHTML = '<div class="empty"><span style="font-size:24px">📝</span>Steps appear here after you run queries.</div>';

    btn.innerHTML = '▶ Run Query';
    btn.disabled = false;
    btn.onclick = runStep;
  })
  .catch(function(e) {
    btn.innerHTML = '▶ Run Query';
    btn.disabled = false;
    document.getElementById('fbbox').textContent = 'Error: ' + e.message;
    document.getElementById('fbbox').className = 'fb fb-err';
  });
}

function showHint() {
  var hb = document.getElementById('hintbox');
  hb.textContent = hint ? '💡 Hint: ' + hint : '💡 No additional hint for this task. Check your JOIN, WHERE, and GROUP BY clauses.';
  hb.style.display = 'block';
}

function resetTask() { if (cur) selectTask(cur); }

function runStep() {
  var sql = document.getElementById('sqlinput').value.trim();
  if (!sql) {
    document.getElementById('fbbox').textContent = '⚠️ Please enter a SQL query first.';
    document.getElementById('fbbox').className = 'fb fb-mid';
    return;
  }
  var btn = document.getElementById('runbtn');
  btn.innerHTML = '<span class="spin"></span> Running...';
  btn.disabled = true;

  fetch('/step', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({sql_query: sql})})
  .then(function(r){ return r.json(); })
  .then(function(data) {
    var reward = parseFloat(data.reward || 0);
    var done = data.done;
    var info = data.info || {};
    var obs = data.observation || {};

    steps++; logs++;
    document.getElementById('stepctr').textContent = steps + ' / ' + maxS + ' steps';
    document.getElementById('logcnt').textContent = logs + ' step' + (logs !== 1 ? 's' : '');
    document.getElementById('prog').style.width = (steps / maxS * 100) + '%';

    var cor = parseFloat(info.correctness || 0);
    var eff = parseFloat(info.efficiency || 0);
    var sty = parseFloat(info.style || 0);
    var tc = reward >= .95 ? 'var(--green)' : reward >= .5 ? 'var(--amber)' : 'var(--red)';

    setScore('sv-total', reward, tc);
    setScore('sv-cor', cor, 'var(--green)');
    setScore('sv-eff', eff, 'var(--blue)');
    setBar('cor', cor, 'var(--green)');
    setBar('eff', eff, 'var(--blue)');
    setBar('sty', sty, 'var(--amber)');

    var fb = document.getElementById('fbbox');
    fb.textContent = info.feedback || (reward >= .95 ? '✅ Perfect answer!' : 'No feedback');
    fb.className = 'fb ' + (reward >= .95 ? 'fb-ok' : reward >= .5 ? 'fb-mid' : 'fb-err');

    var tip = document.getElementById('fbtip');
    if (reward >= .95) tip.textContent = '🎉 Excellent! Try a harder task next.';
    else if (done) tip.textContent = '⏱ Episode ended. Click Reset to try again with fresh state.';
    else if (reward < .5 && steps < maxS) tip.textContent = '💡 Check your WHERE clause, JOINs, and column aliases. Click Hint for guidance.';
    else tip.textContent = '';

    if (obs.previous_error && reward < .5) {
      var hb = document.getElementById('hintbox');
      hb.textContent = '⚠️ ' + obs.previous_error;
      hb.style.display = 'block';
    }

    addLog(steps, sql, reward, done);

    if (done) {
      btn.innerHTML = reward >= .95 ? '🎉 Done! Reset?' : '↺ Reset to retry';
      btn.disabled = false;
      btn.onclick = resetTask;
    } else {
      btn.innerHTML = '▶ Run Query';
      btn.disabled = false;
      btn.onclick = runStep;
    }
  })
  .catch(function(e) {
    document.getElementById('fbbox').textContent = 'Request failed: ' + e.message;
    document.getElementById('fbbox').className = 'fb fb-err';
    btn.innerHTML = '▶ Run Query';
    btn.disabled = false;
  });
}

function setScore(id, val, color) {
  var el = document.getElementById(id);
  el.textContent = Math.round(val * 100) + '%';
  el.style.color = color;
}

function setBar(id, val, color) {
  var p = Math.round(val * 100);
  var f = document.getElementById('bf-' + id);
  f.style.width = p + '%';
  f.style.background = color;
  var v = document.getElementById('bv-' + id);
  v.textContent = p + '%';
  v.style.color = color;
}

function resetScores() {
  ['sv-total','sv-cor','sv-eff'].forEach(function(id) {
    document.getElementById(id).textContent = '—';
    document.getElementById(id).style.color = 'var(--muted)';
  });
  ['cor','eff','sty'].forEach(function(id) {
    document.getElementById('bf-' + id).style.width = '0%';
    document.getElementById('bv-' + id).textContent = '0%';
  });
}

function addLog(n, sql, reward, done) {
  var log = document.getElementById('slog');
  if (log.querySelector('.empty')) log.innerHTML = '';
  var cls = reward >= .9 ? 'rv-hi' : reward >= .5 ? 'rv-mid' : 'rv-lo';
  var row = document.createElement('div');
  row.className = 'sr';
  row.innerHTML = '<span class="sn">Step ' + n + '</span><span class="ss" title="' + sql.replace(/"/g,'&quot;') + '">' + sql.replace(/\n/g,' ') + '</span><span class="sv ' + cls + '">' + Math.round(reward*100) + '%</span>' + (done ? '<span style="color:var(--green);font-size:10px">done</span>' : '');
  log.appendChild(row);
  log.scrollTop = log.scrollHeight;
}

function clearAll() {
  document.getElementById('sqlinput').value = '';
  document.getElementById('fbbox').textContent = 'Run a query to see feedback...';
  document.getElementById('fbbox').className = 'fb';
  document.getElementById('fbtip').textContent = '';
  document.getElementById('slog').innerHTML = '<div class="empty"><span style="font-size:24px">📝</span>Steps appear here after you run queries.</div>';
  resetScores();
  steps = 0; logs = 0;
  document.getElementById('stepctr').textContent = '0 / ' + maxS + ' steps';
  document.getElementById('logcnt').textContent = '0 steps';
  document.getElementById('prog').style.width = '0%';
}

document.addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    var btn = document.getElementById('runbtn');
    if (btn && !btn.disabled) runStep();
  }
});

init();
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
    tasks_data = {"tasks": [
        {"task_id": tid, "name": t["name"], "difficulty": t["difficulty"], "max_steps": t["max_steps"]}
        for tid, t in TASKS.items()
    ]}
    # Inject tasks directly into JS — no client-side fetch needed
    html = HTML_TEMPLATE.replace("TASKS_PLACEHOLDER", json.dumps(tasks_data))
    return HTMLResponse(html)


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
