import os
import argparse
# If DISPLAY is not set, switch Matplotlib to a non-interactive backend to avoid hangs on headless systems
if os.environ.get('DISPLAY', '') == '':
    import matplotlib
    matplotlib.use('Agg')

from utils.csv_loader import load_csv_data
from data.analyzer import calculate_asset_values, calculate_category_distribution
from visualization.pie_charts import generate_pie_charts


def main():
    parser = argparse.ArgumentParser(description="BetBoard")
    parser.add_argument("csv_path", help="Path to portfolio CSV file")
    parser.add_argument("--no-show", action="store_true", help="Do not display plots; print distributions instead")
    parser.add_argument("--simple", action="store_true", help="Use simple CSV format where Amount is current value (columns: Asset,Category,Amount[,Bucket])")
    parser.add_argument("--detailed", action="store_true", help="Do not club small asset slices into 'Other' on the Asset chart")
    args = parser.parse_args()

    # default: live price fetcher
    from data.analyzer import get_current_price as price_fetcher

    if args.simple:
        # load and compute directly from provided amounts
        from utils.csv_loader import load_simple_csv
        simple_rows = load_simple_csv(args.csv_path)
        from data.analyzer import calculate_from_values
        result = calculate_from_values(simple_rows)
        asset_values = result['asset_values']
        category_distribution = result['category_distribution']
        bucket_distribution = result.get('bucket_distribution', None)
    else:
        data = load_csv_data(args.csv_path)
        asset_values = calculate_asset_values(data, price_fetcher=price_fetcher)
        category_distribution = calculate_category_distribution(data, price_fetcher=price_fetcher)
        from data.analyzer import calculate_bucket_distribution
        bucket_distribution = calculate_bucket_distribution(data, price_fetcher=price_fetcher)

    if args.no_show:
        print('ASSETS')
        for k, v in asset_values.items():
            print(k, v)
        print('\nCATEGORIES')
        for k, v in category_distribution.items():
            print(k, v)
    else:
        generate_pie_charts(asset_values, category_distribution, bucket_distribution=bucket_distribution, detailed=args.detailed)


if __name__ == "__main__":
    main()