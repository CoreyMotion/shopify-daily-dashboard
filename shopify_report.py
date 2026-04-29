#!/usr/bin/env python3
"""
Shopify Daily Dashboard
Prompts for a date in AEST and prints a focused KPI summary.
"""

import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import certifi
import requests
from dotenv import load_dotenv

load_dotenv()

_raw_store = os.getenv("SHOPIFY_STORE_NAME", "")
STORE_NAME = _raw_store.replace(".myshopify.com", "").strip()
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-01")

# Sources excluded from order count AND revenue (draft/system orders Shopify hides)
_excl_orders = os.getenv("EXCLUDE_ORDER_SOURCES", "shopify_draft_order,3426665")
EXCLUDE_ORDER_SOURCES = {s.strip() for s in _excl_orders.split(",") if s.strip()}

# Sources counted as orders but excluded from revenue
# (Shopify attributes revenue to the originating channel, not the app that created the order)
_excl_rev = os.getenv("EXCLUDE_REVENUE_SOURCES", "1520611,Edit Order")
EXCLUDE_REVENUE_SOURCES = {s.strip() for s in _excl_rev.split(",") if s.strip()}

AEST = ZoneInfo("Australia/Sydney")
W = 46


def check_config():
    missing = [k for k, v in {"SHOPIFY_STORE_NAME": STORE_NAME, "SHOPIFY_ACCESS_TOKEN": ACCESS_TOKEN}.items() if not v]
    if missing:
        print(f"ERROR: Missing env vars: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)


def shopify_get(endpoint, params=None):
    base = f"https://{STORE_NAME}.myshopify.com/admin/api/{API_VERSION}"
    hdrs = {"X-Shopify-Access-Token": ACCESS_TOKEN}
    url = f"{base}/{endpoint}.json"
    results = []
    while url:
        resp = requests.get(url, headers=hdrs, params=params, verify=certifi.where())
        resp.raise_for_status()
        data = resp.json()
        results.extend(data[next(iter(data))])
        link = resp.headers.get("Link", "")
        url = None
        params = None
        for part in link.split(","):
            if 'rel="next"' in part.strip():
                url = part.strip().split(";")[0].strip().strip("<>")
    return results


def prompt_date():
    while True:
        raw = input("Enter date (YYYY-MM-DD) AEST: ").strip()
        try:
            return datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            print("Use YYYY-MM-DD format.")


def day_utc_range(local_dt):
    start = datetime(local_dt.year, local_dt.month, local_dt.day, 0, 0, 0, tzinfo=AEST)
    end = datetime(local_dt.year, local_dt.month, local_dt.day, 23, 59, 59, tzinfo=AEST)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return start.astimezone(timezone.utc).strftime(fmt), end.astimezone(timezone.utc).strftime(fmt)


def mtd_utc_range(local_dt):
    start = datetime(local_dt.year, local_dt.month, 1, 0, 0, 0, tzinfo=AEST)
    end = datetime(local_dt.year, local_dt.month, local_dt.day, 23, 59, 59, tzinfo=AEST)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return start.astimezone(timezone.utc).strftime(fmt), end.astimezone(timezone.utc).strftime(fmt)


def is_countable(order):
    """Matches Shopify dashboard: excludes cancelled, voided, test, and configured sources."""
    return (
        not order.get("cancelled_at")
        and not order.get("test")
        and order.get("financial_status") != "voided"
        and order.get("source_name", "") not in EXCLUDE_ORDER_SOURCES
    )


def refund_amounts(order):
    """Returns (refund_inc_gst, refund_ex_gst) for an order."""
    inc = sum(
        float(txn.get("amount", 0))
        for refund in order.get("refunds", [])
        for txn in refund.get("transactions", [])
        if txn.get("kind") in ("refund", "suggested_refund")
    )
    ex = sum(
        float(rli.get("subtotal", 0))
        for refund in order.get("refunds", [])
        for rli in refund.get("refund_line_items", [])
    )
    return inc, ex


def calc_revenue(orders):
    """Returns (inc_gst, ex_gst) matching Shopify's Total Sales definition."""
    inc_gst = 0.0
    ex_gst = 0.0
    for o in orders:
        if not is_countable(o):
            continue
        status = o.get("financial_status")
        if status == "refunded":
            continue
        if o.get("source_name", "") in EXCLUDE_REVENUE_SOURCES:
            continue
        price = float(o.get("total_price", 0))
        tax = float(o.get("total_tax", 0))
        if status == "partially_refunded":
            ref_inc, ref_ex = refund_amounts(o)
            inc_gst += price - ref_inc
            ex_gst += (price - tax) - ref_ex
        else:
            inc_gst += price
            ex_gst += price - tax
    return inc_gst, ex_gst


def order_count(orders):
    return sum(1 for o in orders if is_countable(o))


def calc_aov(rev, count):
    return rev / count if count else 0


def row(label, value, note=""):
    label_col = f"  {label}"
    note_str = f"  {note}" if note else ""
    dots = "." * max(1, W - len(label_col) - len(str(value)) - len(note_str))
    print(f"{label_col}{dots}{value}{note_str}")


def divider(char="="):
    print(char * (W + 4))


def section(title):
    print(f"\n  {title}")
    print("  " + "-" * W)


def fmt(amount):
    return f"${amount:,.2f}"


# ---------------------------------------------------------------------------

def main():
    check_config()

    local_dt = prompt_date()
    date_label = local_dt.strftime("%a %d %b %Y")
    month_label = local_dt.strftime("%B %Y")

    day_start, day_end = day_utc_range(local_dt)
    mtd_start, mtd_end = mtd_utc_range(local_dt)

    print(f"\n  Fetching data...", end="", flush=True)

    day_orders = shopify_get("orders", params={
        "status": "any", "financial_status": "any",
        "created_at_min": day_start, "created_at_max": day_end, "limit": 250,
    })
    mtd_orders = shopify_get("orders", params={
        "status": "any", "financial_status": "any",
        "created_at_min": mtd_start, "created_at_max": mtd_end, "limit": 250,
    })

    print(" done.\n")

    day_inc, day_rev = calc_revenue(day_orders)
    mtd_inc, mtd_rev = calc_revenue(mtd_orders)
    day_count = order_count(day_orders)
    mtd_count = order_count(mtd_orders)
    day_aov   = calc_aov(day_rev, day_count)

    divider()
    print(f"  DAILY DASHBOARD  —  {date_label}")
    divider()

    section("REVENUE")
    row("Total Sales (inc GST)", fmt(day_inc))
    row("Revenue ex GST", fmt(day_rev))
    row("MTD Revenue ex GST", fmt(mtd_rev), f"({month_label})")

    section("ORDERS")
    row("Orders", day_count)
    row("MTD Orders", mtd_count, f"({month_label})")
    row("AOV (ex GST)", fmt(day_aov))

    section("AD SPEND")
    row("Meta Ad Spend", "—", "(not connected)")
    row("Google Ad Spend", "—", "(not connected)")

    section("PROFITABILITY")
    row("Gross Profit (daily)", "—", "(no COGS in Shopify)")
    row("MTD Gross Profit", "—", "(no COGS in Shopify)")
    row("Daily Profit", "—", "(requires ad spend)")
    row("MTD Profit", "—", "(requires ad spend)")

    section("SESSIONS & CONVERSION")
    row("Sessions", "—", "(requires Analytics API)")
    row("CVR", "—", "(requires Analytics API)")

    print()
    divider()


if __name__ == "__main__":
    main()
