# BetBoard

See your portfolio at a glance — expose fragility, rebalance with intent, and place smarter bets.

## Overview
BetBoard is a simple application that analyzes user-provided investment data and generates visual representations of the data through pie charts. It helps users understand their asset distribution and category breakdown.

## Project Structure
```
BetBoard
├── src
│   ├── main.py                # Entry point of the application
│   ├── data
│   │   └── analyzer.py        # Contains the PortfolioAnalyzer class for data analysis
│   ├── visualization
│   │   └── pie_charts.py      # Generates pie charts based on analysis results
│   └── utils
│       └── csv_loader.py      # Loads CSV data into a structured format
├── requirements.txt           # Lists project dependencies
├── README.md                  # Project documentation
```

## Installation
To set up the environment, follow these steps:

1. Clone the repository:
	```
	git clone <repository-url>
	cd BetBoard
	```

2. It is recommended to create a virtual environment:
	```
	python -m venv venv
	source venv/bin/activate  # On Windows use `venv\Scripts\activate`
	```

3. Install the required dependencies:
	```
	pip install -r requirements.txt
	```

## Usage
To run the application, execute the following command:
```
python src/main.py <path_to_csv_file>
```
Replace `<path_to_csv_file>` with the path to your CSV file containing asset data.

CLI options (short):

- `--no-show`  : print asset/category distributions to stdout instead of displaying plots
- `--simple`   : input CSV is the simple format (columns: Asset, Category, Amount[, Bucket])
- `--detailed` : do not combine small asset slices into an "Other" bucket (show all assets)

Example:

```
python src/main.py personal/nsh_simple.csv --simple --no-show
```

## Input Data Format
The CSV file should contain the following columns (headers are case-sensitive but whitespace is trimmed):
- `Asset`: The name or label of the asset (e.g., AAPL, BTC)
- `Ticker`: The market ticker symbol (used to fetch live prices)
- `Quantity`: The number of units held (numeric)
- `Category`: The holding category (e.g., Crypto, IRA, Savings)
- `Avg Buy Price`: (optional) the average buy price stored in your CSV

Example (matches `src/data/test.csv`):
```
Asset,Ticker,Quantity,Category,Avg Buy Price
Apple, AAPL,10,Taxable equity,150
VTI, VTI,2000,401K,80
BTC, BTC,0.5,Crypto,30000
ETH, ETH,2,Crypto,2000
GOOGL, GOOGL,5,IRA,120
CASH, CASH,10000,Savings,1
SWIGGY.NS, SWIGGY.NS,100,Taxable equity,330
```

## Generating Visualizations
Once the application processes the CSV data, it will generate two pie charts:
1. Asset Distribution: Shows the total value of each asset.
2. Category Distribution: Displays the distribution of assets by category.

Run examples:

# BetBoard

## Goal / Motivation

A small, local Python tool to visualize an investment portfolio as two pie charts (Assets and Categories). It supports two CSV modes:

- "Live" mode: fetches current prices for tickers (yfinance / CoinGecko) and computes values.
- "Simple" mode: reads already-calculated amounts from a CSV.

The project provides a Streamlit web UI for interactive exploration and a CLI for headless generation and image export.

These days many people spread holdings across several brokerages and wallets, which makes tracking allocation and concentration mentally taxing. BetBoard aims to be a single, unbiased view of your entire portfolio — reduce cognitive load, expose fragility, and help you make calculated, conviction-driven bets.

## Key features

- Functional, modular codebase (data loading, analysis, visualization).
- Two pie charts: Asset and Category distributions.
- Combine small slices into an "Other" slice with a configurable threshold.
- Simple CSV mode for fast offline usage.
- Streamlit UI with Plotly pies for a better interactive experience.
- Results saved into `results/` as date-stamped PNG/SVG when using the CLI.

## Requirements

- Python 3.9+ (project developed using 3.11)
- pip

The project dependencies are listed in `requirements.txt`.

## Quick install

Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux (zsh/bash)
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If you prefer, install into an existing environment instead of creating `.venv`.

## Running the Streamlit app (recommended for interactive use)

From the repository root (where `app.py` lives):

```bash
# from repo root
streamlit run app.py
```

Notes:

- The app imports project modules from `src/`. If you see import errors such as "No module named 'src'", run Streamlit from the repo root (the command above) so the relative import path works, or set PYTHONPATH to include `./src`:

```bash
export PYTHONPATH="$PWD/src"
streamlit run app.py
```

<!-- CLI usage removed: this README documents the Streamlit app. -->

Note: two Streamlit entry scripts exist: `app.py` (recommended canonical entrypoint) and `streamlit_app.py` (alternative UI; points to `personal/nsh_simple.csv` by default). Run the canonical UI from the repo root with `streamlit run app.py`.

## CSV formats

Two CSV formats are supported:

1) Simple CSV (for fast offline use)

- Columns: Asset, Category, Amount
- Example: `personal/nsh_simple.csv`

Optional column: `Bucket` — when present a Bucket Distribution chart is produced and used to show per-bucket asset breakdowns (e.g., Long-Term, Speculative).

2) Detailed CSV (for live price fetching)

- Expected columns (examples found in `personal/nsh.csv`): Asset, Ticker, Quantity, Category, Avg Buy Price
- The analyzer looks up `Ticker` via yfinance (or CoinGecko for crypto) to compute current Value = Quantity * CurrentPrice.

## Behavior & UI notes

- Combine threshold: a slider (in percent) controls when small slices are grouped into "Other". Set to 0 to disable combining.
- If the input CSV already contains a slice named "Other" (case-insensitive), small slices will be merged into that existing label instead of creating a duplicate.
- The Streamlit UI renders two compact tables (Assets and Categories) side-by-side above the pie charts and uses one decimal place for numeric values.

- The visualizer will attempt to download and register the "Lora" font into `fonts/` for improved typography; this requires network access and silently falls back to system fonts if the download or registration fails.

## Price fetching and runtime messages

- Live mode uses `yfinance` and `pycoingecko` where appropriate. Network errors or delisted tickers can produce warnings like "possibly delisted"; these are normal for tickers that don't resolve.
- The code sanitizes input tickers (it strips leading `$` and treats aggregated labels like "Other" as non-tickers) to avoid unnecessary lookup attempts.

Output when running headless: when a non-interactive backend is detected the visualizer saves a high-resolution PNG to `results/Portfolio-YYYY-MM-DD.png` (300 DPI) instead of calling `plt.show()`.

## Troubleshooting

- "No module named 'src'": run from the repo root or set `PYTHONPATH=./src` so `src` is importable.
- If Streamlit shows SyntaxError after edits: run a quick compile to detect the problem:

```bash
python3 -m py_compile app.py
```

- If plots show empty values, try `--simple` mode or provide a well-formed detailed CSV with `Ticker` and `Quantity`.

## Development notes

- Price fetcher is dependency-injected in `src/data/analyzer.py` which makes the analyzer easy to unit-test with a stubbed price-fetcher.
- Visualization helpers live in `src/visualization/pie_charts.py` and the Streamlit-specific presentation is in `app.py`.

## Files of interest

- `app.py` — Streamlit UI (interactive)
- `src/data/analyzer.py` — core calculations and price fetching
- `src/utils/csv_loader.py` — CSV parsing and validation
- `requirements.txt` — Python dependencies
- `personal/` — sample CSVs (`nsh.csv`, `nsh_simple.csv`)

## License

This repo does not include a license file. Add one if you plan to publish the project.

## Next suggestions (optional)

- Add a short `CONTRIBUTING.md` and basic unit tests for the analyzer functions.
- Add a GitHub Actions workflow to run linting and tests on push.