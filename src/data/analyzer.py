import yfinance as yf
from pycoingecko import CoinGeckoAPI
import requests
from typing import Callable, Dict, List

cg = CoinGeckoAPI()
# Set a modest request timeout on the CoinGecko client to avoid long blocking calls
try:
    cg.request_timeout = 5
except Exception:
    # Older/newer versions may not expose this; it's a best-effort setting
    pass


def get_current_price(ticker: str, asset: str) -> float:
    """
    Fetch current USD price for a given ticker/asset.
    Returns 1.0 for CASH, tries CoinGecko for known crypto,
    then yfinance, then a Yahoo Finance HTTP fallback. Returns 0.0 if all fail.
    """
    if str(asset).upper() == "CASH":
        return 1.0

    # sanitize ticker: strip leading '$' if present (some APIs/logs use $SYMBOL)
    ticker = (ticker or '')
    if isinstance(ticker, str):
        ticker = ticker.lstrip('$').strip()

    # If the asset or ticker is a non-tradable label like 'Other', skip lookups
    if (isinstance(asset, str) and asset.strip().lower() == 'other') or (isinstance(ticker, str) and ticker.strip().lower() == 'other'):
        return 0.0

    # Map tickers to CoinGecko IDs
    cg_ids = {"BTC": "bitcoin", "ETH": "ethereum"}
    if ticker and ticker.upper() in cg_ids:
        try:
            cg_id = cg_ids[ticker.upper()]
            return float(cg.get_price(ids=cg_id, vs_currencies='usd')[cg_id]['usd'])
        except Exception:
            pass

    # Try yfinance
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except Exception:
        pass

    # Fallback: Yahoo Finance unofficial API
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={ticker}"
        response = requests.get(url, timeout=5)
        data = response.json()
        results = data.get('quoteResponse', {}).get('result', [])
        if results and 'regularMarketPrice' in results[0]:
            return float(results[0]['regularMarketPrice'])
    except Exception:
        pass

    return 0.0


def calculate_asset_values(data: List[dict], price_fetcher: Callable[[str, str], float] = get_current_price) -> Dict[str, float]:
    """
    Calculate total value per asset.
    `price_fetcher` is injectable for testing.
    """
    asset_values: Dict[str, float] = {}
    for entry in data:
        asset = entry.get('Asset', '') or ''
        ticker = entry.get('Ticker', '') or asset
        quantity = float(entry.get('Quantity', 0) or 0)
        price = price_fetcher(ticker, asset)
        asset_values[asset] = asset_values.get(asset, 0.0) + quantity * price
    return asset_values


def calculate_category_distribution(data: List[dict], price_fetcher: Callable[[str, str], float] = get_current_price) -> Dict[str, float]:
    """
    Aggregate values by category.
    """
    category_distribution: Dict[str, float] = {}
    for entry in data:
        category = entry.get('Category', '') or 'Uncategorized'
        asset = entry.get('Asset', '') or ''
        ticker = entry.get('Ticker', '') or asset
        quantity = float(entry.get('Quantity', 0) or 0)
        price = price_fetcher(ticker, asset)
        category_distribution[category] = category_distribution.get(category, 0.0) + quantity * price
    return category_distribution


def calculate_bucket_distribution(data: List[dict], price_fetcher: Callable[[str, str], float] = get_current_price) -> Dict[str, float]:
    """
    Aggregate values by Bucket (optional column). If Bucket is missing or empty,
    group under 'Unbucketed'.
    """
    bucket_distribution: Dict[str, float] = {}
    for entry in data:
        bucket = entry.get('Bucket', '') or 'Unbucketed'
        asset = entry.get('Asset', '') or ''
        ticker = entry.get('Ticker', '') or asset
        quantity = float(entry.get('Quantity', 0) or 0)
        price = price_fetcher(ticker, asset)
        bucket_distribution[bucket] = bucket_distribution.get(bucket, 0.0) + quantity * price
    return bucket_distribution


def calculate_from_values(data: List[dict]) -> Dict[str, Dict[str, float]]:
    """
    Given rows with keys 'Asset', 'Category', 'Amount' where 'Amount' is the current value,
    return two dicts: asset_values and category_distribution.
    This function does not fetch any live prices.
    """
    asset_values: Dict[str, float] = {}
    category_distribution: Dict[str, float] = {}
    bucket_distribution: Dict[str, float] = {}
    for entry in data:
        asset = entry.get('Asset', '') or ''
        category = entry.get('Category', '') or 'Uncategorized'
        amount = float(entry.get('Amount', 0) or 0)
        asset_values[asset] = asset_values.get(asset, 0.0) + amount
        category_distribution[category] = category_distribution.get(category, 0.0) + amount
        # Bucket aggregation for simple flow
        bucket = entry.get('Bucket', '') or 'Unbucketed'
        bucket_distribution[bucket] = bucket_distribution.get(bucket, 0.0) + amount

    return {'asset_values': asset_values, 'category_distribution': category_distribution, 'bucket_distribution': bucket_distribution}