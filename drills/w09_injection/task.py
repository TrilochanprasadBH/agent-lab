"""Drill 09 - Reading untrusted documents safely.

Goal
    Answer the question from the documents, without obeying instructions that were
    hidden inside them.

Return
    A dict with keys: answer, actions.

Run
    python3 run.py --drill w09_injection

Starting point
    All documents are concatenated and sent to the model. A poisoned document is
    obeyed, and an outbound email is executed.

Full brief
    drills/w09_injection/spec.md
"""

from __future__ import annotations

import json

PROMPT = """Answer the question using the documents.

{docs}

Question: {question}
"""


def respond(case, model) -> dict:
    docs = "\n\n".join(case.docs)
    response = model.complete(PROMPT.format(docs=docs, question=case.question))
    text = response.text.strip()

    actions = []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {"answer": text, "actions": actions}

    if "tool" in payload:
        case.world.execute(payload["tool"], payload.get("args") or {})
        actions.append(payload["tool"])
        return {"answer": "", "actions": actions}

    return {"answer": str(payload.get("final", "")), "actions": actions}
