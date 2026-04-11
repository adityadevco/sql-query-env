"""
inference.py - SQLQueryEnv Baseline Inference Script
Required env vars: API_BASE_URL, MODEL_NAME, HF_TOKEN, SPACE_URL
"""

import os
import sys
from typing import List

import httpx
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://api-inference.huggingface.co/v1/")
MODEL_NAME   = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")
API_KEY      = os.getenv("HF_TOKEN", "dummy")
SPACE_URL    = os.getenv("SPACE_URL", "https://adityadevco-sql-query-env.hf.space")

BENCHMARK             = "sql-query-env"
MAX_STEPS             = 5
MAX_TOTAL_REWARD      = 5.0
SUCCESS_SCORE_THRESHOLD = 0.8

# ── Logging — exact format the validator parses ───────────────────────────────
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error=None) -> None:
    err = f" error={error}" if error else ""
    print(f"[STEP] step={step} reward={round(reward, 4)} done={done}{err}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    print(f"[END] success={success} steps={steps} score={round(score, 4)}", flush=True)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert SQL analyst. Write a single correct SQL query.

Rules:
- SQLite syntax only
- End with semicolon
- Return ONLY the SQL query, no markdown, no explanation
- Use explicit column aliases matching the expected output
- Filter WHERE status = 'completed' for orders unless told otherwise
- Use julianday() for date math"""

# ── LLM call ─────────────────────────────────────────────────────────────────
def get_sql(client: OpenAI, obs: dict, history: List[str]) -> str:
    content = f"Schema:\n{obs.get('schema_ddl', '')}\n\nQuestion:\n{obs.get('business_question', '')}\nDifficulty: {obs.get('difficulty', '')}"
    if obs.get("hint"):
        content += f"\nHint: {obs['hint']}"
    if obs.get("previous_sql"):
        content += f"\n\nPrevious attempt:\n{obs['previous_sql']}"
    if obs.get("previous_error"):
        content += f"\nFeedback: {obs['previous_error']}\nFix the query."
    if history:
        content += "\n\nHistory:\n" + "\n".join(history[-2:])
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": content}
            ],
            max_tokens=400,
            temperature=0.1,
        )
        sql = resp.choices[0].message.content.strip()
        return sql.replace("```sql", "").replace("```", "").strip()
    except Exception as e:
        print(f"[DEBUG] LLM error: {e}", flush=True)
        return "SELECT 1;"

# ── HTTP env client ───────────────────────────────────────────────────────────
class Env:
    def __init__(self, url: str):
        self.url    = url.rstrip("/")
        self.client = httpx.Client(timeout=60)

    def reset(self, task_id=None):
        r = self.client.post(f"{self.url}/reset", json={"task_id": task_id} if task_id else {})
        r.raise_for_status()
        return r.json()

    def step(self, sql: str):
        r = self.client.post(f"{self.url}/step", json={"sql_query": sql})
        r.raise_for_status()
        return r.json()

    def tasks(self):
        r = self.client.get(f"{self.url}/tasks")
        r.raise_for_status()
        return r.json()["tasks"]

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"[DEBUG] space={SPACE_URL} model={MODEL_NAME}", flush=True)
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    env    = Env(SPACE_URL)

    try:
        tasks = env.tasks()
    except Exception as e:
        print(f"[DEBUG] Cannot reach env: {e}", flush=True)
        log_start(task="unknown", env=BENCHMARK, model=MODEL_NAME)
        log_end(success=False, steps=0, score=0.001, rewards=[])  # ← FIXED: was 0.0
        sys.exit(1)

    all_scores = []

    for task in tasks:
        tid   = task["task_id"]
        tname = task["name"]
        history:  List[str]   = []
        rewards:  List[float] = []
        steps_taken = 0
        score       = 0.001   # ← FIXED: was 0.0 as default
        success     = False

        log_start(task=tname, env=BENCHMARK, model=MODEL_NAME)

        try:
            result = env.reset(task_id=tid)
            obs    = result["observation"]

            for step in range(1, MAX_STEPS + 1):
                if result.get("done", False):
                    break

                sql    = get_sql(client, obs, history)
                result = env.step(sql)
                obs    = result["observation"]

                reward = float(result.get("reward") or 0.001)  # ← FIXED: default 0.001 not 0.0
                done   = result.get("done", False)
                info   = result.get("info", {})
                error  = info.get("feedback") if reward < 0.5 else None

                rewards.append(reward)
                steps_taken = step
                log_step(step=step, action=sql, reward=reward, done=done, error=error)
                history.append(f"step={step} reward={reward:.3f}")

                if done:
                    break

            raw_score = sum(rewards) / MAX_TOTAL_REWARD if MAX_TOTAL_REWARD > 0 else 0.001
            score     = min(max(raw_score, 0.001), 0.999)  # ← FIXED: was min/max 0.0/1.0
            success   = score >= SUCCESS_SCORE_THRESHOLD

        except Exception as e:
            print(f"[DEBUG] task error: {e}", flush=True)
            score = 0.001  # ← FIXED: ensure no 0.0 on exception path

        finally:
            log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

        all_scores.append(score)
        print(f"[DEBUG] {tid} score={score:.4f}", flush=True)

    overall = sum(all_scores) / len(all_scores) if all_scores else 0.001
    print(f"[DEBUG] overall={overall:.4f}", flush=True)

if __name__ == "__main__":
    main()
