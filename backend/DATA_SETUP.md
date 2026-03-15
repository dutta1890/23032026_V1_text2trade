# Market Data Setup Guide

## Overview
Text2trade uses **NSE India** as the data source for historical stock data.
**No signup. No API key. No demat account.** All data is scraped directly from NSE India's public endpoints.

## Quick Start

```bash
cd /app/backend

# Step 1: Run setup (interactive CLI, installs dependencies)
python scripts/setup_data_source.py

# Step 2: Ingest data (downloads historical OHLCV from NSE India)
python scripts/ingest_data.py

# Step 3 (optional): Create admin account to manage data from the app
python scripts/create_admin.py --email admin@yourdomain.com --password YourSecurePass1!
```

## Data Sources

### 1. nsepython (PRIMARY — Daily OHLCV)
- **Package**: `pip install nsepython`
- **What it does**: Scrapes NSE India website for daily equity/index OHLCV data
- **Coverage**: Up to 3 years of daily data
- **No signup, no API key, no demat account**
- **Rate limit**: 1.5 second delay between requests (mandatory, NSE blocks aggressive scrapers)

### 2. NseIndiaApi (INTRADAY)
- **Package**: `pip install nse`
- **What it does**: Fetches historical intraday data from NSE India
- **Coverage**: 1h, 15m, 5m candle data
- **No signup, no API key, no demat account**
- **Built-in rate limiting**: 3 req/sec

### 3. NSE Bhavcopy (FALLBACK — Daily Only)
- **What it does**: Downloads official NSE end-of-day CSV archives
- **URL**: `https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip`
- **Coverage**: Daily OHLCV only
- **Guaranteed fallback**: Works even when NSE website is under maintenance

## Instruments (22 total)

### Equity (20 stocks)
RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK, HINDUNILVR, ITC, SBIN, BHARTIARTL, KOTAKBANK, LT, AXISBANK, ASIANPAINT, MARUTI, BAJFINANCE, TITAN, SUNPHARMA, HCLTECH, WIPRO, TATAMOTORS

### Index (2)
NIFTY 50, NIFTY BANK

## Timeframes

| Timeframe | Lookback | Source |
|-----------|----------|--------|
| 1d (daily) | 3 years | nsepython |
| 1h (hourly) | 1 year | NseIndiaApi |
| 15m | 6 months | NseIndiaApi |
| 5m | 3 months | NseIndiaApi |

## Daily Data Refresh

Set up a cron job to refresh data after market close:

```bash
# Add to crontab (6 PM IST = 12:30 PM UTC, weekdays only)
0 18 * * 1-5 cd /app/backend && python scripts/refresh_data.py >> /var/log/data_refresh.log 2>&1
```

Or trigger via admin API:
```bash
curl -X POST /api/v1/admin/data/refresh -H "Authorization: Bearer <admin_token>"
```

## Troubleshooting

### "NSE website is in maintenance"
- NSE India goes down for maintenance daily around 11:30 PM - 6:00 AM IST
- **Solution**: Run ingestion/refresh after 6 AM IST and before 11 PM IST
- Best time: **4-6 PM IST** (after market close, before maintenance)

### "Getting blocked by NSE"
- NSE rate-limits aggressive scrapers
- **Solution**: The ingestion script already adds 1.5s delay between requests
- If still blocked, wait 1-2 hours and retry

### "No data for symbol X"
- Check if the symbol is valid NSE equity symbol
- Some symbols may have limited historical data
- Index data (NIFTY 50, NIFTY BANK) uses a different API endpoint

### "Intraday data missing"
- If using `daily_only` strategy, only 1d data is available
- Re-run setup with `full` strategy: `python scripts/setup_data_source.py`

## Environment Variables

Only ONE env var needed in `.env`:
```
DATA_STRATEGY=full    # or daily_only
```

No API keys, no credentials, no tokens.

## Admin API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/admin/data/status` | GET | Full data health report |
| `/api/v1/admin/data/refresh` | POST | Trigger incremental refresh |
| `/api/v1/admin/users` | GET | List all users |
| `/api/v1/admin/analytics` | GET | Platform-wide stats |

All admin endpoints require JWT token with `role: "admin"`.
