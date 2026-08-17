"""
AI Evaluator — structured observation layer.

Contract:
- Receives: learner input + item context + evaluator instructions
- Returns: EvaluatorOutput (observation + signals + skill_demonstration + metacognitive_flags)
- Does NOT set acquisition_probability — that is the engine's job.

The evaluator is a sensor. The engine is the interpreter.
"""

import json
from typing import Any

from openai import AsyncOpenAI

from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = """
You are a strict but fair linguistic evaluator for a German language learning engine.
Your role is to observe what a learner produced and return an honest structured assessment.

You return structured JSON. Never add fields outside the schema.
Never set acquisition_probability — that is not your job.

STRICTNESS RULES — apply these before anything else:
1. If the learner's response is nonsense, random characters, or completely unrelated to the task
   → performance_score: 0.0, retrieval_success: false, functional: false
2. If the response is not in German (when German is required)
   → performance_score: 0.1 at most, language_switches: true
3. If the response is partially correct but missing the key target element
   → performance_score: 0.3–0.5, retrieval_success: false
4. Only give performance_score >= 0.75 if the target word/structure is clearly and correctly used
5. For gap-fill tasks: the answer must contain the exact target word (allow minor case errors)
   → Wrong word or nonsense = performance_score: 0.0

Key principle:
A learner who writes "blabla" or random text has demonstrated nothing.
Set performance_score: 0.0 for any input that is not a genuine attempt in German.
Evaluate whether the communicative function was actually achieved.
Be encouraging in the feedback text, but be honest in the scores.
""".strip()


OUTPUT_SCHEMA = {
    "observation": {
        "produced_text": "string — exact learner output",
        "register": "formal | informal | mixed",
        "completeness": "float 0.0-1.0",
        "language_switches": "bool — did learner switch to L1 or English?",
    },
    "signals": {
        "performance_score": "float 0.0-1.0 — overall quality of production",
        "retrieval_success": "bool — did learner attempt to retrieve the target pattern?",
        "lexical_errors": ["list of string descriptions"],
        "morphological_errors": ["list of string descriptions"],
        "syntactic_errors": ["list of string descriptions"],
        "pragmatic_errors": ["list of string descriptions"],
        "register_consistent": "bool",
        "target_skill_demonstrated": "bool — was the target skill used at all?",
        "transfer_appropriate": "bool | null — null if transfer_distance < 2",
    },
    "skill_demonstration": {
        "functional": "bool — was the communicative function achieved?",
        "context_appropriate": "bool — was the output appropriate for this specific context?",
        "independent": "bool — did learner produce without needing prompts or scaffolding?",
        "generalized": "bool — was the skill applied in a context different from training? null if not applicable",
    },
    "metacognitive_flags": {
        "possible_gap": "bool — high performance but signs of low confidence",
        "possible_error": "bool — low performance but signs of overconfidence",
        "note": "string | null",
    },
    "raw_feedback_for_learner": "string — concise, encouraging feedback in the learner's context language (German for German content). Point to one key thing to improve.",
}


def _build_user_prompt(
    learner_input: str,
    item_prompt: str,
    context_label: str,
    transfer_distance: int,
    context_variable: str | None,
    evaluator_notes: str | None,
    expected_skill_demonstration: dict[str, Any],
) -> str:
    lines = [
        f"## Learning Item Context",
        f"Context type: {context_label} (transfer_distance={transfer_distance})",
    ]
    if context_variable:
        lines.append(f"Context variable: {context_variable}")
    lines += [
        f"\n## Item Prompt (what the learner saw)",
        item_prompt,
        f"\n## Learner's Response",
        learner_input or "(no response — learner did not produce output)",
    ]
    if evaluator_notes:
        lines += [f"\n## Evaluator Instructions", evaluator_notes]
    lines += [
        f"\n## Expected Skill Demonstration (for this item)",
        json.dumps(expected_skill_demonstration, indent=2),
        f"\n## Output Schema",
        json.dumps(OUTPUT_SCHEMA, indent=2),
        "\nReturn only valid JSON matching the schema above. No prose.",
    ]
    return "\n".join(lines)


async def evaluate(
    learner_input: str,
    item_prompt: str,
    context_label: str,
    transfer_distance: int,
    context_variable: str | None = None,
    evaluator_notes: str | None = None,
    expected_skill_demonstration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Call the AI evaluator and return the structured observation dict.
    Raises ValueError if the response cannot be parsed as valid JSON.
    """
    user_prompt = _build_user_prompt(
        learner_input=learner_input,
        item_prompt=item_prompt,
        context_label=context_label,
        transfer_distance=transfer_distance,
        context_variable=context_variable,
        evaluator_notes=evaluator_notes,
        expected_skill_demonstration=expected_skill_demonstration or {},
    )

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,  # low temperature — we want consistent structured output
    )

    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Evaluator returned invalid JSON: {e}\nRaw: {raw}")
