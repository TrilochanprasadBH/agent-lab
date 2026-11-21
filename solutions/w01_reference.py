"""Reference solution for drill 1 — read this *after* you have tried your own.

Four ideas, in order of payoff:

  1. Repair the payload before you parse it. Truncated objects and trailing
     commas are the model's most common failure, and both are mechanical to fix.
  2. Normalize at the boundary. "1.350,00 EUR" and "1350.00" are the same
     number; decide that once, in one place.
  3. Validate against arithmetic. subtotal + tax must equal total. If it does
     not, you know the record is corrupt without needing the ground truth.
  4. Retry selectively, and only with a changed prompt. Blanket retries cost
     money and rarely help; a retry aimed at a detected defect usually does.

The last step is the one people skip: after three honest attempts, return the
best partial record rather than an empty one.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime

PROMPT = """Extract the invoice fields below as JSON with keys:
vendor, invoice_date (ISO 8601), currency (ISO 4217), subtotal, tax, total.

Document:
{doc}
"""

RETRY_PROMPT = """Extract the invoice fields below as JSON with keys:
vendor, invoice_date (ISO 8601), currency (ISO 4217), subtotal, tax, total.

Rules:
- vendor is the party issuing the invoice, never the one being billed.
- subtotal + tax must equal total exactly.
- return JSON only, with no commentary.

Document:
{doc}
"""

SCORED = ("vendor", "invoice_date", "currency", "total")

DATE_FORMATS = (
    "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
    "%d %B %Y", "%B %d, %Y", "%d %b %Y", "%b %d, %Y",
)

SYMBOLS = {"$": "USD", "\u20ac": "EUR", "\u00a3": "GBP", "\u20b9": "INR"}


# -- 1. parsing -------------------------------------------------------------


def _close_json(fragment: str) -> str:
    """Balance quotes and brackets in a truncated JSON fragment."""
    stack: list[str] = []
    in_string = False
    escaped = False

    for ch in fragment:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch in "}]" and stack:
            stack.pop()

    text = fragment
    if in_string:
        text += '"'
    text = text.rstrip()
    while text and text[-1] in ".,:":
        text = text[:-1].rstrip()
    return text + "".join(reversed(stack))


def _candidates(text: str) -> list[str]:
    out = [text.strip()]

    fenced = re.search(r"```(?:json)?\s*(.*?)(?:```|$)", text, re.DOTALL)
    if fenced:
        out.append(fenced.group(1).strip())

    start = text.find("{")
    if start != -1:
        out.append(text[start:].strip())
        end = text.rfind("}")
        if end > start:
            out.append(text[start : end + 1].strip())

    return out


def parse_json(text: str) -> dict | None:
    if not text:
        return None

    for candidate in _candidates(text):
        attempts = [candidate, re.sub(r",(\s*[}\]])", r"\1", candidate)]

        try:
            value = json.loads(attempts[1])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            pass

        for attempt in attempts:
            # Walk backwards through truncation points until something parses.
            positions = [m.start() for m in re.finditer(r"[,{]", attempt)][-12:]
            for cut in reversed(positions):
                try:
                    value = json.loads(_close_json(attempt[:cut]))
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    return value

    return None


# -- 2. normalization -------------------------------------------------------


def to_money(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    if not isinstance(value, str):
        return None

    cleaned = re.sub(r"[^0-9.,\-]", "", value)
    if not re.search(r"\d", cleaned):
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        if re.search(r",\d{2}$", cleaned) and cleaned.count(",") == 1:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def to_currency(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.search(r"\b([A-Za-z]{3})\b", value)
    if match:
        return match.group(1).upper()
    for symbol, code in SYMBOLS.items():
        if symbol in value:
            return code
    return None


def to_iso_date(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        pass
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def normalize(record: dict | None) -> dict:
    if not isinstance(record, dict):
        return {}
    return {
        "vendor": record.get("vendor").strip() if isinstance(record.get("vendor"), str) else None,
        "invoice_date": to_iso_date(record.get("invoice_date")),
        "currency": to_currency(record.get("currency") or record.get("total")),
        "subtotal": to_money(record.get("subtotal")),
        "tax": to_money(record.get("tax")),
        "total": to_money(record.get("total")),
    }


# -- 3. validation against the document and against arithmetic --------------


def _line_value(doc: str, label: str) -> str | None:
    match = re.search(rf"^\s*(?:{label})\s*:\s*(.+)$", doc, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else None


def _squash(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").casefold())


def arithmetic_ok(record: dict) -> bool:
    subtotal, tax, total = record.get("subtotal"), record.get("tax"), record.get("total")
    if subtotal is None or tax is None or total is None:
        return True  # nothing to check against; not evidence of a defect
    return abs((subtotal + tax) - total) <= 0.02


def vendor_grounded(record: dict, doc: str) -> bool:
    vendor = record.get("vendor")
    if not vendor:
        return False

    key = _squash(vendor)
    issuer = _squash(_line_value(doc, r"Supplier|Vendor"))
    bill_to = _squash(_line_value(doc, r"Bill To|Customer|Client"))

    if key not in _squash(doc):
        return False  # hallucinated
    if bill_to and key == bill_to and key != issuer:
        return False  # the model handed back the party being billed
    return True


def defect(record: dict, doc: str) -> str | None:
    if not record:
        return "no parseable payload"
    missing = [name for name in SCORED if record.get(name) is None]
    if missing:
        return f"missing {', '.join(missing)}"
    if not arithmetic_ok(record):
        return "subtotal + tax != total"
    if not vendor_grounded(record, doc):
        return "vendor not grounded in the document"
    return None


# -- 4. selective retry -----------------------------------------------------


def _richness(record: dict) -> int:
    score = sum(1 for name in SCORED if record.get(name) is not None)
    return score + (2 if arithmetic_ok(record) else 0)


def extract(invoice, model) -> dict:
    doc = invoice.raw
    best: dict = {}

    for attempt in range(3):
        prompt = (PROMPT if attempt == 0 else RETRY_PROMPT).format(doc=doc)
        response = model.complete(prompt)
        record = normalize(parse_json(response.text))

        if defect(record, doc) is None:
            return record

        if _richness(record) > _richness(best):
            best = record

    return best
