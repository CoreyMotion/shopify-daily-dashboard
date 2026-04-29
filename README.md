# Shopify Daily Dashboard

A local Python script that fetches daily KPIs from the Shopify Admin API and prints them in a clean dashboard format, matched to Shopify's analytics dashboard figures.

## Output

```
==================================================
  DAILY DASHBOARD  —  Mon 27 Apr 2026
==================================================

  REVENUE
  ------------------------------------------------
  Total Sales (inc GST)...........$76,870.62
  Revenue ex GST...................$69,882.00
  MTD Revenue ex GST...$XXX,XXX.XX  (April 2026)

  ORDERS
  ------------------------------------------------
  Orders....................................340
  MTD Orders.......................XXXX  (April 2026)
  AOV (ex GST)........................$213.57

  AD SPEND
  ------------------------------------------------
  Meta Ad Spend...........—  (not connected)
  Google Ad Spend.........—  (not connected)

  PROFITABILITY
  ------------------------------------------------
  Gross Profit (daily).—  (no COGS in Shopify)
  MTD Gross Profit...—  (no COGS in Shopify)
  Daily Profit........—  (requires ad spend)
  MTD Profit..........—  (requires ad spend)

  SESSIONS & CONVERSION
  ------------------------------------------------
  Sessions.......—  (requires Analytics API)
  CVR............—  (requires Analytics API)

==================================================
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in your `.env` file:

| Variable | Description |
|---|---|
| `SHOPIFY_STORE_NAME` | Your store subdomain (e.g. `my-store` from `my-store.myshopify.com`) |
| `SHOPIFY_ACCESS_TOKEN` | Admin API access token (`shpat_...`) |
| `SHOPIFY_API_VERSION` | API version (default: `2024-01`) |
| `EXCLUDE_ORDER_SOURCES` | Comma-separated source names excluded from order count and revenue |
| `EXCLUDE_REVENUE_SOURCES` | Comma-separated source names counted as orders but excluded from revenue |

### 3. Shopify API access

Create a Custom App in your Shopify Admin:

1. Go to **Settings → Apps → Develop apps**
2. Create a new app and enable Admin API access
3. Grant the following scopes: `read_orders`, `read_products`, `read_customers`
4. Copy the **Admin API access token** into your `.env`

### 4. Run

```bash
python shopify_report.py
```

You will be prompted to enter a date in `YYYY-MM-DD` format (AEST). The script fetches all orders for that day and month-to-date.

## Notes

- Dates are entered in **AEST (Australia/Sydney)** and automatically converted to UTC for the API. Daylight saving (AEDT) is handled automatically.
- Revenue figures are **net of refunds** and exclude cancelled, voided, and test orders.
- **Total Sales (inc GST)** matches the figure shown in Shopify's Analytics dashboard.
- Ad spend, sessions, CVR, and profitability metrics require additional integrations (Meta Ads API, Google Ads API, Shopify Analytics API).
