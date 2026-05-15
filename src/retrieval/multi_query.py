from __future__ import annotations

from src.schemas.outputs import RetrievalPlan
from src.schemas.prompts import QUERY_PLANNER_PROMPT, TASK_QUERY_HINTS


def fallback_plan(mode: str, user_input: str, query_count: int) -> RetrievalPlan:
    hints = TASK_QUERY_HINTS.get(mode, TASK_QUERY_HINTS["Ask with Citations"])
    queries = [user_input.strip()]
    for hint in hints:
        queries.append(f"{user_input.strip()} — {hint}")
    while len(queries) < query_count:
        queries.append(f"{user_input.strip()} — evidence, scope, limitations, and caveats")
    return RetrievalPlan(
        queries=list(dict.fromkeys(queries))[:query_count],
        rationale="Fallback task-specific query expansion was used.",
    )


def generate_retrieval_plan(
    reasoner,
    mode: str,
    user_input: str,
    query_count: int,
) -> RetrievalPlan:
    hints = "\n".join(f"- {item}" for item in TASK_QUERY_HINTS.get(mode, []))
    prompt = f"""
Selected task: {mode}
User request: {user_input}
Create exactly {query_count} complementary retrieval queries.
Task-specific evidence targets:
{hints}
""".strip()
    try:
        result = reasoner.parse(
            system_prompt=QUERY_PLANNER_PROMPT,
            user_prompt=prompt,
            output_schema=RetrievalPlan,
            max_output_tokens=900,
        )
        cleaned = [query.strip() for query in result.queries if query.strip()]
        if len(cleaned) >= 2:
            result.queries = list(dict.fromkeys(cleaned))[:query_count]
            return result
    except Exception:
        pass
    return fallback_plan(mode, user_input, query_count)
