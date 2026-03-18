import json


# Единственный источник истины для ролей и причин
ROLES = ["Harvester", "Architect", "Consultant", "Interrogator", "Guardian"]

REASONS = {
    "Harvester":    "new_fact_detected",
    "Architect":    "spec_block_affected",
    "Consultant":   "question_about_project",
    "Guardian":     "offtopic_segment",
}

_EXAMPLE_INPUT = (
    "поставь mysql для основной БД, "
    "и ещё напиши мне код быстрой сортировки"
)
_EXAMPLE_OUTPUT = {
    "behaviors": [
        {
            "role": "Harvester",
            "reason": REASONS["Harvester"],
            "quote": "поставь mysql для основной БД",
        },
        {
            "role": "Architect",
            "reason": REASONS["Architect"],
            "quote": "поставь mysql для основной БД",
        },
        {
            "role": "Guardian",
            "reason": REASONS["Guardian"],
            "quote": "напиши мне код быстрой сортировки",
        },
    ]
}


def build_system_prompt() -> str:
    roles_block = "\n".join(
        f"  - {role}: {desc}"
        for role, desc in [
            ("Harvester",    "User provides new facts, requirements, or project context → extract and update GKG."),
            ("Architect",    "User requests to create, modify, or regenerate a spec block → rewrite affected sections."),
            ("Consultant",   "User asks a question about the current project or spec → answer from existing knowledge."),
            ("Guardian",     "Request is outside system scope (write code, off-topic tasks, harmful content) → reject that segment only."),
        ]
    )

    return f"""\
You are the Intent Router for a technical-specification assistant (Auto-TZ).
Your only job: decompose user input into one or more behavior activations.

## Roles
{roles_block}

## Output format
Return valid JSON only — no markdown, no explanation.
Schema:
{{
  "behaviors": [
    {{
      "role":   "<one of: {', '.join(ROLES)}>",
      "reason": "<one of: {', '.join(REASONS.values())}>",
      "quote":  "<exact substring copied from user input>"
    }}
  ]
}}

## Rules
1. A single message can activate several roles — split it into relevant quotes per role.
2. "quote" MUST be a verbatim substring of the user input — never paraphrase.
3. Technical terms, stack names, API names, config keys, logs, code snippets are NEVER off-topic.
4. Guardian activates only on the off-topic/harmful segment, not the whole message.
5. If no behavior applies, return an empty behaviors array: {{"behaviors": []}}.

## Example
Input:
{_EXAMPLE_INPUT}

Output:
{json.dumps(_EXAMPLE_OUTPUT, ensure_ascii=False, indent=2)}
"""


def build_user_prompt(user_input: str) -> str:
    return f"Route this input:\n{user_input}"
