"""
Crypto Mean-Reversion Experiment
=================================
Buy weakness, sell strength — starting with $1 in each of the top 20 coins.

Strategy:
  - If a coin drops 8% today  → increase your position by 8%
  - If a coin rises 12% today → decrease your position by 12%
  - Track cash separately (selling adds to cash, buying uses cash)
  - Cap each position between $0.10 and $5.00

Compares against a simple buy-and-hold benchmark.
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
import time
import sys

# ============================================================
# SETTINGS — change these to tweak the experiment
# ============================================================

DAYS = 365                  # how far back to look (max 365 for free API)
START_PER_COIN = 1.0        # starting dollars in each coin
MIN_POSITION = 0.10         # minimum position size ($)
MAX_POSITION = 5.00         # maximum position size ($)
TOP_N = 20                  # how many coins to trade
RATE_LIMIT_DELAY = 1.5      # seconds between API calls (demo key = ~30/min)
MAX_RETRIES = 3             # retry failed API calls this many times

# CoinGecko Demo API key (free tier, higher rate limits)
API_KEY = "CG-YfbUADruwvwbQVBpGnj3NJ8P"
HEADERS = {"x-cg-demo-api-key": API_KEY}

# stablecoins, wrapped tokens & non-crypto assets to skip
SKIP_COINS = {
    "tether", "usd-coin", "dai", "binance-usd", "trueusd",
    "paxos-standard", "frax", "usdd", "gemini-dollar",
    "first-digital-usd", "ethena-usde", "paypal-usd",
    "tether-gold", "wrapped-bitcoin", "staked-ether",
    "lido-staked-ether", "wrapped-steth", "rocket-pool-eth",
    "coinbase-wrapped-staked-eth", "wrapped-eeth",
    "usds", "figure-heloc", "canton", "usd1", "memecore",
    "whitebit", "leo-token", "rain",
}

MIN_DAYS = 300  # skip coins with less history than this

# CoinGecko API base URL
BASE_URL = "https://api.coingecko.com/api/v3"


# ============================================================
# STEP 1: Get the top coins by market cap
# ============================================================

def get_top_coins():
    """Fetch top coins from CoinGecko, filter out stablecoins."""
    print(f"Fetching top coins by market cap...")

    url = f"{BASE_URL}/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": TOP_N + 15,   # fetch extra to account for filtering
        "page": 1,
    }

    response = api_get(url, params=params)

    if response.status_code != 200:
        print(f"  API returned status {response.status_code}")
        print("  Using fallback coin list instead...")
        return get_fallback_coins()

    data = response.json()

    # filter out stablecoins and wrapped tokens
    coins = []
    for coin in data:
        coin_id = coin["id"]
        if coin_id not in SKIP_COINS:
            coins.append({
                "id": coin_id,
                "name": coin["name"],
                "symbol": coin["symbol"].upper(),
            })
        if len(coins) == TOP_N:
            break

    print(f"Selected {len(coins)} coins:")
    for i, c in enumerate(coins, 1):
        print(f"  {i:2d}. {c['name']} ({c['symbol']})")

    return coins


def get_fallback_coins():
    """Hardcoded fallback list if the API is down."""
    names = [
        ("bitcoin", "Bitcoin", "BTC"),
        ("ethereum", "Ethereum", "ETH"),
        ("solana", "Solana", "SOL"),
        ("binancecoin", "BNB", "BNB"),
        ("ripple", "XRP", "XRP"),
        ("cardano", "Cardano", "ADA"),
        ("dogecoin", "Dogecoin", "DOGE"),
        ("tron", "TRON", "TRX"),
        ("polkadot", "Polkadot", "DOT"),
        ("avalanche-2", "Avalanche", "AVAX"),
        ("chainlink", "Chainlink", "LINK"),
        ("shiba-inu", "Shiba Inu", "SHIB"),
        ("toncoin", "Toncoin", "TON"),
        ("polygon-ecosystem-token", "POL", "POL"),
        ("litecoin", "Litecoin", "LTC"),
        ("bitcoin-cash", "Bitcoin Cash", "BCH"),
        ("uniswap", "Uniswap", "UNI"),
        ("cosmos", "Cosmos", "ATOM"),
        ("stellar", "Stellar", "XLM"),
        ("near", "NEAR Protocol", "NEAR"),
    ]
    print(f"Using {len(names)} fallback coins:")
    coins = []
    for coin_id, name, symbol in names:
        coins.append({"id": coin_id, "name": name, "symbol": symbol})
        print(f"  {len(coins):2d}. {name} ({symbol})")
    return coins


# ============================================================
# STEP 2: Download historical price data
# ============================================================

def api_get(url, params=None):
    """Make a GET request with retry logic for rate limiting."""
    for attempt in range(MAX_RETRIES):
        response = requests.get(url, params=params, headers=HEADERS)

        if response.status_code == 200:
            return response

        if response.status_code == 429:  # rate limited
            wait = (attempt + 1) * 10    # wait 10s, 20s, 30s
            print(f"rate limited, waiting {wait}s...", end=" ", flush=True)
            time.sleep(wait)
        else:
            return response  # other error, don't retry

    return response  # return last response even if failed


def get_price_history(coin_id):
    """Get daily prices for one coin from CoinGecko."""
    url = f"{BASE_URL}/coins/{coin_id}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": DAYS,
        "interval": "daily",
    }

    response = api_get(url, params=params)

    if response.status_code != 200:
        return None

    data = response.json()

    if "prices" not in data:
        return None

    # data["prices"] = list of [timestamp_ms, price]
    prices = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
    prices["date"] = pd.to_datetime(prices["timestamp"], unit="ms").dt.date
    prices = prices.groupby("date")["price"].last()  # one price per day

    return prices


def download_all_prices(coins):
    """Download price data for all coins with rate limiting."""
    print(f"\nDownloading {DAYS} days of price data...")

    all_prices = {}

    for i, coin in enumerate(coins):
        coin_id = coin["id"]
        print(f"  [{i+1}/{len(coins)}] {coin['name']}...", end=" ", flush=True)

        prices = get_price_history(coin_id)

        if prices is not None and len(prices) > 0:
            if len(prices) < MIN_DAYS:
                print(f"SKIPPED (only {len(prices)} days, need {MIN_DAYS})")
            else:
                all_prices[coin_id] = prices
                print(f"got {len(prices)} days")
        else:
            print("SKIPPED (no data)")

        # don't hammer the API
        if i < len(coins) - 1:
            time.sleep(RATE_LIMIT_DELAY)

    # combine into one table (each column = one coin)
    df = pd.DataFrame(all_prices)
    df = df.dropna()  # only keep days where ALL coins have data

    print(f"\nReady: {len(df)} trading days for {len(df.columns)} coins")

    return df


# ============================================================
# STEP 3: Run the mean-reversion strategy
# ============================================================

def run_strategy(prices_df):
    """
    The main experiment.

    For each day:
      1. Update position values based on actual price change
      2. Calculate adjustment = -(daily return) * position value
         - Coin went DOWN 8%  → add 8% of position value (buy more)
         - Coin went UP 12%   → remove 12% of position value (sell)
      3. Enforce min/max position limits
      4. Track cash balance (sells add to cash, buys use cash)
    """
    coins = list(prices_df.columns)
    num_days = len(prices_df)

    # --- starting state ---
    positions = {coin: START_PER_COIN for coin in coins}   # $ value in each coin
    cash = 0.0                                              # starts at $0

    total_start = START_PER_COIN * len(coins)

    # --- tracking lists ---
    dates = [prices_df.index[0]]
    portfolio_values = [total_start]
    cash_history = [cash]
    invested_history = [total_start]

    # --- buy-and-hold benchmark ---
    # buy $1 of each coin on day 0, never touch it
    start_prices = prices_df.iloc[0]
    bh_shares = {coin: START_PER_COIN / start_prices[coin] for coin in coins}
    bh_values = [total_start]

    print(f"\nRunning strategy over {num_days} days...")
    print(f"Starting capital: ${total_start:.2f} (${START_PER_COIN} x {len(coins)} coins)\n")

    # --- simulate each day ---
    for day in range(1, num_days):

        for coin in coins:
            prev_price = prices_df.iloc[day - 1][coin]
            curr_price = prices_df.iloc[day][coin]

            # daily return (e.g. -0.08 = down 8%, +0.12 = up 12%)
            daily_return = (curr_price - prev_price) / prev_price

            # 1) mark-to-market: update position value from price change
            positions[coin] = positions[coin] * (curr_price / prev_price)

            # 2) calculate trade: buy if down, sell if up
            trade_amount = -daily_return * positions[coin]

            # 3) apply trade and enforce limits
            new_position = positions[coin] + trade_amount
            new_position = max(MIN_POSITION, min(MAX_POSITION, new_position))

            actual_trade = new_position - positions[coin]

            # 4) update cash and position
            cash -= actual_trade        # selling = +cash, buying = -cash
            positions[coin] = new_position

        # record today's totals
        invested = sum(positions.values())
        total = invested + cash

        dates.append(prices_df.index[day])
        portfolio_values.append(total)
        cash_history.append(cash)
        invested_history.append(invested)

        # buy-and-hold for today
        bh_total = sum(bh_shares[coin] * prices_df.iloc[day][coin] for coin in coins)
        bh_values.append(bh_total)

    results = {
        "dates": dates,
        "portfolio_values": portfolio_values,
        "cash_history": cash_history,
        "invested_history": invested_history,
        "bh_values": bh_values,
        "positions": positions,
        "cash": cash,
        "total_start": total_start,
    }
    return results


# ============================================================
# STEP 4: Show results and plot graphs
# ============================================================

def show_results(results):
    """Print final numbers and create a 4-panel chart."""
    total_start = results["total_start"]
    final_value = results["portfolio_values"][-1]
    final_bh = results["bh_values"][-1]
    cash = results["cash"]
    positions = results["positions"]

    strategy_return = (final_value - total_start) / total_start * 100
    bh_return = (final_bh - total_start) / total_start * 100

    print("=" * 55)
    print("  RESULTS")
    print("=" * 55)
    print(f"  Starting capital:         ${total_start:.2f}")
    print()
    print(f"  MEAN-REVERSION STRATEGY:")
    print(f"    Final value:            ${final_value:.2f}")
    print(f"    Return:                 {strategy_return:+.2f}%")
    print(f"    Cash on hand:           ${cash:.2f}")
    print(f"    Still invested:         ${sum(positions.values()):.2f}")
    print()
    print(f"  BUY & HOLD (benchmark):")
    print(f"    Final value:            ${final_bh:.2f}")
    print(f"    Return:                 {bh_return:+.2f}%")
    print()

    diff = final_value - final_bh
    if diff > 0:
        print(f"  >>> Strategy BEAT buy-and-hold by ${diff:.2f}")
    else:
        print(f"  >>> Strategy LOST to buy-and-hold by ${-diff:.2f}")

    print("=" * 55)

    # ----------------------------------------------------------
    # CHARTS
    # ----------------------------------------------------------
    dates = results["dates"]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        "Crypto Mean-Reversion Experiment\n"
        "Buy the dip, sell the rip — Top 20 coins, $1 each",
        fontsize=15, fontweight="bold",
    )

    # --- Chart 1: Portfolio value over time ---
    ax1 = axes[0][0]
    ax1.plot(dates, results["portfolio_values"],
             label="Mean-Reversion", color="#2ecc71", linewidth=2)
    ax1.plot(dates, results["bh_values"],
             label="Buy & Hold", color="#e74c3c", linewidth=2, linestyle="--")
    ax1.axhline(y=total_start, color="gray", linestyle=":", alpha=0.5,
                label=f"Start (${total_start:.0f})")
    ax1.set_title("Portfolio Value Over Time")
    ax1.set_ylabel("Value ($)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # --- Chart 2: Cash balance over time ---
    ax2 = axes[0][1]
    ax2.fill_between(dates, results["cash_history"], alpha=0.3, color="#3498db")
    ax2.plot(dates, results["cash_history"], color="#3498db", linewidth=2)
    ax2.axhline(y=0, color="gray", linestyle=":", alpha=0.5)
    ax2.set_title("Cash Balance Over Time")
    ax2.set_ylabel("Cash ($)")
    ax2.grid(True, alpha=0.3)

    # --- Chart 3: Cumulative return % ---
    ax3 = axes[1][0]
    strat_pct = [(v - total_start) / total_start * 100
                 for v in results["portfolio_values"]]
    bh_pct = [(v - total_start) / total_start * 100
              for v in results["bh_values"]]
    ax3.plot(dates, strat_pct,
             label="Mean-Reversion", color="#2ecc71", linewidth=2)
    ax3.plot(dates, bh_pct,
             label="Buy & Hold", color="#e74c3c", linewidth=2, linestyle="--")
    ax3.axhline(y=0, color="gray", linestyle=":", alpha=0.5)
    ax3.set_title("Cumulative Return (%)")
    ax3.set_ylabel("Return (%)")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # --- Chart 4: Final position sizes (horizontal bar chart) ---
    ax4 = axes[1][1]
    sorted_pos = sorted(positions.items(), key=lambda x: x[1], reverse=True)
    names = [name.replace("-", " ").title()[:12] for name, _ in sorted_pos]
    values = [val for _, val in sorted_pos]
    colors = ["#2ecc71" if v >= START_PER_COIN else "#e74c3c" for v in values]
    ax4.barh(names, values, color=colors)
    ax4.axvline(x=START_PER_COIN, color="gray", linestyle=":",
                alpha=0.7, label=f"Start (${START_PER_COIN})")
    ax4.set_title("Final Position Sizes")
    ax4.set_xlabel("Value ($)")
    ax4.legend()
    ax4.invert_yaxis()

    plt.tight_layout()
    plt.savefig("results.png", dpi=150, bbox_inches="tight")
    print(f"\nChart saved to results.png")

    # show chart if running interactively (not headless)
    try:
        plt.show()
    except Exception:
        pass


# ============================================================
# MAIN — run everything
# ============================================================

if __name__ == "__main__":
    print()
    print("=" * 55)
    print("  CRYPTO MEAN-REVERSION EXPERIMENT")
    print("  Buy the dip, sell the rip")
    print("=" * 55)
    print()

    # Step 1: figure out which coins to use
    coins = get_top_coins()

    # Step 2: download historical prices
    prices_df = download_all_prices(coins)

    if len(prices_df) < 10:
        print("\nNot enough data to run the experiment.")
        print("The CoinGecko free API may be rate-limiting you.")
        print("Wait a minute and try again, or reduce TOP_N.")
        sys.exit(1)

    # Step 3: run the strategy
    results = run_strategy(prices_df)

    # Step 4: show results + charts
    show_results(results)
