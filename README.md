# Crypto Mean-Reversion Experiment

vibecoded a random slopsperiment

A simple Python experiment that tests a **mean-reversion** strategy on the top 20 cryptocurrencies.

**The idea:** when a coin drops, buy more. When it rises, sell some. Does systematically "buying the dip and selling the rip" actually make money?

---

## What does it do?

1. **Fetches the top 20 coins** by market cap from [CoinGecko](https://www.coingecko.com/) (free, no API key needed)
2. **Downloads 365 days** of daily price data for each coin
3. **Simulates the strategy** starting with $1 in each coin ($20 total)
4. **Compares against buy-and-hold** (just buying $1 of each and doing nothing)
5. **Generates a chart** showing how the strategy performed

---

## The Strategy (simple version)

Every day, for each coin:

| What happened today | What we do | Example |
|---|---|---|
| Coin dropped 8% | **Buy more** — increase position by 8% | $1.00 → $1.08 |
| Coin rose 12% | **Sell some** — decrease position by 12% | $1.00 → $0.88 |

In code, the formula is:

```
trade_amount = -(daily return) × (current position value)
```

So if your position is worth $2.00 and the coin dropped 5%:
- `trade_amount = -(-0.05) × $2.00 = +$0.10` → you buy $0.10 more

**Safety limits:**
- No position can go below **$0.10** (prevents going to zero)
- No position can go above **$5.00** (prevents one coin eating your whole portfolio)
- Cash is tracked separately — when you sell, cash goes up, when you buy, cash goes down

---

## When does this strategy work?

| Market type | Strategy performance |
|---|---|
| **Sideways / choppy** | Works well — you're buying low and selling high repeatedly |
| **Strong uptrend** | Loses — you keep selling into strength while buy-and-hold rides it up |
| **Crash** | Risky — you keep buying on the way down |

This is essentially **volatility harvesting** — the strategy profits from mean-reversion (prices bouncing around), not from direction.

---

## Quick Start

### 1. Install Python

You need Python 3.7+ installed. Check with:

```bash
python3 --version
```

### 2. Install dependencies

```bash
cd bored-crypto-experiment
pip install -r requirements.txt
```

This installs three packages:
- **requests** — for calling the CoinGecko API
- **pandas** — for organizing price data into tables
- **matplotlib** — for making charts

### 3. Run the experiment

```bash
python3 experiment.py
```

This will:
- Fetch the top 20 coins (~30 seconds, rate-limited to be nice to the API)
- Download a year of price data for each (~30 seconds)
- Run the backtest
- Print results to the terminal
- Save a chart to `results.png`
- Open the chart in a window

---

## What you'll see

### Terminal output

```
=======================================================
  RESULTS
=======================================================
  Starting capital:         $20.00

  MEAN-REVERSION STRATEGY:
    Final value:            $XX.XX
    Return:                 +XX.XX%
    Cash on hand:           $X.XX
    Still invested:         $XX.XX

  BUY & HOLD (benchmark):
    Final value:            $XX.XX
    Return:                 +XX.XX%

  >>> Strategy BEAT/LOST to buy-and-hold by $X.XX
=======================================================
```

### Chart (`results.png`)

A 4-panel chart showing:

| Panel | What it shows |
|---|---|
| **Top left** | Portfolio value over time — strategy (green) vs buy-and-hold (red dashed) |
| **Top right** | Cash balance — how much money is sitting on the sidelines |
| **Bottom left** | Cumulative return % — same as top-left but in percentage terms |
| **Bottom right** | Final position sizes — bar chart of how much is in each coin at the end |

---

## Tweaking the settings

Open `experiment.py` and change the settings near the top:

```python
DAYS = 365              # how far back to look
START_PER_COIN = 1.0    # starting $ in each coin
MIN_POSITION = 0.10     # smallest allowed position ($)
MAX_POSITION = 5.00     # largest allowed position ($)
TOP_N = 20              # how many coins to trade
```

**Ideas to try:**
- Set `DAYS = 90` for a shorter window (might show different results)
- Set `MAX_POSITION = 10.0` to let positions grow bigger
- Set `TOP_N = 10` for fewer coins (faster to run)

---

## How the code works (for beginners)

The script has 4 main steps:

### Step 1: `get_top_coins()`
Calls the CoinGecko `/coins/markets` API to get the top coins ranked by market cap. Filters out stablecoins (USDT, USDC, etc.) since they don't move and would be useless for this experiment.

### Step 2: `download_all_prices()`
For each coin, calls `/coins/{id}/market_chart` to get daily price data. Waits 1.5 seconds between calls to avoid hitting rate limits. Combines everything into a pandas DataFrame where each column is a coin and each row is a day.

### Step 3: `run_strategy()`
The core loop. For each day:
1. **Mark to market** — update each position's value based on the actual price change
2. **Calculate trade** — figure out how much to buy/sell (proportional to the day's return)
3. **Apply limits** — enforce min/max position sizes
4. **Update cash** — selling adds cash, buying subtracts cash

Also tracks a buy-and-hold benchmark for comparison.

### Step 4: `show_results()`
Prints the final numbers and generates a matplotlib chart saved to `results.png`.

---

## Data source

All data comes from the **CoinGecko free API**:
- No API key required
- Rate limited to ~10-30 calls/minute
- Historical data available for 365 days
- Docs: https://docs.coingecko.com/reference/introduction

If you hit rate limits (HTTP 429), just wait a minute and try again.

---

## File structure

```
bored-crypto-experiment/
├── experiment.py       # the main script — run this
├── requirements.txt    # Python packages to install
├── README.md           # you are here
└── results.png         # generated chart (after running)
```

---

## Disclaimer

This is a **learning experiment**, not financial advice. Don't trade real money based on this. Crypto is volatile, past performance doesn't predict the future, and this backtest doesn't account for exchange fees, slippage, or taxes.
