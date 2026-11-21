"""Seeded invoice corpus with ground truth.

Deterministic: the same 48 invoices come out on every run, so a score change
always means *your* change caused it.

Three label dialects and a few layout variations. Enough that hand-rolling
regexes over the whole corpus is tedious, not enough to make it impossible —
which is realistic. Regular formats *should* be parsed deterministically.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

SYMBOL = {"USD": "$", "EUR": "\u20ac", "GBP": "\u00a3", "INR": "\u20b9"}

VENDORS = [
    "Northwind Traders",
    "Acme Corp.",
    "Helios Systems GmbH",
    "Blue Harbor Logistics",
    "Kestrel & Sons",
    "Vantage Analytics Ltd",
    "Meridian Cloud Services",
    "Orchard Street Bakery",
]

VENDOR_ADDRESSES = [
    "88 Harbour Road, Bristol",
    "Unit 4, Fenchurch Estate, London",
    "Hauptstrasse 12, 10115 Berlin",
    "2200 Mission Street, San Francisco",
]

CUSTOMERS = [
    "Globex Corporation",
    "Initech LLC",
    "Umbrella Health",
    "Soylent Foods",
    "Hooli Inc.",
    "Stark Industrial",
    "Wonka Labs",
]

ITEMS = [
    "Consulting hours (8h)",
    "Cloud hosting, standard tier",
    "Priority support",
    "Onboarding fee",
    "Data migration",
    "Custom integration",
    "License renewal",
    "Training session",
]

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

LABEL_SETS = [
    {
        "date": "Date",
        "vendor": "Vendor",
        "bill_to": "Bill To",
        "subtotal": "Subtotal",
        "tax": "Tax",
        "total": "Total Due",
    },
    {
        "date": "Invoice Date",
        "vendor": "Supplier",
        "bill_to": "Customer",
        "subtotal": "Net",
        "tax": "VAT",
        "total": "Amount Due",
    },
    {
        "date": "Issued",
        "vendor": "Vendor",
        "bill_to": "Bill To",
        "subtotal": "Sub-total",
        "tax": "Tax",
        "total": "Total",
    },
]

LABEL_CYCLE = [0, 0, 1, 0, 2, 0, 1, 2]


@dataclass(frozen=True)
class Invoice:
    doc_id: str
    raw: str
    truth: dict


def _fmt(value: float, style: str, currency: str) -> str:
    if style == "eu":
        body = f"{value:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")
        return f"{body} {currency}"
    if style == "sym":
        return f"{SYMBOL[currency]}{value:,.2f}"
    return f"{value:,.2f} {currency}"


def _fmt_date(day: int, month: int, year: int, style: str) -> str:
    if style == "iso":
        return f"{year:04d}-{month:02d}-{day:02d}"
    if style == "long":
        return f"{day} {MONTHS[month - 1]} {year}"
    if style == "us":
        return f"{MONTHS[month - 1]} {day}, {year}"
    if style == "slash":
        return f"{day:02d}/{month:02d}/{year}"
    return f"{day:02d}-{month:02d}-{year}"


def generate(n: int = 48, seed: int = 2027) -> list[Invoice]:
    rng = random.Random(seed)
    invoices: list[Invoice] = []

    currency_cycle = ["USD", "USD", "EUR", "USD", "GBP", "USD", "INR", "EUR"]
    style_cycle = ["sym", "iso", "eu", "sym", "iso", "iso", "sym", "eu"]
    date_cycle = ["iso", "long", "us", "slash", "long", "iso", "us", "dash"]

    for i in range(n):
        currency = currency_cycle[i % len(currency_cycle)]
        style = style_cycle[i % len(style_cycle)]
        if style == "eu":
            currency = "EUR"

        labels = LABEL_SETS[LABEL_CYCLE[i % len(LABEL_CYCLE)]]
        date_style = date_cycle[i % len(date_cycle)]
        day = rng.randint(1, 28)
        month = rng.randint(1, 12)
        year = 2026

        vendor = rng.choice(VENDORS)
        customer = rng.choice(CUSTOMERS)

        rate = rng.choice([0, 5, 8, 10, 18, 20])
        subtotal = round(rng.uniform(120, 9400), 2)
        tax = round(subtotal * rate / 100, 2)
        total = round(subtotal + tax, 2)

        n_items = rng.randint(1, 3)
        chosen = rng.sample(ITEMS, n_items)
        item_lines = "\n".join(f"  - {name}" for name in chosen)

        number = 1000 + i

        lines = [f"INVOICE #{number}", f"{labels['date']}: {_fmt_date(day, month, year, date_style)}"]
        lines.append(f"{labels['vendor']}: {vendor}")
        if i % 4 == 1:
            lines.append(f"  {rng.choice(VENDOR_ADDRESSES)}")
        if i % 5 == 2:
            lines.append(f"PO Number: PO-{rng.randint(10000, 99999)}")
        lines.append(f"{labels['bill_to']}: {customer}")
        lines.append("-" * 44)
        lines.append(item_lines)
        lines.append("-" * 44)
        lines.append(f"{labels['subtotal']}: {_fmt(subtotal, style, currency)}")
        lines.append(f"{labels['tax']} ({rate}%): {_fmt(tax, style, currency)}")
        lines.append(f"{labels['total']}: {_fmt(total, style, currency)}")

        truth = {
            "vendor": vendor,
            "invoice_date": f"{year:04d}-{month:02d}-{day:02d}",
            "currency": currency,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
        }

        invoices.append(Invoice(doc_id=f"inv-{number}", raw="\n".join(lines) + "\n", truth=truth))

    return invoices
