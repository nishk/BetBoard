import streamlit as st
import os
import sys
import pandas as pd

# Ensure src is importable when running from repo root or inside venv
ROOT = os.path.dirname(__file__)
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from utils.csv_loader import load_csv_data, load_simple_csv
from data.analyzer import (
    calculate_asset_values,
    calculate_category_distribution,
    calculate_from_values,
    get_current_price,
)

st.set_page_config(page_title='BetBoard', layout='wide')

st.title('BetBoard')

st.sidebar.header('Input')
mode = st.sidebar.selectbox('Mode', ['Live (fetch prices)', 'Simple (values provided)'])
uploaded = st.sidebar.file_uploader('Upload CSV', type=['csv'])
use_sample = st.sidebar.checkbox('Use sample CSV', value=True)

if uploaded is None and not use_sample:
    st.sidebar.info('Upload a CSV or select sample')

# sample path
sample_path = os.path.join('personal', 'nsh_simple.csv')

csv_path = None
if uploaded is not None:
    csv_path = uploaded
elif use_sample:
    csv_path = sample_path

if csv_path:
    st.sidebar.write('Using:', csv_path if isinstance(csv_path, str) else uploaded.name)

# Options
detailed = st.sidebar.checkbox('Detailed Asset Chart', value=False)
combine_threshold = st.sidebar.slider('Combine threshold (%)', 0.0, 10.0, 2.0) / 100.0

if csv_path:
    # st.header('Portfolio')
    try:
        # Handle Simple vs Live mode. If user selected Simple but their CSV doesn't contain
        # an 'Amount' column, fall back to Live mode (using Ticker/Quantity) and warn.
        rows = None
        data = None
        if mode.startswith('Simple'):
            # Peek at CSV headers to ensure 'Amount' exists; if not, fallback to live
            try:
                # If csv_path is a Streamlit uploaded file (file-like), ensure pointer is at 0
                if not isinstance(csv_path, str):
                    try:
                        csv_path.seek(0)
                    except Exception:
                        pass
                peek_cols = {c.strip().lower() for c in pd.read_csv(csv_path, nrows=0).columns}
            except Exception:
                peek_cols = set()

            if 'amount' not in peek_cols:
                # Try to synthesize Amount from Quantity * Avg Buy Price without performing live price fetches
                # If csv_path is a file-like uploaded object, reset pointer first
                if not isinstance(csv_path, str):
                    try:
                        csv_path.seek(0)
                    except Exception:
                        pass
                df_peek = pd.read_csv(csv_path)
                # normalize column lookup by lowercasing stripped names
                col_map = {c.strip().lower(): c for c in df_peek.columns}
                if 'quantity' in col_map and ('avg buy price' in col_map or 'avg_buy_price' in col_map or 'avgbuyprice' in col_map):
                    # find the actual Avg Buy Price column name
                    abp_key = None
                    for key in ('avg buy price', 'avg_buy_price', 'avgbuyprice'):
                        if key in col_map:
                            abp_key = col_map[key]
                            break
                    qty_col = col_map['quantity']
                    try:
                        df_peek[qty_col] = pd.to_numeric(df_peek[qty_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                        df_peek[abp_key] = pd.to_numeric(df_peek[abp_key].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                        df_peek['Amount'] = df_peek[qty_col] * df_peek[abp_key]
                        # Build simple rows expected by calculate_from_values
                        # Ensure we have Asset and Category columns
                        if 'asset' in col_map and 'category' in col_map:
                            asset_col = col_map['asset']
                            category_col = col_map['category']
                            simple_df = df_peek[[asset_col, category_col, 'Amount']].rename(columns={asset_col: 'Asset', category_col: 'Category'})
                            # Preserve optional Bucket column if present
                            if 'bucket' in col_map:
                                simple_df['Bucket'] = df_peek[col_map['bucket']].astype(str).str.strip().replace({'': None})
                            rows = simple_df.to_dict(orient='records')
                            result = calculate_from_values(rows)
                            asset_values = result['asset_values']
                            category_distribution = result['category_distribution']
                        else:
                            raise ValueError("Simple mode requires 'Asset' and 'Category' columns when synthesizing Amount from Quantity and Avg Buy Price.")
                    except Exception as exc:
                        raise ValueError(f"Failed to synthesize Amount from Quantity and Avg Buy Price: {exc}")
                else:
                    raise ValueError("Simple mode expects an 'Amount' column or Quantity+Avg Buy Price columns to compute amounts; no fallback to live mode.")
            else:
                # Ensure file pointer reset for loader if necessary
                if not isinstance(csv_path, str):
                    try:
                        csv_path.seek(0)
                    except Exception:
                        pass
                rows = load_simple_csv(csv_path)
                result = calculate_from_values(rows)
                asset_values = result['asset_values']
                category_distribution = result['category_distribution']
        else:
            # Reset file pointer for loader if necessary
            if not isinstance(csv_path, str):
                try:
                    csv_path.seek(0)
                except Exception:
                    pass
            data = load_csv_data(csv_path)
            # default: live fetcher uses get_current_price which will hit network
            asset_values = calculate_asset_values(data, price_fetcher=get_current_price)
            category_distribution = calculate_category_distribution(data, price_fetcher=get_current_price)

    # Show distributions in tables (with headers) and format numbers to 1 decimal place
        # Use HTML output to reliably hide the index column and center-align text
        assets_df = pd.DataFrame(sorted(asset_values.items(), key=lambda x: x[1], reverse=True), columns=['Asset', 'Value'])
        assets_html = (
            "<style>table.dataframe td, table.dataframe th { text-align: center; }</style>"
            + assets_df.to_html(index=False, float_format='%.1f')
        )

        cats_df = pd.DataFrame(sorted(category_distribution.items(), key=lambda x: x[1], reverse=True), columns=['Category', 'Value'])
        cats_html = (
            "<style>table.dataframe td, table.dataframe th { text-align: center; }</style>"
            + cats_df.to_html(index=False, float_format='%.1f')
        )

        # Determine source rows and whether an actual 'Bucket' column exists
        source_rows = rows if mode.startswith('Simple') else data
        has_bucket_column = False
        try:
            for entry in source_rows:
                if isinstance(entry, dict) and 'Bucket' in entry and entry.get('Bucket') not in (None, '', 'None'):
                    has_bucket_column = True
                    break
        except Exception:
            has_bucket_column = False

        # Bucket distribution (only compute if Bucket column is present)
        bucket_distribution = {}
        if has_bucket_column:
            if mode.startswith('Simple'):
                try:
                    bucket_distribution = result.get('bucket_distribution', {})
                except Exception:
                    bucket_distribution = {}
            else:
                try:
                    from data.analyzer import calculate_bucket_distribution
                    bucket_distribution = calculate_bucket_distribution(data, price_fetcher=get_current_price)
                except Exception:
                    bucket_distribution = {}

        buckets_df = pd.DataFrame(sorted(bucket_distribution.items(), key=lambda x: x[1], reverse=True), columns=['Bucket', 'Value']) if bucket_distribution else pd.DataFrame(columns=['Bucket', 'Value'])
        buckets_html = (
            "<style>table.dataframe td, table.dataframe th { text-align: center; }</style>"
            + buckets_df.to_html(index=False, float_format='%.1f')
        ) if has_bucket_column else ""

        # Render tables: show 3 columns only if bucket data exists; otherwise show 2 columns
        if has_bucket_column:
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                st.subheader('Asset Distribution')
                st.markdown(assets_html, unsafe_allow_html=True)
            with col2:
                st.subheader('Category Distribution')
                st.markdown(cats_html, unsafe_allow_html=True)
            with col3:
                st.subheader('Bucket Distribution')
                st.markdown(buckets_html, unsafe_allow_html=True)
        else:
            col1, col2 = st.columns([1, 1])
            with col1:
                st.subheader('Asset Distribution')
                st.markdown(assets_html, unsafe_allow_html=True)
            with col2:
                st.subheader('Category Distribution')
                st.markdown(cats_html, unsafe_allow_html=True)

        # Prepare and render Plotly pies directly for better Streamlit UX
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        def prepare_pie_data(data_dict, combine_threshold, respect_existing_other=True):
            """
            Return labels and values applying combining logic similar to plot_pie.
            If combine_threshold == 0, do not combine.
            """
            items = [(k, float(v)) for k, v in data_dict.items() if float(v) > 0]
            total = sum(v for _, v in items)
            if total == 0:
                return [], []

            # detect existing other
            existing_other = None
            for k, _ in items:
                if 'other' in str(k).strip().lower():
                    existing_other = k
                    break

            # split
            if combine_threshold and combine_threshold > 0:
                big = []
                small_sum = 0.0
                for k, v in items:
                    if v / total < combine_threshold:
                        small_sum += v
                    else:
                        big.append((k, v))
                if small_sum > 0:
                    if existing_other is not None:
                        # add to existing other
                        for i, (k, v) in enumerate(big):
                            if 'other' in str(k).strip().lower():
                                big[i] = (k, v + small_sum)
                                break
                        else:
                            big.append((existing_other, small_sum))
                    else:
                        big.append(('Other', small_sum))
                labels = [k for k, _ in big]
                values = [v for _, v in big]
            else:
                labels = [k for k, _ in items]
                values = [v for _, v in items]

            # sort descending
            pairs = list(zip(labels, values))
            pairs.sort(key=lambda x: x[1], reverse=True)
            labels, values = zip(*pairs) if pairs else ([], [])
            return list(labels), list(values)

        # apply combine threshold to assets unless detailed view is requested
        asset_threshold = 0 if detailed else combine_threshold
        a_labels, a_values = prepare_pie_data(asset_values, asset_threshold)
        c_labels, c_values = prepare_pie_data(category_distribution, combine_threshold)

        # Create subplots: include bucket pie if we have bucket data
        # We will render the main three pies on the first row, and two bucket-specific
        # asset-breakdown pies on the second row (Long-Term & Speculative) centered.
        # Prepare per-bucket asset breakdowns so we can show asset-level pies for each bucket.
        bucket_asset_breakdowns = {}
        try:
            # pick source rows depending on mode
            source_rows = rows if mode.startswith('Simple') else data
            for entry in source_rows:
                b = (entry.get('Bucket') or 'Unbucketed') if isinstance(entry, dict) else 'Unbucketed'
                asset = (entry.get('Asset') or '') if isinstance(entry, dict) else ''
                if mode.startswith('Simple'):
                    value = float(entry.get('Amount') or 0)
                else:
                    qty = float(entry.get('Quantity') or 0)
                    ticker = entry.get('Ticker') or asset
                    # use the same price fetcher used earlier
                    price = get_current_price(ticker, asset)
                    value = qty * price
                bucket_asset_breakdowns.setdefault(b, {})
                bucket_asset_breakdowns[b][asset] = bucket_asset_breakdowns[b].get(asset, 0.0) + value
        except Exception:
            bucket_asset_breakdowns = {}

        # Create subplots conditionally: include bucket-related charts only when bucket data exists
        if has_bucket_column and bucket_distribution and sum(bucket_distribution.values()) > 0:
            # Full layout: top row (Assets, Categories, Buckets), bottom row (Long-Term, Speculative centered)
            fig = make_subplots(rows=2, cols=3,
                                specs=[[{'type': 'domain'}, {'type': 'domain'}, {'type': 'domain'}],
                                       [{'type': 'domain'}, {'type': 'domain'}, {'type': 'domain'}]],
                                row_heights=[0.55, 0.45],
                                vertical_spacing=0.08,
                                subplot_titles=['Assets', 'Categories', 'Buckets', '', 'Long-Term', 'Speculative'])

            # Top row
            fig.add_trace(go.Pie(labels=a_labels, values=a_values, name='Assets'), 1, 1)
            fig.add_trace(go.Pie(labels=c_labels, values=c_values, name='Categories'), 1, 2)
            b_labels, b_values = prepare_pie_data(bucket_distribution, combine_threshold)
            fig.add_trace(go.Pie(labels=b_labels, values=b_values, name='Buckets'), 1, 3)

            # Bottom row: only add per-bucket pies if there is asset-level data for those buckets
            target_buckets = ['Long-Term', 'Speculative']
            for idx, bname in enumerate(target_buckets):
                col = 2 + idx  # places in column 2 and 3
                items = bucket_asset_breakdowns.get(bname, {}) if bucket_asset_breakdowns else {}
                blabels, bvalues = prepare_pie_data(items, combine_threshold)
                if blabels and sum(bvalues) > 0:
                    fig.add_trace(go.Pie(labels=blabels, values=bvalues, name=bname), 2, col)
        else:
            # Simpler layout: only Assets and Categories
            fig = make_subplots(rows=1, cols=2, specs=[[{'type': 'domain'}, {'type': 'domain'}]],
                                subplot_titles=['Assets', 'Categories'])
            fig.add_trace(go.Pie(labels=a_labels, values=a_values, name='Assets'), 1, 1)
            fig.add_trace(go.Pie(labels=c_labels, values=c_values, name='Categories'), 1, 2)

        # show label + percent with one decimal, and hover shows value with one decimal
        fig.update_traces(textinfo='none',
                          texttemplate='%{label}<br>%{percent:.1%}',
                          hovertemplate='%{label}<br>%{value:,.1f} (%{percent:.1%})')

        # Increase overall figure height so pies render larger. Streamlit will allow scrolling.
        fig.update_layout(height=900, margin=dict(t=80, b=40, l=20, r=20))

        # Ensure legend/font sizes are comfortable
        fig.update_layout(legend=dict(font=dict(size=11)))

        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f'Failed to load or render CSV: {e}')
