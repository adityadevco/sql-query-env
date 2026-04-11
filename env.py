"""
SQLQueryEnv — OpenEnv Environment
Real-world SQL query optimization and correctness environment.
An AI agent receives a database schema + business question and must
write correct, efficient SQL. Tasks range from simple SELECTs to
complex window functions with business logic.
"""
import sqlite3
import re
import time
import uuid
import json
from typing import Optional, Any
from pydantic import BaseModel, Field
from openenv import Environment, StepResult

# ─────────────────────────────────────────────
# Typed Models
# ─────────────────────────────────────────────
class SQLObservation(BaseModel):
    task_id: str
    task_name: str
    difficulty: str  # easy | medium | hard
    schema_ddl: str
    sample_data: str
    business_question: str
    hint: Optional[str] = None
    previous_error: Optional[str] = None
    previous_sql: Optional[str] = None
    step_number: int = 0
    max_steps: int = 5

class SQLAction(BaseModel):
    sql_query: str = Field(..., description="The SQL query to execute against the database")

class SQLReward(BaseModel):
    score: float = Field(..., ge=0.001, le=0.999)  # strictly between 0 and 1
    correctness: float
    efficiency: float
    style: float
    feedback: str

# ─────────────────────────────────────────────
# Task Definitions
# ─────────────────────────────────────────────
TASKS = {
    "easy_sales_summary": {
        "name": "Sales Summary Report",
        "difficulty": "easy",
        "schema_ddl": """
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    unit_price REAL,
    order_date TEXT,
    status TEXT
);
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT,
    category TEXT,
    cost_price REAL
);
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    customer_name TEXT,
    region TEXT,
    tier TEXT
);
""",
        "seed_data": """
INSERT INTO products VALUES (1,'Laptop','Electronics',500),(2,'Mouse','Electronics',10),(3,'Desk','Furniture',150),(4,'Chair','Furniture',80),(5,'Keyboard','Electronics',20);
INSERT INTO customers VALUES (1,'Alice Corp','North','Gold'),(2,'Bob Ltd','South','Silver'),(3,'Charlie Inc','North','Gold'),(4,'Delta Co','West','Bronze'),(5,'Echo LLC','East','Silver');
INSERT INTO orders VALUES
(1,1,1,2,1200,'2024-01-15','completed'),
(2,2,2,5,25,'2024-01-16','completed'),
(3,3,1,1,1200,'2024-01-17','completed'),
(4,1,3,3,350,'2024-02-01','completed'),
(5,4,4,2,200,'2024-02-10','completed'),
(6,5,5,10,45,'2024-02-15','completed'),
(7,2,1,1,1200,'2024-03-01','completed'),
(8,3,2,3,25,'2024-03-05','completed'),
(9,1,5,5,45,'2024-03-10','completed'),
(10,4,3,1,350,'2024-03-15','cancelled');
""",
        "business_question": "What is the total revenue per product category for completed orders only? Show category and total_revenue, sorted by total_revenue descending.",
        "expected_columns": ["category", "total_revenue"],
        "expected_rows": [
            {"category": "Electronics", "total_revenue": 7075.0},
            {"category": "Furniture", "total_revenue": 1650.0},
        ],
        "hint": "Revenue = quantity * unit_price. Filter by status = 'completed'.",
        "max_steps": 5,
    },
    "medium_customer_cohort": {
        "name": "Customer Cohort Analysis",
        "difficulty": "medium",
        "schema_ddl": """
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    unit_price REAL,
    order_date TEXT,
    status TEXT
);
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    customer_name TEXT,
    region TEXT,
    tier TEXT
);
""",
        "seed_data": """
INSERT INTO customers VALUES (1,'Alice Corp','North','Gold'),(2,'Bob Ltd','South','Silver'),(3,'Charlie Inc','North','Gold'),(4,'Delta Co','West','Bronze'),(5,'Echo LLC','East','Silver'),(6,'Foxtrot AG','North','Gold'),(7,'Golf Inc','South','Bronze');
INSERT INTO orders VALUES
(1,1,1,2,1200,'2024-01-15','completed'),
(2,2,2,5,25,'2024-01-20','completed'),
(3,3,1,1,1200,'2024-02-10','completed'),
(4,1,3,3,350,'2024-02-14','completed'),
(5,4,4,2,200,'2024-02-20','completed'),
(6,5,5,10,45,'2024-03-05','completed'),
(7,2,1,1,1200,'2024-03-08','completed'),
(8,6,2,3,25,'2024-01-25','completed'),
(9,1,5,5,45,'2024-03-10','completed'),
(10,7,3,1,350,'2024-03-12','completed'),
(11,6,1,2,1200,'2024-03-15','completed'),
(12,3,2,3,25,'2024-03-20','completed');
""",
        "business_question": """Find customers who placed orders in at least 2 different months. 
Return: customer_name, region, tier, order_count, distinct_months, total_spent.
Sort by total_spent descending.""",
        "expected_columns": ["customer_name", "region", "tier", "order_count", "distinct_months", "total_spent"],
        "expected_rows": [
            {"customer_name": "Alice Corp", "region": "North", "tier": "Gold", "order_count": 3, "distinct_months": 3, "total_spent": 3875.0},
            {"customer_name": "Bob Ltd", "region": "South", "tier": "Silver", "order_count": 2, "distinct_months": 2, "total_spent": 1225.0},
            {"customer_name": "Foxtrot AG", "region": "North", "tier": "Gold", "order_count": 2, "distinct_months": 2, "total_spent": 2475.0},
            {"customer_name": "Charlie Inc", "region": "North", "tier": "Gold", "order_count": 2, "distinct_months": 2, "total_spent": 1275.0},
        ],
        "hint": "Use GROUP BY with HAVING. Extract month from order_date using strftime('%m', order_date).",
        "max_steps": 7,
    },
    "hard_running_metrics": {
        "name": "Running Revenue & Churn Risk Analysis",
        "difficulty": "hard",
        "schema_ddl": """
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    unit_price REAL,
    order_date TEXT,
    status TEXT
);
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    customer_name TEXT,
    region TEXT,
    tier TEXT
);
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT,
    category TEXT,
    cost_price REAL
);
""",
        "seed_data": """
INSERT INTO customers VALUES (1,'Alice Corp','North','Gold'),(2,'Bob Ltd','South','Silver'),(3,'Charlie Inc','North','Gold'),(4,'Delta Co','West','Bronze'),(5,'Echo LLC','East','Silver');
INSERT INTO products VALUES (1,'Laptop','Electronics',500),(2,'Mouse','Electronics',10),(3,'Desk','Furniture',150),(4,'Chair','Furniture',80),(5,'Keyboard','Electronics',20);
INSERT INTO orders VALUES
(1,1,1,2,1200,'2024-01-15','completed'),
(2,2,2,5,25,'2024-01-20','completed'),
(3,1,3,3,350,'2024-02-14','completed'),
(4,3,1,1,1200,'2024-02-10','completed'),
(5,4,4,2,200,'2024-02-20','completed'),
(6,5,5,10,45,'2024-03-05','completed'),
(7,2,1,1,1200,'2024-03-08','completed'),
(8,1,5,5,45,'2024-03-10','completed'),
(9,3,2,3,25,'2024-03-20','completed'),
(10,1,1,1,1200,'2024-04-01','completed'),
(11,5,3,2,350,'2024-04-15','completed'),
(12,4,5,5,45,'2024-04-20','cancelled');
""",
        "business_question": """For each customer, compute:
- customer_name, tier
- total_orders (completed only)
- total_spent (completed only) 
- avg_order_value (completed only)
- months_since_last_order (months between their last completed order and '2024-05-01')
- churn_risk: 'High' if months_since_last_order >= 2 AND total_orders <= 2, 'Medium' if months_since_last_order >= 2 AND total_orders > 2, else 'Low'
Only include customers with at least 1 completed order.
Sort by churn_risk (High first, then Medium, then Low), then total_spent desc.""",
        "expected_columns": ["customer_name", "tier", "total_orders", "total_spent", "avg_order_value", "months_since_last_order", "churn_risk"],
        "expected_rows": [
            {"customer_name": "Bob Ltd", "tier": "Silver", "total_orders": 2, "total_spent": 1225.0, "avg_order_value": 612.5, "months_since_last_order": 2, "churn_risk": "High"},
            {"customer_name": "Charlie Inc", "tier": "Gold", "total_orders": 2, "total_spent": 1275.0, "avg_order_value": 637.5, "months_since_last_order": 2, "churn_risk": "High"},
            {"customer_name": "Delta Co", "tier": "Bronze", "total_orders": 1, "total_spent": 400.0, "avg_order_value": 400.0, "months_since_last_order": 2, "churn_risk": "High"},
            {"customer_name": "Echo LLC", "tier": "Silver", "total_orders": 2, "total_spent": 745.0, "avg_order_value": 372.5, "months_since_last_order": 1, "churn_risk": "Low"},
            {"customer_name": "Alice Corp", "tier": "Gold", "total_orders": 4, "total_spent": 4045.0, "avg_order_value": 1011.25, "months_since_last_order": 1, "churn_risk": "Low"},
        ],
        "hint": "Use CASE WHEN for churn_risk. Use (julianday('2024-05-01') - julianday(MAX(order_date)))/30 for months_since_last_order, cast to INTEGER.",
        "max_steps": 10,
    },
}

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def _clamp(value: float) -> float:
    """Clamp a score to strictly (0, 1) as required by OpenEnv."""
    return min(max(value, 0.001), 0.999)

# ─────────────────────────────────────────────
# Grader Logic
# ─────────────────────────────────────────────
def normalize_rows(rows: list[dict]) -> list[dict]:
    """Normalize float precision for comparison."""
    normalized = []
    for row in rows:
        norm_row = {}
        for k, v in row.items():
            if isinstance(v, float):
                norm_row[k] = round(v, 2)
            else:
                norm_row[k] = v
        normalized.append(norm_row)
    return normalized

def grade_sql(sql: str, task: dict, conn: sqlite3.Connection) -> SQLReward:
    """Execute SQL and grade the result."""
    expected_rows = task["expected_rows"]
    expected_cols = task["expected_columns"]

    # --- Style score ---
    style_score = 1.0
    sql_upper = sql.upper()
    if "SELECT *" in sql_upper:
        style_score -= 0.2
    if not sql.strip().endswith(";"):
        style_score -= 0.05
    style_score = _clamp(style_score)

    try:
        cursor = conn.execute(sql)
        cols = [d[0].lower() for d in cursor.description]
        raw_rows = cursor.fetchall()
        result_rows = [dict(zip(cols, row)) for row in raw_rows]
        result_rows = normalize_rows(result_rows)
        expected_norm = normalize_rows(expected_rows)

        # --- Column correctness ---
        expected_col_set = set(expected_cols)
        got_col_set = set(cols)
        col_match = len(expected_col_set & got_col_set) / len(expected_col_set)

        # --- Row correctness ---
        if len(result_rows) == 0:
            row_score = 0.001
            feedback = "Query returned no rows."
        elif len(result_rows) != len(expected_norm):
            matched = sum(1 for r in result_rows if r in expected_norm)
            row_score = _clamp(matched / len(expected_norm) * 0.5)
            feedback = f"Expected {len(expected_norm)} rows, got {len(result_rows)}. {matched} rows matched."
        else:
            exact_matches = sum(1 for a, b in zip(result_rows, expected_norm) if a == b)
            row_score = exact_matches / len(expected_norm)
            if row_score >= 1.0:
                row_score = 0.999
                feedback = "Perfect! All rows match exactly."
            else:
                # Try order-insensitive
                set_matches = sum(1 for r in result_rows if r in expected_norm)
                if set_matches == len(expected_norm):
                    row_score = 0.85  # correct but wrong order
                    feedback = "Correct rows but wrong sort order."
                else:
                    row_score = _clamp(row_score)
                    feedback = f"{exact_matches}/{len(expected_norm)} rows correct."

        correctness = _clamp(col_match * 0.3 + row_score * 0.7)

        # --- Efficiency score (heuristic) ---
        efficiency = 1.0
        if task["difficulty"] in ("medium", "hard"):
            if "GROUP BY" not in sql_upper and "group by" not in sql.lower():
                efficiency -= 0.3
        if task["difficulty"] == "hard":
            if "CASE" not in sql_upper:
                efficiency -= 0.2
        efficiency = _clamp(efficiency)

        # --- Final score ---
        raw_score = correctness * 0.7 + efficiency * 0.2 + style_score * 0.1
        score = _clamp(round(raw_score, 3))

        return SQLReward(
            score=score,
            correctness=correctness,
            efficiency=efficiency,
            style=style_score,
            feedback=feedback,
        )

    except Exception as e:
        return SQLReward(
            score=0.05,
            correctness=0.001,
            efficiency=0.001,
            style=style_score,
            feedback=f"SQL Error: {str(e)}",
        )

# ─────────────────────────────────────────────
# Environment
# ─────────────────────────────────────────────
class SQLQueryEnv(Environment):
    """
    SQLQueryEnv: A real-world SQL environment where agents must write
    correct, efficient SQL queries to answer business questions.
    """

    def __init__(self):
        self._task_ids = list(TASKS.keys())
        self._current_task_id: Optional[str] = None
        self._current_task: Optional[dict] = None
        self._conn: Optional[sqlite3.Connection] = None
        self._step_count: int = 0
        self._done: bool = False
        self._last_observation: Optional[SQLObservation] = None
        self._last_error: Optional[str] = None
        self._last_sql: Optional[str] = None

    def _setup_db(self, task: dict) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON")
        for stmt in task["schema_ddl"].strip().split(";"):
            s = stmt.strip()
            if s:
                conn.execute(s)
        for stmt in task["seed_data"].strip().split(";"):
            s = stmt.strip()
            if s:
                conn.execute(s)
        conn.commit()
        return conn

    def _make_sample_data_preview(self, task: dict) -> str:
        """Return a preview of seed data for context."""
        lines = []
        for stmt in task["seed_data"].strip().split(";"):
            s = stmt.strip()
            if s and s.upper().startswith("INSERT INTO"):
                match = re.match(r"INSERT INTO (\w+) VALUES", s, re.IGNORECASE)
                if match:
                    table = match.group(1)
                    lines.append(f"-- Sample rows in {table}: (see schema above for columns)")
        return "\n".join(lines) if lines else "-- See schema DDL above"

    async def reset(self, task_id: Optional[str] = None) -> StepResult:
        """Reset environment to a specific or default task."""
        self._current_task_id = task_id or self._task_ids[0]
        self._current_task = TASKS[self._current_task_id]
        self._conn = self._setup_db(self._current_task)
        self._step_count = 0
        self._done = False
        self._last_error = None
        self._last_sql = None

        obs = SQLObservation(
            task_id=self._current_task_id,
            task_name=self._current_task["name"],
            difficulty=self._current_task["difficulty"],
            schema_ddl=self._current_task["schema_ddl"],
            sample_data=self._make_sample_data_preview(self._current_task),
            business_question=self._current_task["business_question"],
            hint=self._current_task.get("hint"),
            step_number=0,
            max_steps=self._current_task["max_steps"],
        )
        self._last_observation = obs

        return StepResult(
            observation=obs,
            reward=0.001,  # reset reward is not a task score; use min valid value
            done=False,
            info={"task_id": self._current_task_id, "difficulty": self._current_task["difficulty"]},
        )

    async def step(self, action: SQLAction) -> StepResult:
        """Execute the agent's SQL query and return graded result."""
        if self._done:
            return StepResult(
                observation=self._last_observation,
                reward=0.001,  # episode over; return min valid value instead of 0.0
                done=True,
                info={"error": "Episode already done"},
            )

        self._step_count += 1
        sql = action.sql_query.strip()
        self._last_sql = sql

        reward_obj = grade_sql(sql, self._current_task, self._conn)
        score = reward_obj.score  # already clamped to (0.001, 0.999) by grade_sql

        # Determine if done
        max_steps = self._current_task["max_steps"]
        done = score >= 0.95 or self._step_count >= max_steps
        self._done = done

        error_msg = None
        if reward_obj.correctness < 0.5:
            error_msg = reward_obj.feedback

        obs = SQLObservation(
            task_id=self._current_task_id,
            task_name=self._current_task["name"],
            difficulty=self._current_task["difficulty"],
            schema_ddl=self._current_task["schema_ddl"],
            sample_data=self._make_sample_data_preview(self._current_task),
            business_question=self._current_task["business_question"],
            hint=self._current_task.get("hint"),
            previous_error=error_msg,
            previous_sql=sql,
            step_number=self._step_count,
            max_steps=max_steps,
        )
        self._last_observation = obs

        return StepResult(
            observation=obs,
            reward=score,
            done=done,
            info={
                "correctness": reward_obj.correctness,
                "efficiency": reward_obj.efficiency,
                "style": reward_obj.style,
                "feedback": reward_obj.feedback,
                "step": self._step_count,
            },
        )

    async def state(self) -> dict:
        """Return current environment state."""
        return {
            "task_id": self._current_task_id,
            "step": self._step_count,
            "done": self._done,
            "last_sql": self._last_sql,
        }

    def list_tasks(self) -> list[str]:
        return self._task_ids
