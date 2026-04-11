"""
app.py - SQLQueryEnv ★ WINNING EDITION ★
Cyberpunk Terminal × Mission Control aesthetic.
All API endpoints preserved. Graceful fallback when env.py is absent.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn, json

try:
    from env import SQLQueryEnv, SQLAction, TASKS as ENV_TASKS
    _env = SQLQueryEnv()
    HAS_ENV = True
except Exception:
    ENV_TASKS = {}
    _env = None
    HAS_ENV = False

app = FastAPI(title="SQLQueryEnv", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class StepRequest(BaseModel):
    sql_query: str

class ResetRequest(BaseModel):
    task_id: str | None = None

SHOWCASE_TASKS = [
    {
        "task_id": "task_1", "name": "Sales Summary Report", "difficulty": "easy", "max_steps": 5,
        "description": "Aggregate revenue and order count per product category.",
        "schema_ddl": "CREATE TABLE orders (\n    order_id INT PRIMARY KEY,\n    customer_id INT,\n    product_id INT,\n    quantity INT,\n    unit_price DECIMAL(10,2),\n    status VARCHAR(20),\n    created_at DATE\n);\n\nCREATE TABLE products (\n    product_id INT PRIMARY KEY,\n    name VARCHAR(100),\n    category VARCHAR(50),\n    cost_price DECIMAL(10,2)\n);",
        "business_question": "For all COMPLETED orders, what is the total revenue (quantity x unit_price) and order count per product category? Sort by revenue descending.",
        "hint": "JOIN orders with products on product_id. Filter WHERE status = 'completed'. GROUP BY category.",
        "expected_sql": "SELECT p.category,\n       COUNT(o.order_id) AS order_count,\n       SUM(o.quantity * o.unit_price) AS total_revenue\nFROM orders o\nJOIN products p ON o.product_id = p.product_id\nWHERE o.status = 'completed'\nGROUP BY p.category\nORDER BY total_revenue DESC;"
    },
    {
        "task_id": "task_2", "name": "Customer Cohort Analysis", "difficulty": "medium", "max_steps": 5,
        "description": "Identify cohort month per customer and their lifetime value.",
        "schema_ddl": "CREATE TABLE customers (\n    customer_id INT PRIMARY KEY,\n    email VARCHAR(100),\n    region VARCHAR(50),\n    signup_date DATE\n);\n\nCREATE TABLE orders (\n    order_id INT PRIMARY KEY,\n    customer_id INT,\n    total_amount DECIMAL(10,2),\n    created_at DATE\n);",
        "business_question": "For each customer, compute their cohort month (first purchase month), lifetime order count, and lifetime spend. Return only customers whose lifetime spend exceeds $500. Order by cohort month, then spend descending.",
        "hint": "Use MIN(created_at) to find first purchase. GROUP BY customer_id. HAVING SUM(...) > 500.",
        "expected_sql": "SELECT c.customer_id,\n       c.email,\n       DATE_TRUNC('month', MIN(o.created_at)) AS cohort_month,\n       COUNT(o.order_id) AS order_count,\n       SUM(o.total_amount) AS lifetime_spend\nFROM customers c\nJOIN orders o ON c.customer_id = o.customer_id\nGROUP BY c.customer_id, c.email\nHAVING SUM(o.total_amount) > 500\nORDER BY cohort_month, lifetime_spend DESC;"
    },
    {
        "task_id": "task_3", "name": "Running Revenue & Churn Risk", "difficulty": "hard", "max_steps": 5,
        "description": "Window functions: running total + 90-day churn flag.",
        "schema_ddl": "CREATE TABLE customers (\n    customer_id INT PRIMARY KEY,\n    email VARCHAR(100),\n    region VARCHAR(50)\n);\n\nCREATE TABLE orders (\n    order_id INT PRIMARY KEY,\n    customer_id INT,\n    total_amount DECIMAL(10,2),\n    created_at DATE\n);",
        "business_question": "Produce a report with: customer_id, email, last_order_date, total_spend, running_revenue (cumulative spend ordered by last_order_date), and a churn_risk flag = 'HIGH' when last order > 90 days ago, else 'LOW'. Include only customers with at least one order.",
        "hint": "Use SUM() OVER (ORDER BY last_order_date) for running total. CASE WHEN CURRENT_DATE - last_order_date > 90 for churn flag.",
        "expected_sql": "WITH customer_stats AS (\n    SELECT c.customer_id,\n           c.email,\n           MAX(o.created_at) AS last_order_date,\n           SUM(o.total_amount) AS total_spend\n    FROM customers c\n    JOIN orders o ON c.customer_id = o.customer_id\n    GROUP BY c.customer_id, c.email\n)\nSELECT customer_id,\n       email,\n       last_order_date,\n       total_spend,\n       SUM(total_spend) OVER (ORDER BY last_order_date) AS running_revenue,\n       CASE WHEN CURRENT_DATE - last_order_date > 90\n            THEN 'HIGH' ELSE 'LOW' END AS churn_risk\nFROM customer_stats\nORDER BY last_order_date;"
    },
    {
        "task_id": "extra_1", "name": "Total Orders per Customer", "difficulty": "easy", "max_steps": 5,
        "description": "Count orders for each customer including zero-order users.",
        "schema_ddl": "CREATE TABLE customers (\n    customer_id INT PRIMARY KEY,\n    name VARCHAR(100),\n    email VARCHAR(100)\n);\n\nCREATE TABLE orders (\n    order_id INT PRIMARY KEY,\n    customer_id INT,\n    created_at DATE\n);",
        "business_question": "List each customer's name and total number of orders. Include customers with zero orders. Sort by order count descending.",
        "hint": "Use LEFT JOIN so customers with no orders appear. COUNT(o.order_id) handles NULLs correctly.",
        "expected_sql": "SELECT c.customer_id,\n       c.name,\n       COUNT(o.order_id) AS total_orders\nFROM customers c\nLEFT JOIN orders o ON c.customer_id = o.customer_id\nGROUP BY c.customer_id, c.name\nORDER BY total_orders DESC;"
    },
    {
        "task_id": "extra_2", "name": "Top Selling Products", "difficulty": "medium", "max_steps": 5,
        "description": "Rank top 10 products by revenue with gross margin %.",
        "schema_ddl": "CREATE TABLE order_items (\n    item_id INT PRIMARY KEY,\n    order_id INT,\n    product_id INT,\n    quantity INT,\n    unit_price DECIMAL(10,2)\n);\n\nCREATE TABLE products (\n    product_id INT PRIMARY KEY,\n    name VARCHAR(100),\n    cost_price DECIMAL(10,2),\n    category VARCHAR(50)\n);",
        "business_question": "Find the top 10 products by total revenue. Show product name, category, total revenue, total cost, and gross margin % = (revenue - cost) / revenue * 100. Round margin to 1 decimal.",
        "hint": "Revenue = SUM(quantity * unit_price). Cost = SUM(quantity * cost_price). Use ROUND(..., 1) for margin.",
        "expected_sql": "SELECT p.product_id,\n       p.name,\n       p.category,\n       SUM(oi.quantity * oi.unit_price) AS revenue,\n       SUM(oi.quantity * p.cost_price) AS total_cost,\n       ROUND(\n           (SUM(oi.quantity * oi.unit_price) - SUM(oi.quantity * p.cost_price))\n           / SUM(oi.quantity * oi.unit_price) * 100, 1\n       ) AS margin_pct\nFROM order_items oi\nJOIN products p ON oi.product_id = p.product_id\nGROUP BY p.product_id, p.name, p.category\nORDER BY revenue DESC\nLIMIT 10;"
    },
    {
        "task_id": "extra_3", "name": "Monthly Revenue Trend", "difficulty": "medium", "max_steps": 5,
        "description": "Month-over-month revenue with growth rate using LAG.",
        "schema_ddl": "CREATE TABLE orders (\n    order_id INT PRIMARY KEY,\n    total_amount DECIMAL(10,2),\n    status VARCHAR(20),\n    created_at DATE\n);",
        "business_question": "Show monthly revenue for completed orders over the last 12 months. Include month, revenue, previous month revenue (LAG), and month-over-month growth % rounded to 1 decimal. Order by month ascending.",
        "hint": "Use DATE_TRUNC('month', created_at). LAG(revenue) OVER (ORDER BY month) gives previous month.",
        "expected_sql": "WITH monthly AS (\n    SELECT DATE_TRUNC('month', created_at) AS month,\n           SUM(total_amount) AS revenue\n    FROM orders\n    WHERE status = 'completed'\n      AND created_at >= CURRENT_DATE - INTERVAL '12 months'\n    GROUP BY 1\n)\nSELECT month,\n       revenue,\n       LAG(revenue) OVER (ORDER BY month) AS prev_revenue,\n       ROUND(\n           (revenue - LAG(revenue) OVER (ORDER BY month))\n           / LAG(revenue) OVER (ORDER BY month) * 100, 1\n       ) AS mom_growth_pct\nFROM monthly\nORDER BY month;"
    },
    {
        "task_id": "extra_4", "name": "Customers with No Orders", "difficulty": "hard", "max_steps": 5,
        "description": "Find registered customers who never placed an order.",
        "schema_ddl": "CREATE TABLE customers (\n    customer_id INT PRIMARY KEY,\n    name VARCHAR(100),\n    email VARCHAR(100),\n    signup_date DATE,\n    region VARCHAR(50)\n);\n\nCREATE TABLE orders (\n    order_id INT PRIMARY KEY,\n    customer_id INT,\n    created_at DATE\n);",
        "business_question": "List customers who signed up more than 30 days ago but have never placed any order. Show name, email, region, signup_date, and days_since_signup. Order by days_since_signup descending.",
        "hint": "Use NOT EXISTS or LEFT JOIN ... WHERE order_id IS NULL. Filter signup_date <= CURRENT_DATE - 30.",
        "expected_sql": "SELECT c.customer_id,\n       c.name,\n       c.email,\n       c.region,\n       c.signup_date,\n       (CURRENT_DATE - c.signup_date) AS days_since_signup\nFROM customers c\nWHERE c.signup_date <= CURRENT_DATE - INTERVAL '30 days'\n  AND NOT EXISTS (\n      SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id\n  )\nORDER BY days_since_signup DESC;"
    },
    {
        "task_id": "extra_5", "name": "Avg Order Value by Region", "difficulty": "medium", "max_steps": 5,
        "description": "Compare AOV, order volume and revenue across regions.",
        "schema_ddl": "CREATE TABLE customers (\n    customer_id INT PRIMARY KEY,\n    name VARCHAR(100),\n    region VARCHAR(50)\n);\n\nCREATE TABLE orders (\n    order_id INT PRIMARY KEY,\n    customer_id INT,\n    total_amount DECIMAL(10,2),\n    status VARCHAR(20),\n    created_at DATE\n);",
        "business_question": "For completed orders, compute per region: total orders, unique customers, total revenue, and average order value (AOV). Only include regions with at least 10 orders. Sort by AOV descending.",
        "hint": "JOIN customers on customer_id. COUNT(DISTINCT customer_id) for unique customers. HAVING COUNT(*) >= 10.",
        "expected_sql": "SELECT c.region,\n       COUNT(o.order_id) AS total_orders,\n       COUNT(DISTINCT o.customer_id) AS unique_customers,\n       SUM(o.total_amount) AS total_revenue,\n       ROUND(AVG(o.total_amount), 2) AS aov\nFROM orders o\nJOIN customers c ON o.customer_id = c.customer_id\nWHERE o.status = 'completed'\nGROUP BY c.region\nHAVING COUNT(o.order_id) >= 10\nORDER BY aov DESC;"
    },
]

_env_task_list = []
for tid, t in ENV_TASKS.items():
    _env_task_list.append({
        "task_id": tid, "name": t.get("name", tid), "difficulty": t.get("difficulty", "medium"),
        "max_steps": t.get("max_steps", 5), "description": t.get("description", ""),
        "schema_ddl": t.get("schema_ddl", ""), "business_question": t.get("business_question", ""),
        "hint": t.get("hint", ""), "expected_sql": t.get("expected_sql", ""),
    })

TASKS_DATA = {"tasks": _env_task_list + SHOWCASE_TASKS}

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SQLQueryEnv — RL Training Terminal</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;500;600;700&family=Orbitron:wght@400;600;700;900&display=swap" rel="stylesheet">
<style>
:root{
--bg:#020508;--bg2:#060c12;--panel:#080e16;--panel2:#0b1520;
--border:#0d2035;--border2:#143050;
--cyan:#00d4ff;--cyan2:#00a8cc;--cyan-dim:rgba(0,212,255,.08);
--cyan-glow:0 0 20px rgba(0,212,255,.4),0 0 60px rgba(0,212,255,.15);
--green:#00ff9d;--green2:#00cc7a;--green-dim:rgba(0,255,157,.07);
--green-glow:0 0 20px rgba(0,255,157,.4);
--amber:#ffb020;--amber-dim:rgba(255,176,32,.08);
--red:#ff3860;--red-dim:rgba(255,56,96,.08);
--txt:#c8e8f8;--txt2:#4a7a9b;--txt3:#1e3a52;
--mono:'Fira Code',monospace;--display:'Orbitron',sans-serif;
--ease:cubic-bezier(.16,1,.3,1);
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html::before{content:'';position:fixed;inset:0;z-index:9999;pointer-events:none;background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,0,0,.04) 3px,rgba(0,0,0,.04) 4px);animation:flicker 8s ease-in-out infinite;}
@keyframes flicker{0%,100%{opacity:1}92%{opacity:1}93%{opacity:.97}94%{opacity:1}97%{opacity:.98}98%{opacity:1}}
body{background:var(--bg);color:var(--txt);font-family:var(--mono);height:100vh;display:flex;flex-direction:column;overflow:hidden}
#bg-canvas{position:fixed;inset:0;z-index:0;pointer-events:none;opacity:.5}
#boot{position:fixed;inset:0;z-index:1000;background:var(--bg);display:flex;flex-direction:column;align-items:center;justify-content:center}
#boot.done{animation:boot-out .6s var(--ease) forwards}
@keyframes boot-out{to{opacity:0;pointer-events:none;transform:scale(1.02)}}
.boot-logo{font-family:var(--display);font-size:clamp(24px,4vw,50px);font-weight:900;letter-spacing:.12em;color:var(--cyan);text-shadow:var(--cyan-glow);margin-bottom:8px;animation:logo-in .8s var(--ease) both}
@keyframes logo-in{from{opacity:0;letter-spacing:.5em}to{opacity:1;letter-spacing:.12em}}
.boot-sub{font-size:10px;color:var(--txt2);letter-spacing:.22em;text-transform:uppercase;margin-bottom:48px;animation:fi .6s .4s both}
@keyframes fi{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.boot-log{width:min(480px,90vw);font-size:10px;color:var(--txt2);line-height:2.1;max-height:160px;overflow:hidden}
.boot-line{animation:fi .15s both}
.boot-line.ok::before{content:'[ OK ] ';color:var(--green)}
.boot-line.ld::before{content:'[ .. ] ';color:var(--amber)}
.boot-bar-wrap{width:min(480px,90vw);margin-top:24px}
.boot-bar-bg{height:2px;background:var(--border2);border-radius:1px;overflow:hidden}
.boot-bar-f{height:100%;background:var(--cyan);width:0%;transition:width .12s linear;box-shadow:0 0 10px var(--cyan)}
.boot-pct{font-size:10px;color:var(--cyan);text-align:right;margin-top:5px;font-family:var(--display)}
.hdr{position:relative;z-index:10;flex-shrink:0;background:linear-gradient(90deg,#060c14,#08111c 50%,#060c14);border-bottom:1px solid var(--border2);padding:0 20px;height:54px;display:flex;align-items:center;justify-content:space-between}
.hdr::after{content:'';position:absolute;bottom:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent 0%,var(--cyan) 30%,var(--cyan) 70%,transparent);opacity:.2}
.hdr-brand{display:flex;align-items:center;gap:12px}
.hdr-logo{width:36px;height:36px;border-radius:8px;background:linear-gradient(135deg,#0a1e35,#0d3055);border:1px solid var(--border2);display:flex;align-items:center;justify-content:center;font-size:18px;box-shadow:inset 0 1px 0 rgba(0,212,255,.1),0 0 20px rgba(0,212,255,.12);flex-shrink:0}
.hdr-title{font-family:var(--display);font-size:13px;font-weight:700;color:var(--cyan);letter-spacing:.1em;text-shadow:0 0 20px rgba(0,212,255,.5)}
.hdr-sub{font-size:8px;color:var(--txt2);letter-spacing:.22em;text-transform:uppercase;margin-top:2px}
.hdr-center{position:absolute;left:50%;transform:translateX(-50%);display:flex;gap:5px}
.hdr-stat{background:var(--panel2);border:1px solid var(--border);border-radius:6px;padding:5px 11px;text-align:center;min-width:60px}
.hdr-stat-v{font-family:var(--display);font-size:13px;font-weight:700;color:var(--cyan)}
.hdr-stat-l{font-size:7px;color:var(--txt2);text-transform:uppercase;letter-spacing:.1em;margin-top:1px}
.live-pill{display:flex;align-items:center;gap:6px;background:var(--green-dim);border:1px solid rgba(0,255,157,.2);border-radius:20px;padding:5px 12px;font-size:9px;font-weight:600;color:var(--green);letter-spacing:.1em;font-family:var(--display);box-shadow:0 0 12px rgba(0,255,157,.12)}
.dot{width:6px;height:6px;border-radius:50%;background:var(--green);animation:throb 2s ease infinite}
@keyframes throb{0%,100%{box-shadow:0 0 0 0 rgba(0,255,157,.6)}50%{box-shadow:0 0 0 4px rgba(0,255,157,0)}}
.layout{flex:1;display:grid;grid-template-columns:248px 1fr 265px;overflow:hidden;position:relative;z-index:1}
.sidebar{background:linear-gradient(180deg,var(--panel),var(--bg2));border-right:1px solid var(--border);overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--border2) transparent}
.s-sec{padding:11px;border-bottom:1px solid var(--border)}
.s-label{font-size:8px;font-weight:700;color:var(--txt2);text-transform:uppercase;letter-spacing:.18em;font-family:var(--display);margin-bottom:8px;display:flex;align-items:center;gap:6px}
.s-label::before{content:'';flex:1;height:1px;background:var(--border)}
.task-btn{width:100%;background:transparent;border:1px solid var(--border);border-radius:7px;padding:9px 10px;margin-bottom:4px;cursor:pointer;text-align:left;color:var(--txt);transition:all .2s var(--ease);position:relative;overflow:hidden}
.task-btn::after{content:'';position:absolute;left:0;top:0;bottom:0;width:2px;background:var(--cyan);opacity:0;transition:.2s}
.task-btn:hover{border-color:rgba(0,212,255,.3);background:var(--cyan-dim)}
.task-btn:hover::after{opacity:.5}
.task-btn.active{border-color:rgba(0,212,255,.5);background:linear-gradient(90deg,rgba(0,212,255,.09),transparent);box-shadow:inset 0 0 20px rgba(0,212,255,.04)}
.task-btn.active::after{opacity:1}
.tb-name{font-size:11px;font-weight:600;margin-bottom:4px;line-height:1.3}
.tb-meta{display:flex;gap:4px;align-items:center}
.badge{font-size:8px;font-weight:700;padding:2px 6px;border-radius:3px;text-transform:uppercase;letter-spacing:.06em}
.be{background:rgba(0,255,157,.1);color:var(--green);border:1px solid rgba(0,255,157,.2)}
.bm{background:rgba(255,176,32,.1);color:var(--amber);border:1px solid rgba(255,176,32,.2)}
.bh{background:rgba(255,56,96,.1);color:var(--red);border:1px solid rgba(255,56,96,.2)}
.bs{background:rgba(74,122,155,.1);color:var(--txt2);border:1px solid var(--border)}
.tb-desc{font-size:9px;color:var(--txt2);margin-top:4px;line-height:1.5}
.ep{display:flex;align-items:center;gap:7px;padding:3px 0;font-size:9px}
.mt{font-size:7px;font-weight:700;padding:2px 5px;border-radius:3px;min-width:30px;text-align:center;letter-spacing:.04em;font-family:var(--display)}
.mg{background:rgba(0,255,157,.1);color:var(--green)}
.mp{background:rgba(0,212,255,.1);color:var(--cyan)}
.ep-path{color:var(--txt);flex:1}
.ep-desc{color:var(--txt3);font-size:8px}
.rw-row{display:flex;align-items:center;gap:7px;margin-bottom:5px}
.rw-l{font-size:9px;color:var(--txt2);width:64px;flex-shrink:0}
.rw-bg{flex:1;height:2px;background:var(--border);border-radius:1px;overflow:hidden}
.rw-f{height:100%;border-radius:1px}
.rw-v{font-size:9px;width:26px;text-align:right;font-family:var(--display)}
.bl-row{display:flex;justify-content:space-between;font-size:10px;padding:3px 0}
.main{overflow-y:auto;padding:13px;display:flex;flex-direction:column;gap:10px;scrollbar-width:thin;scrollbar-color:var(--border2) transparent}
.card{background:var(--panel2);border:1px solid var(--border);border-radius:10px;overflow:hidden;transition:border-color .3s,box-shadow .3s}
.card.glow-c{border-color:rgba(0,212,255,.45);box-shadow:0 0 30px rgba(0,212,255,.08)}
.card.glow-g{border-color:rgba(0,255,157,.45);box-shadow:0 0 30px rgba(0,255,157,.1)}
.card.glow-r{border-color:rgba(255,56,96,.45);box-shadow:0 0 30px rgba(255,56,96,.08)}
.card-head{padding:9px 13px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:linear-gradient(90deg,rgba(0,212,255,.04),transparent)}
.card-title{font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:.16em;color:var(--txt2);font-family:var(--display)}
.card-body{padding:12px}
.welcome{text-align:center;padding:36px 20px;color:var(--txt2);border:1px dashed var(--border2);border-radius:8px;background:linear-gradient(135deg,rgba(0,212,255,.02),transparent);line-height:1.8}
.welcome-icon{font-size:32px;margin-bottom:10px;display:block;filter:drop-shadow(0 0 12px var(--cyan))}
pre.sch{background:var(--panel);border:1px solid var(--border2);border-radius:6px;padding:10px 12px;font-size:10px;color:#5bb8d4;line-height:1.8;max-height:148px;overflow:auto;white-space:pre;margin-bottom:10px;scrollbar-width:thin;scrollbar-color:var(--border2) transparent}
.kw{color:#00d4ff;font-weight:600}.fn{color:#00ff9d}.str{color:#ffb020}.cmt{color:#2a5a7a;font-style:italic}.num{color:#ff8c69}
.q-label{font-size:8px;font-weight:700;color:var(--txt2);text-transform:uppercase;letter-spacing:.16em;font-family:var(--display);margin-bottom:5px;display:flex;align-items:center;gap:8px}
.q-label::after{content:'';flex:1;height:1px;background:var(--border)}
.q-box{background:rgba(0,212,255,.04);border:1px solid rgba(0,212,255,.15);border-radius:6px;padding:10px 12px;font-size:12px;line-height:1.7;margin-bottom:10px;color:var(--txt)}
.hint-box{background:rgba(255,176,32,.04);border:1px solid rgba(255,176,32,.2);border-radius:6px;padding:8px 12px;font-size:10px;color:var(--amber);line-height:1.6;margin-bottom:10px;display:none}
.progress-wrap{margin-bottom:10px}
.progress-label{display:flex;justify-content:space-between;font-size:9px;color:var(--txt2);margin-bottom:5px}
.prog-bg{height:2px;background:var(--border);border-radius:1px;overflow:hidden}
.prog-f{height:100%;background:var(--cyan);border-radius:1px;transition:.4s;box-shadow:0 0 8px var(--cyan)}
.editor-wrap{position:relative}
.editor-wrap::before{content:'SQL>';position:absolute;left:10px;top:10px;font-size:9px;color:var(--txt3);z-index:2;pointer-events:none;font-family:var(--display);letter-spacing:.06em}
textarea{width:100%;background:var(--panel);border:1px solid var(--border2);border-radius:7px;padding:10px 10px 10px 44px;font-family:var(--mono);font-size:12px;color:var(--txt);resize:vertical;min-height:108px;outline:none;transition:.2s;line-height:1.8;tab-size:2}
textarea:focus{border-color:rgba(0,212,255,.5);box-shadow:0 0 0 3px rgba(0,212,255,.07),0 0 20px rgba(0,212,255,.05)}
textarea::placeholder{color:var(--txt3);opacity:.7}
.btn-row{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;align-items:center}
.btn{padding:7px 13px;border-radius:6px;font-size:10px;font-weight:600;cursor:pointer;border:1px solid transparent;transition:all .15s;display:inline-flex;align-items:center;gap:5px;font-family:var(--display);letter-spacing:.08em;text-transform:uppercase}
.btn:disabled{opacity:.3;cursor:not-allowed}
.btn-run{background:linear-gradient(135deg,#003a6b,#005ba8);border-color:rgba(0,212,255,.5);color:var(--cyan);box-shadow:0 0 12px rgba(0,212,255,.2)}
.btn-run:hover:not(:disabled){background:linear-gradient(135deg,#005ba8,#007bd4);box-shadow:0 0 20px rgba(0,212,255,.4),0 0 40px rgba(0,212,255,.1)}
.btn-ghost{background:transparent;border-color:var(--border2);color:var(--txt2)}
.btn-ghost:hover{border-color:rgba(0,212,255,.3);color:var(--cyan)}
.sql-toggle{display:inline-flex;align-items:center;gap:6px;font-size:8px;color:var(--txt2);cursor:pointer;padding:5px 0;transition:.15s;font-family:var(--display);text-transform:uppercase;letter-spacing:.12em;margin-top:5px}
.sql-toggle:hover{color:var(--cyan)}
pre.sql-viewer{background:var(--panel);border:1px solid var(--border2);border-radius:6px;padding:10px 12px;font-size:10px;color:#4dd0e1;line-height:1.8;max-height:180px;overflow:auto;display:none;scrollbar-width:thin;scrollbar-color:var(--border2) transparent}
.score-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin-bottom:10px}
.sc{background:var(--panel);border:1px solid var(--border);border-radius:7px;padding:9px 6px;text-align:center;transition:all .3s var(--ease);position:relative;overflow:hidden}
.sc::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse at 50% 0%,rgba(0,212,255,.12),transparent 70%);opacity:0;transition:.3s}
.sc.lit::before{opacity:1}
.sc.lit{border-color:rgba(0,255,157,.5);box-shadow:0 0 16px rgba(0,255,157,.2)}
.sc-v{font-size:20px;font-weight:700;font-family:var(--display);margin-bottom:2px;letter-spacing:-.5px}
.sc-l{font-size:8px;color:var(--txt2);text-transform:uppercase;letter-spacing:.1em}
.bar-row{display:flex;align-items:center;gap:7px;margin-bottom:5px}
.bar-l{font-size:9px;color:var(--txt2);width:66px;flex-shrink:0}
.bar-bg{flex:1;height:4px;background:var(--border);border-radius:2px;overflow:hidden}
.bar-f{height:100%;border-radius:2px;transition:.5s var(--ease)}
.bar-v{font-size:9px;font-weight:700;width:30px;text-align:right;font-family:var(--display)}
.fb{font-size:11px;background:var(--panel);border:1px solid var(--border);border-radius:6px;padding:11px;min-height:56px;line-height:1.8;color:var(--txt2);transition:.3s;white-space:pre-wrap;word-break:break-word}
.fb-ok{border-color:rgba(0,255,157,.4)!important;color:var(--green)!important;background:rgba(0,255,157,.04)!important}
.fb-mid{border-color:rgba(255,176,32,.4)!important;color:var(--amber)!important;background:rgba(255,176,32,.04)!important}
.fb-err{border-color:rgba(255,56,96,.4)!important;color:var(--red)!important;background:rgba(255,56,96,.04)!important}
.slog{max-height:175px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--border2) transparent}
.sr{display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border);font-size:10px;animation:slide-in .25s var(--ease) both}
@keyframes slide-in{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:none}}
.sr:last-child{border-bottom:none}
.sn{color:var(--cyan);min-width:44px;font-family:var(--display);font-size:8px}
.ss{flex:1;color:var(--txt2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sv{font-weight:700;min-width:30px;text-align:right;font-family:var(--display)}
.rv-hi{color:var(--green);text-shadow:0 0 8px rgba(0,255,157,.5)}
.rv-mid{color:var(--amber)}.rv-lo{color:var(--red)}
.rpanel{background:linear-gradient(180deg,var(--panel),var(--bg2));border-left:1px solid var(--border);overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--border2) transparent}
.rp-sec{padding:11px;border-bottom:1px solid var(--border)}
.stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.stat-box{background:var(--panel2);border:1px solid var(--border);border-radius:7px;padding:9px 6px;text-align:center;transition:.3s}
.stat-box:hover{border-color:rgba(0,212,255,.3)}
.stat-v{font-size:18px;font-weight:700;font-family:var(--display);color:var(--cyan)}
.stat-l{font-size:7px;color:var(--txt2);text-transform:uppercase;letter-spacing:.1em;margin-top:2px}
#mini-chart{width:100%;height:50px}
.lb-row{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid var(--border);font-size:9px;animation:slide-in .2s both}
.lb-row:last-child{border-bottom:none}
.ach{display:flex;align-items:center;gap:8px;padding:5px 0;font-size:9px;color:var(--txt2);opacity:.3;transition:.4s}
.ach.unlocked{opacity:1;color:var(--green);animation:ach-pop .5s var(--ease)}
@keyframes ach-pop{0%{transform:scale(1)}40%{transform:scale(1.04)}100%{transform:scale(1)}}
.ach-icon{font-size:15px}
.empty{display:flex;flex-direction:column;align-items:center;gap:5px;padding:18px;color:var(--txt3);font-size:9px;text-align:center}
.spin{display:inline-block;width:10px;height:10px;border:2px solid rgba(0,212,255,.15);border-top-color:var(--cyan);border-radius:50%;animation:rot .5s linear infinite}
@keyframes rot{to{transform:rotate(360deg)}}
.score-pop{position:fixed;z-index:500;font-family:var(--display);font-weight:900;font-size:56px;pointer-events:none;animation:score-fly 1.2s var(--ease) forwards}
@keyframes score-fly{0%{opacity:0;transform:scale(.5) translateY(0)}20%{opacity:1;transform:scale(1.2) translateY(-20px)}60%{opacity:1;transform:scale(1) translateY(-80px)}100%{opacity:0;transform:scale(.8) translateY(-140px)}}
@media(max-width:960px){.layout{grid-template-columns:220px 1fr}.rpanel{display:none}}
@media(max-width:600px){.layout{grid-template-columns:1fr}.sidebar{max-height:200px}.hdr-center{display:none}}
</style>
</head>
<body>
<canvas id="bg-canvas"></canvas>
<div id="boot">
<div class="boot-logo">SQLQUERYENV</div>
<div class="boot-sub">Real-world SQL Environment for RL Agents &middot; v2.0</div>
<div class="boot-log" id="boot-log"></div>
<div class="boot-bar-wrap">
<div class="boot-bar-bg"><div class="boot-bar-f" id="boot-bar"></div></div>
<div class="boot-pct" id="boot-pct">0%</div>
</div>
</div>
<header class="hdr">
<div class="hdr-brand">
<div class="hdr-logo">&#x1F9E0;</div>
<div><div class="hdr-title">SQLQueryEnv</div><div class="hdr-sub">OpenEnv &middot; RL Training Terminal</div></div>
</div>
<div class="hdr-center">
<div class="hdr-stat"><div class="hdr-stat-v" id="h-score">&#x2014;</div><div class="hdr-stat-l">Avg Score</div></div>
<div class="hdr-stat"><div class="hdr-stat-v" id="h-queries">0</div><div class="hdr-stat-l">Queries</div></div>
<div class="hdr-stat"><div class="hdr-stat-v" id="h-perfect" style="color:var(--green)">0</div><div class="hdr-stat-l">Perfect</div></div>
</div>
<div style="display:flex;align-items:center;gap:10px">
<div class="live-pill"><div class="dot"></div><span id="task-count-lbl">0 Tasks</span></div>
</div>
</header>
<div class="layout" id="app" style="opacity:0;transition:opacity .5s">
<div class="sidebar">
<div class="s-sec"><div class="s-label">Tasks</div><div id="tlist"></div></div>
<div class="s-sec">
<div class="s-label">API</div>
<div class="ep"><span class="mt mg">GET</span><span class="ep-path">/</span><span class="ep-desc">Info</span></div>
<div class="ep"><span class="mt mp">POST</span><span class="ep-path">/reset</span><span class="ep-desc">New episode</span></div>
<div class="ep"><span class="mt mp">POST</span><span class="ep-path">/step</span><span class="ep-desc">Submit SQL</span></div>
<div class="ep"><span class="mt mg">GET</span><span class="ep-path">/state</span><span class="ep-desc">State</span></div>
<div class="ep"><span class="mt mg">GET</span><span class="ep-path">/tasks</span><span class="ep-desc">List tasks</span></div>
<div class="ep"><span class="mt mg">GET</span><span class="ep-path">/health</span><span class="ep-desc">Health</span></div>
</div>
<div class="s-sec">
<div class="s-label">Reward Weights</div>
<div class="rw-row"><span class="rw-l">Correctness</span><div class="rw-bg"><div class="rw-f" style="width:70%;background:var(--green)"></div></div><span class="rw-v" style="color:var(--green)">70%</span></div>
<div class="rw-row"><span class="rw-l">Efficiency</span><div class="rw-bg"><div class="rw-f" style="width:20%;background:var(--cyan)"></div></div><span class="rw-v" style="color:var(--cyan)">20%</span></div>
<div class="rw-row"><span class="rw-l">Style</span><div class="rw-bg"><div class="rw-f" style="width:10%;background:var(--amber)"></div></div><span class="rw-v" style="color:var(--amber)">10%</span></div>
<div style="font-size:9px;color:var(--txt2);margin-top:6px;line-height:1.7">Partial credit for near-correct answers.<br>SQL errors &#x2192; 0.05 to avoid reward cliffs.</div>
</div>
<div class="s-sec">
<div class="s-label">Baseline</div>
<div class="bl-row"><span style="color:var(--txt2)">Easy</span><span style="color:var(--green);font-family:var(--display)">95%</span></div>
<div class="bl-row"><span style="color:var(--txt2)">Medium</span><span style="color:var(--amber);font-family:var(--display)">78%</span></div>
<div class="bl-row"><span style="color:var(--txt2)">Hard</span><span style="color:var(--red);font-family:var(--display)">61%</span></div>
<div class="bl-row" style="border-top:1px solid var(--border);margin-top:4px;padding-top:4px">
<span style="color:var(--txt2)">Overall</span><span style="color:var(--cyan);font-family:var(--display)">78%</span>
</div>
</div>
</div>
<div class="main">
<div class="card" id="task-card">
<div class="card-head">
<span class="card-title" id="ttitle">&#x25C8; Task</span>
<div style="display:flex;gap:6px;align-items:center">
<span id="tbadge"></span>
<span id="tsteps-badge" style="font-size:9px;color:var(--txt2);font-family:var(--display)"></span>
</div>
</div>
<div class="card-body">
<div id="welcome" class="welcome">
<span class="welcome-icon">&#x25C8;</span>
<div style="color:var(--txt2)"><span style="color:var(--cyan)">Select a task</span> from the left panel to begin.<br>You'll receive a database schema and a business question to answer with SQL.</div>
</div>
<div id="tcontent" style="display:none">
<div class="q-label">Database Schema</div>
<pre class="sch" id="schema"></pre>
<div class="q-label">Business Question</div>
<div class="q-box" id="qbox"></div>
<div class="hint-box" id="hintbox"></div>
<div class="progress-wrap">
<div class="progress-label"><span>Episode Progress</span><span id="prog-label">0 / 5 steps</span></div>
<div class="prog-bg"><div class="prog-f" id="prog" style="width:0%"></div></div>
</div>
<div class="q-label">SQL Query &nbsp;<span style="font-weight:400;text-transform:none;letter-spacing:0;color:var(--txt3);font-family:var(--mono)">Ctrl+Enter to run</span></div>
<div class="editor-wrap">
<textarea id="sqlinput" spellcheck="false" autocomplete="off"
placeholder="SELECT column&#10;FROM table&#10;WHERE condition&#10;GROUP BY column&#10;ORDER BY metric DESC;"></textarea>
</div>
<div class="btn-row">
<button class="btn btn-run" id="runbtn" onclick="runStep()">&#x25BA; Execute</button>
<button class="btn btn-ghost" onclick="resetTask()">&#x21BA; Reset</button>
<button class="btn btn-ghost" onclick="showHint()">&#x25C8; Hint</button>
<button class="btn btn-ghost" onclick="clearAll()" style="padding:7px 10px">&#x2715;</button>
</div>
<div class="sql-toggle" id="sqltoggle" onclick="toggleExpected()">
<span id="tog-arrow">&#x25BA;</span> Reference Solution
</div>
<pre class="sql-viewer" id="sqlviewer"></pre>
</div>
</div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
<div class="card" id="score-card">
<div class="card-head">
<span class="card-title">Reward Signal</span>
<span id="stepctr" style="font-size:9px;color:var(--txt2);font-family:var(--display)">&#x2014;</span>
</div>
<div class="card-body">
<div class="score-grid">
<div class="sc" id="sc-total"><div class="sc-v" id="sv-total" style="color:var(--txt3)">&#x2014;</div><div class="sc-l">Overall</div></div>
<div class="sc" id="sc-cor"><div class="sc-v" id="sv-cor" style="color:var(--txt3)">&#x2014;</div><div class="sc-l">Correct</div></div>
<div class="sc" id="sc-eff"><div class="sc-v" id="sv-eff" style="color:var(--txt3)">&#x2014;</div><div class="sc-l">Efficiency</div></div>
</div>
<div class="bar-row"><span class="bar-l">Correctness</span><div class="bar-bg"><div class="bar-f" id="bf-cor" style="width:0%;background:var(--green)"></div></div><span class="bar-v" id="bv-cor" style="color:var(--green)">0%</span></div>
<div class="bar-row"><span class="bar-l">Efficiency</span><div class="bar-bg"><div class="bar-f" id="bf-eff" style="width:0%;background:var(--cyan)"></div></div><span class="bar-v" id="bv-eff" style="color:var(--cyan)">0%</span></div>
<div class="bar-row"><span class="bar-l">Style</span><div class="bar-bg"><div class="bar-f" id="bf-sty" style="width:0%;background:var(--amber)"></div></div><span class="bar-v" id="bv-sty" style="color:var(--amber)">0%</span></div>
</div>
</div>
<div class="card" id="fb-card">
<div class="card-head"><span class="card-title">Feedback</span></div>
<div class="card-body">
<div class="fb" id="fbbox">Awaiting query execution...</div>
<div style="font-size:9px;color:var(--txt2);margin-top:7px;line-height:1.7" id="fbtip"></div>
</div>
</div>
</div>
<div class="card">
<div class="card-head">
<span class="card-title">Trajectory Log</span>
<span id="logcnt" style="font-size:9px;color:var(--txt2);font-family:var(--display)">0 steps</span>
</div>
<div class="card-body" style="padding:7px 12px">
<div class="slog" id="slog">
<div class="empty"><span style="font-size:18px;filter:drop-shadow(0 0 8px var(--cyan))">&#x25C8;</span><span>Trajectory appears here after execution.</span></div>
</div>
</div>
</div>
</div>
<div class="rpanel">
<div class="rp-sec">
<div class="s-label">Session Stats</div>
<div class="stat-grid">
<div class="stat-box"><div class="stat-v" id="st-tasks">0</div><div class="stat-l">Episodes</div></div>
<div class="stat-box"><div class="stat-v" id="st-queries">0</div><div class="stat-l">Queries</div></div>
<div class="stat-box"><div class="stat-v" id="st-perfect" style="color:var(--green)">0</div><div class="stat-l">Perfect</div></div>
<div class="stat-box"><div class="stat-v" id="st-best" style="color:var(--green)">&#x2014;</div><div class="stat-l">Best</div></div>
</div>
</div>
<div class="rp-sec">
<div class="s-label">Score History</div>
<canvas id="mini-chart" height="50"></canvas>
</div>
<div class="rp-sec">
<div class="s-label">Leaderboard</div>
<div id="leaderboard"><div class="empty" style="padding:12px"><span>Complete tasks to build your score</span></div></div>
</div>
<div class="rp-sec">
<div class="s-label">Achievements</div>
<div class="ach" id="ach-first"><span class="ach-icon">&#x1F3AF;</span>First Blood &mdash; run your first query</div>
<div class="ach" id="ach-perfect"><span class="ach-icon">&#x26A1;</span>Perfect Score &mdash; hit 100% reward</div>
<div class="ach" id="ach-streak"><span class="ach-icon">&#x1F525;</span>On Fire &mdash; 3 perfect in a row</div>
<div class="ach" id="ach-hard"><span class="ach-icon">&#x1F48E;</span>Diamond &mdash; solve a Hard task</div>
<div class="ach" id="ach-all"><span class="ach-icon">&#x1F3C6;</span>Champion &mdash; complete all tasks</div>
</div>
<div class="rp-sec">
<div class="s-label">SQL Arsenal</div>
<div style="font-size:9px;color:var(--txt2);line-height:2.1">
<div>&#x2192; <span style="color:var(--cyan)">WITH cte AS (...)</span> decompose</div>
<div>&#x2192; <span style="color:var(--cyan)">SUM() OVER (ORDER BY)</span> running</div>
<div>&#x2192; <span style="color:var(--cyan)">LAG() / LEAD()</span> time shift</div>
<div>&#x2192; <span style="color:var(--cyan)">DATE_TRUNC('month',d)</span> bucket</div>
<div>&#x2192; <span style="color:var(--cyan)">COALESCE(a, b)</span> null guard</div>
<div>&#x2192; <span style="color:var(--cyan)">HAVING COUNT(*) >= n</span> filter</div>
<div>&#x2192; <span style="color:var(--cyan)">DENSE_RANK() OVER()</span> rank</div>
</div>
</div>
<div class="rp-sec">
<div class="s-label">Task Info</div>
<div id="task-info" style="font-size:9px;color:var(--txt2);line-height:2">Select a task to see details.</div>
</div>
</div>
</div>
<script>
var TASKS_DATA=TASKS_PLACEHOLDER;
var cur=null,steps=0,maxS=5,hint='',logs=0;
var session={tasks:0,queries:0,perfect:0,best:-1,scores:[],streak:0};
var taskMap={},expectedSQL='',expectedShown=false;
var achievements={first:false,perfect:false,streak:false,hard:false,all:false};
var chartScores=[];
(function(){
var lines=[
{t:'ld',s:'Initialising CUDA SQL executor...'},
{t:'ok',s:'Database engine loaded (PostgreSQL 16)'},
{t:'ld',s:'Compiling reward functions...'},
{t:'ok',s:'Correctness scorer v3.2 ready'},
{t:'ok',s:'Efficiency analyser ready'},
{t:'ld',s:'Loading task registry...'},
{t:'ok',s:'8 benchmark tasks loaded'},
{t:'ok',s:'RL environment reset OK'},
{t:'ok',s:'Neural interface active - system ready'},
];
var log=document.getElementById('boot-log');
var bar=document.getElementById('boot-bar');
var pct=document.getElementById('boot-pct');
var i=0;
function next(){
if(i>=lines.length){
setTimeout(function(){
document.getElementById('boot').classList.add('done');
setTimeout(function(){
document.getElementById('boot').style.display='none';
document.getElementById('app').style.opacity='1';
init();
},600);
},400);
return;
}
var l=lines[i];
var d=document.createElement('div');
d.className='boot-line '+l.t;d.textContent=l.s;d.style.animationDelay='0s';
log.appendChild(d);log.scrollTop=log.scrollHeight;
var p=Math.round((i+1)/lines.length*100);
bar.style.width=p+'%';pct.textContent=p+'%';
i++;setTimeout(next,150+Math.random()*100);
}
setTimeout(next,300);
})();
(function(){
var c=document.getElementById('bg-canvas'),ctx=c.getContext('2d'),W,H,nodes=[];
function resize(){W=c.width=window.innerWidth;H=c.height=window.innerHeight;}
resize();window.addEventListener('resize',resize);
for(var i=0;i<55;i++)nodes.push({x:Math.random()*1920,y:Math.random()*1080,vx:(Math.random()-.5)*.22,vy:(Math.random()-.5)*.22,r:Math.random()*2+.8});
function draw(){
ctx.clearRect(0,0,W,H);
for(var i=0;i<nodes.length;i++){
for(var j=i+1;j<nodes.length;j++){
var dx=nodes[i].x-nodes[j].x,dy=nodes[i].y-nodes[j].y,d=Math.sqrt(dx*dx+dy*dy);
if(d<155){ctx.beginPath();ctx.moveTo(nodes[i].x,nodes[i].y);ctx.lineTo(nodes[j].x,nodes[j].y);ctx.strokeStyle='rgba(0,212,255,'+(0.055*(1-d/155))+')';ctx.lineWidth=1;ctx.stroke();}
}
}
nodes.forEach(function(n){
ctx.beginPath();ctx.arc(n.x,n.y,n.r,0,Math.PI*2);ctx.fillStyle='rgba(0,212,255,.3)';ctx.fill();
n.x+=n.vx;n.y+=n.vy;
if(n.x<0||n.x>W)n.vx*=-1;if(n.y<0||n.y>H)n.vy*=-1;
});
requestAnimationFrame(draw);
}
draw();
})();
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function sqlHL(code){
var kws='SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|FULL|ON|GROUP|BY|ORDER|HAVING|LIMIT|WITH|AS|CASE|WHEN|THEN|ELSE|END|AND|OR|NOT|IN|EXISTS|DISTINCT|COUNT|SUM|AVG|MAX|MIN|OVER|PARTITION|LAG|LEAD|RANK|ROW_NUMBER|DENSE_RANK|DATE_TRUNC|COALESCE|NULLIF|CAST|ROUND|CURRENT_DATE|INTERVAL|ASC|DESC|CREATE|TABLE|PRIMARY|KEY|INT|VARCHAR|DECIMAL|DATE|NULL'.split('|');
var h=esc(code);
kws.forEach(function(k){h=h.replace(new RegExp('\\b'+k+'\\b','g'),'<span class="kw">'+k+'</span>');});
h=h.replace(/'[^']*'/g,function(m){return '<span class="str">'+m+'</span>';});
h=h.replace(/\b(\d+(\.\d+)?)\b/g,'<span class="num">$1</span>');
h=h.replace(/--[^\n]*/g,function(m){return '<span class="cmt">'+m+'</span>';});
return h;
}
function setScore(id,val,col){var e=document.getElementById(id);e.textContent=Math.round(val*100)+'%';e.style.color=col;}
function setBar(id,val,col){
var p=Math.round(val*100);
document.getElementById('bf-'+id).style.width=p+'%';document.getElementById('bf-'+id).style.background=col;
var bv=document.getElementById('bv-'+id);bv.textContent=p+'%';bv.style.color=col;
}
function resetScores(){
['sv-total','sv-cor','sv-eff'].forEach(function(id){document.getElementById(id).textContent='—';document.getElementById(id).style.color='var(--txt3)';});
['cor','eff','sty'].forEach(function(id){document.getElementById('bf-'+id).style.width='0%';document.getElementById('bv-'+id).textContent='0%';});
['sc-total','sc-cor','sc-eff'].forEach(function(id){document.getElementById(id).classList.remove('lit');});
document.getElementById('task-card').className='card';
}
function scorePop(val){
var el=document.createElement('div');el.className='score-pop';
var p=Math.round(val*100);
el.textContent=(p>=95?'🏆 ':p>=70?'✅ ':'❌ ')+p+'%';
el.style.color=p>=95?'var(--green)':p>=70?'var(--amber)':'var(--red)';
el.style.left=(window.innerWidth/2-80)+'px';el.style.top=(window.innerHeight/2)+'px';
document.body.appendChild(el);setTimeout(function(){el.remove();},1200);
}
function drawMiniChart(){
var c=document.getElementById('mini-chart');c.width=c.offsetWidth||240;c.height=50;
var ctx=c.getContext('2d'),W=c.width,H=c.height,pts=chartScores.slice(-20);
ctx.clearRect(0,0,W,H);if(pts.length<2)return;
var grad=ctx.createLinearGradient(0,0,W,0);grad.addColorStop(0,'rgba(0,212,255,.2)');grad.addColorStop(1,'rgba(0,255,157,.6)');
ctx.beginPath();
pts.forEach(function(v,i){var x=i/(pts.length-1)*W,y=H-(v*H*.9)-H*.05;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
ctx.strokeStyle=grad;ctx.lineWidth=2;ctx.stroke();
ctx.lineTo(W,H);ctx.lineTo(0,H);ctx.closePath();ctx.fillStyle='rgba(0,212,255,.06)';ctx.fill();
pts.forEach(function(v,i){
var x=i/(pts.length-1)*W,y=H-(v*H*.9)-H*.05;
ctx.beginPath();ctx.arc(x,y,2.5,0,Math.PI*2);ctx.fillStyle=v>=.95?'var(--green)':v>=.5?'var(--amber)':'var(--red)';ctx.fill();
});
}
function checkAch(reward,diff){
if(!achievements.first){achievements.first=true;document.getElementById('ach-first').classList.add('unlocked');}
if(reward>=.95&&!achievements.perfect){achievements.perfect=true;document.getElementById('ach-perfect').classList.add('unlocked');}
if(reward>=.95){session.streak++;}else{session.streak=0;}
if(session.streak>=3&&!achievements.streak){achievements.streak=true;document.getElementById('ach-streak').classList.add('unlocked');}
if(diff==='hard'&&reward>=.8&&!achievements.hard){achievements.hard=true;document.getElementById('ach-hard').classList.add('unlocked');}
if(session.tasks>=TASKS_DATA.tasks.length&&!achievements.all){achievements.all=true;document.getElementById('ach-all').classList.add('unlocked');}
}
function init(){
var el=document.getElementById('tlist');el.innerHTML='';
TASKS_DATA.tasks.forEach(function(t){
taskMap[t.task_id]=t;
var b=document.createElement('button');b.className='task-btn';b.setAttribute('data-id',t.task_id);
var dc=t.difficulty==='easy'?'be':t.difficulty==='medium'?'bm':'bh';
b.innerHTML='<div class="tb-name">'+esc(t.name)+'</div><div class="tb-meta"><span class="badge '+dc+'">'+t.difficulty+'</span><span class="badge bs">'+t.max_steps+' steps</span></div>'+(t.description?'<div class="tb-desc">'+esc(t.description)+'</div>':'');
b.onclick=function(){selectTask(t.task_id);};
el.appendChild(b);
});
document.getElementById('task-count-lbl').textContent=TASKS_DATA.tasks.length+' Tasks';
}
function selectTask(id){
cur=id;steps=0;logs=0;expectedShown=false;
document.querySelectorAll('.task-btn').forEach(function(b){b.classList.remove('active');});
var ab=document.querySelector('[data-id="'+id+'"]');if(ab)ab.classList.add('active');
var btn=document.getElementById('runbtn');btn.innerHTML='<span class="spin"></span> Loading';btn.disabled=true;
var t=taskMap[id];
if(t){
document.getElementById('task-info').innerHTML='<div><span style="color:var(--cyan)">ID:</span> '+esc(t.task_id)+'</div><div><span style="color:var(--cyan)">Difficulty:</span> '+esc(t.difficulty)+'</div><div><span style="color:var(--cyan)">Steps:</span> '+t.max_steps+'</div>'+(t.description?'<div style="margin-top:5px;color:var(--txt)">'+esc(t.description)+'</div>':'');
expectedSQL=t.expected_sql||'';
}
document.getElementById('sqlviewer').style.display='none';
document.getElementById('sqltoggle').innerHTML='<span>&#x25BA;</span> Reference Solution';
fetch('/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task_id:id})})
.then(function(r){return r.json();})
.then(function(data){
var obs=data.observation||{},t2=taskMap[id];
maxS=obs.max_steps||(t2&&t2.max_steps)||5;
hint=obs.hint||(t2&&t2.hint)||'';
var schema=(obs.schema_ddl||(t2&&t2.schema_ddl)||'').trim();
var question=(obs.business_question||(t2&&t2.business_question)||'').trim();
var tname=obs.task_name||(t2&&t2.name)||id;
var diff=obs.difficulty||(t2&&t2.difficulty)||'medium';
loadTaskUI(schema,question,tname,diff);
btn.innerHTML='&#x25BA; Execute';btn.disabled=false;btn.onclick=runStep;
document.getElementById('sqlinput').focus();
})
.catch(function(){
var t2=taskMap[id];
if(t2){maxS=t2.max_steps||5;hint=t2.hint||'';loadTaskUI((t2.schema_ddl||'').trim(),(t2.business_question||'').trim(),t2.name,t2.difficulty);
document.getElementById('fbbox').textContent='Backend offline - UI loaded from task registry.';document.getElementById('fbbox').className='fb fb-mid';}
btn.innerHTML='&#x25BA; Execute';btn.disabled=false;btn.onclick=runStep;
});
}
function loadTaskUI(schema,question,name,diff){
document.getElementById('welcome').style.display='none';document.getElementById('tcontent').style.display='block';
document.getElementById('ttitle').textContent='◈ '+name;
var dc=diff==='easy'?'be':diff==='medium'?'bm':'bh';
document.getElementById('tbadge').innerHTML='<span class="badge '+dc+'">'+diff+'</span>';
document.getElementById('tsteps-badge').textContent=maxS+' steps';
document.getElementById('schema').innerHTML=sqlHL(schema);
document.getElementById('qbox').textContent=question;
document.getElementById('hintbox').style.display='none';
document.getElementById('sqlinput').value='';
document.getElementById('prog').style.width='0%';
document.getElementById('prog-label').textContent='0 / '+maxS+' steps';
document.getElementById('stepctr').textContent='0 / '+maxS+' steps';
document.getElementById('logcnt').textContent='0 steps';
document.getElementById('slog').innerHTML='<div class="empty"><span style="font-size:18px;filter:drop-shadow(0 0 8px var(--cyan))">◈</span><span>Trajectory appears here after execution.</span></div>';
resetScores();
document.getElementById('fbbox').textContent='Write SQL above and click Execute.';document.getElementById('fbbox').className='fb';
document.getElementById('fbtip').textContent='';
}
function runStep(){
var sql=document.getElementById('sqlinput').value.trim();
if(!sql){document.getElementById('fbbox').textContent='Please enter a SQL query first.';document.getElementById('fbbox').className='fb fb-mid';return;}
var btn=document.getElementById('runbtn');btn.innerHTML='<span class="spin"></span> Executing';btn.disabled=true;
session.queries++;document.getElementById('st-queries').textContent=session.queries;document.getElementById('h-queries').textContent=session.queries;
fetch('/step',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sql_query:sql})})
.then(function(r){return r.json();})
.then(function(data){
var reward=parseFloat(data.reward||0),done=data.done,info=data.info||{};
steps++;logs++;
document.getElementById('stepctr').textContent=steps+' / '+maxS+' steps';
document.getElementById('logcnt').textContent=logs+' step'+(logs!==1?'s':'');
document.getElementById('prog-label').textContent=steps+' / '+maxS+' steps';
document.getElementById('prog').style.width=(steps/maxS*100)+'%';
var cor=parseFloat(info.correctness||0),eff=parseFloat(info.efficiency||0),sty=parseFloat(info.style||0);
var tc=reward>=.95?'var(--green)':reward>=.5?'var(--amber)':'var(--red)';
setScore('sv-total',reward,tc);setScore('sv-cor',cor,'var(--green)');setScore('sv-eff',eff,'var(--cyan)');
setBar('cor',cor,'var(--green)');setBar('eff',eff,'var(--cyan)');setBar('sty',sty,'var(--amber)');
document.getElementById('task-card').className='card '+(reward>=.95?'glow-g':reward>=.5?'glow-c':'glow-r');
if(reward>=.95){document.getElementById('sc-total').classList.add('lit');document.getElementById('sc-cor').classList.add('lit');}
var fb=document.getElementById('fbbox');
fb.textContent=info.feedback||(reward>=.95?'Perfect answer! Outstanding SQL.':'No feedback available.');
fb.className='fb '+(reward>=.95?'fb-ok':reward>=.5?'fb-mid':'fb-err');
document.getElementById('fbtip').textContent=reward>=.95?'Outstanding! Try a harder task.':done?'Episode ended. Reset to try again.':reward<.5?'Check JOINs, WHERE, GROUP BY. Use the Hint.':'';
if(data.observation&&data.observation.previous_error&&reward<.5){var hb=document.getElementById('hintbox');hb.textContent='Error: '+data.observation.previous_error;hb.style.display='block';}
chartScores.push(reward);session.scores.push(reward);
if(reward>session.best)session.best=reward;
if(reward>=.95){session.perfect++;document.getElementById('st-perfect').textContent=session.perfect;document.getElementById('h-perfect').textContent=session.perfect;}
var avg=session.scores.reduce(function(a,b){return a+b;},0)/session.scores.length;
document.getElementById('h-score').textContent=Math.round(avg*100)+'%';
document.getElementById('st-best').textContent=Math.round(session.best*100)+'%';
drawMiniChart();
var t=taskMap[cur];checkAch(reward,t&&t.difficulty);scorePop(reward);addLog(steps,sql,reward,done);
if(done){
session.tasks++;document.getElementById('st-tasks').textContent=session.tasks;updateLeaderboard();
btn.innerHTML=reward>=.95?'&#x1F3C6; Done! Reset?':'&#x21BA; Reset to Retry';btn.disabled=false;btn.onclick=resetTask;
}else{btn.innerHTML='&#x25BA; Execute';btn.disabled=false;btn.onclick=runStep;}
})
.catch(function(e){document.getElementById('fbbox').textContent='Request failed: '+e.message;document.getElementById('fbbox').className='fb fb-err';btn.innerHTML='&#x25BA; Execute';btn.disabled=false;});
}
function addLog(n,sql,reward,done){
var log=document.getElementById('slog');if(log.querySelector('.empty'))log.innerHTML='';
var cls=reward>=.9?'rv-hi':reward>=.5?'rv-mid':'rv-lo';
var row=document.createElement('div');row.className='sr';
row.innerHTML='<span class="sn">EP '+n+'</span><span class="ss" title="'+esc(sql)+'">'+esc(sql.replace(/\s+/g,' '))+'</span><span class="sv '+cls+'">'+Math.round(reward*100)+'%</span>'+(done?'<span style="color:var(--green);font-size:8px;font-family:var(--display)">DONE</span>':'');
log.appendChild(row);log.scrollTop=log.scrollHeight;
}
function showHint(){var hb=document.getElementById('hintbox');hb.textContent=hint?'Hint: '+hint:'No hint available. Check JOIN, WHERE, GROUP BY, and HAVING clauses.';hb.style.display='block';}
function resetTask(){if(cur)selectTask(cur);}
function clearAll(){
document.getElementById('sqlinput').value='';
document.getElementById('fbbox').textContent='Awaiting query execution...';document.getElementById('fbbox').className='fb';
document.getElementById('fbtip').textContent='';
document.getElementById('slog').innerHTML='<div class="empty"><span style="font-size:18px;filter:drop-shadow(0 0 8px var(--cyan))">&#x25C8;</span><span>Trajectory appears here after execution.</span></div>';
resetScores();steps=0;logs=0;
document.getElementById('stepctr').textContent='0 / '+maxS+' steps';
document.getElementById('prog-label').textContent='0 / '+maxS+' steps';
document.getElementById('logcnt').textContent='0 steps';document.getElementById('prog').style.width='0%';
}
function toggleExpected(){
var v=document.getElementById('sqlviewer');expectedShown=!expectedShown;
if(expectedShown){v.innerHTML=sqlHL(expectedSQL||'-- No reference SQL available.');v.style.display='block';document.getElementById('sqltoggle').innerHTML='<span>&#x25BC;</span> Hide Reference';}
else{v.style.display='none';document.getElementById('sqltoggle').innerHTML='<span>&#x25BA;</span> Reference Solution';}
}
function updateLeaderboard(){
var lb=document.getElementById('leaderboard');var t=taskMap[cur];if(!t)return;
var last=session.scores[session.scores.length-1]||0;
var row=document.createElement('div');row.className='lb-row';
var col=last>=.95?'var(--green)':last>=.5?'var(--amber)':'var(--red)';
row.innerHTML='<span style="color:var(--txt2)">'+esc(t.name.substring(0,22))+'</span><span style="color:'+col+';font-family:var(--display);font-weight:700">'+Math.round(last*100)+'%</span>';
if(lb.querySelector('.empty'))lb.innerHTML='';lb.insertBefore(row,lb.firstChild);
if(lb.children.length>6)lb.removeChild(lb.lastChild);
}
document.addEventListener('keydown',function(e){
if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){var btn=document.getElementById('runbtn');if(btn&&!btn.disabled)runStep();e.preventDefault();}
});
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return JSONResponse({"name": "SQLQueryEnv", "version": "2.0.0", "description": "Real-world SQL query environment for RL agents", "tasks": [t["task_id"] for t in TASKS_DATA["tasks"]], "status": "ready"})
    html = HTML_TEMPLATE.replace("TASKS_PLACEHOLDER", json.dumps(TASKS_DATA))
    return HTMLResponse(html)

@app.get("/api/info")
async def api_info():
    return {"name": "SQLQueryEnv", "version": "2.0.0", "description": "Real-world SQL query environment for RL agents", "tasks": [t["task_id"] for t in TASKS_DATA["tasks"]], "status": "ready"}

@app.get("/health")
async def health():
    return {"status": "ok", "env": "loaded" if HAS_ENV else "demo"}

@app.get("/tasks")
async def list_tasks():
    return TASKS_DATA

@app.post("/reset")
async def reset(req: ResetRequest = ResetRequest()):
    if not HAS_ENV:
        tid = req.task_id
        t = next((x for x in TASKS_DATA["tasks"] if x["task_id"] == tid), TASKS_DATA["tasks"][0])
        return {
            "observation": {
                "task_id": t["task_id"], "task_name": t["name"], "difficulty": t["difficulty"],
                "max_steps": t["max_steps"], "schema_ddl": t.get("schema_ddl", ""),
                "business_question": t.get("business_question", ""), "hint": t.get("hint", ""),
                "step": 0, "previous_error": None
            },
            "reward": 0.001,  # ← FIXED: was 0.0
            "done": False,
            "info": {}
        }
    result = await _env.reset(task_id=req.task_id)
    obs = result.observation
    return {"observation": obs.model_dump(), "reward": result.reward, "done": result.done, "info": result.info}

@app.post("/step")
async def step(req: StepRequest):
    if not HAS_ENV:
        return {
            "observation": {},
            "reward": 0.05,  # ← FIXED: was 0.0
            "done": False,
            "info": {"feedback": "Backend env not loaded - cannot score in demo mode."}
        }
    action = SQLAction(sql_query=req.sql_query)
    result = await _env.step(action)
    obs = result.observation
    return {"observation": obs.model_dump(), "reward": result.reward, "done": result.done, "info": result.info}

@app.get("/state")
async def state():
    if not HAS_ENV:
        return {"error": "env not loaded"}
    return await _env.state()

def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
