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
sample_path = os.path.join('src', 'data', 'test.csv')

csv_path = None
if uploaded is not None:
    csv_path = uploaded
elif use_sample:
    csv_path = sample_path

if csv_path:
    st.sidebar.write('Using:', csv_path if isinstance(csv_path, str) else uploaded.name)

# Options
detailed = st.sidebar.checkbox('Detailed Asset Chart', value=False)
# Show integer percent steps from 0..20 (whole numbers only). Convert to fraction for internal use.
combine_pct = st.sidebar.slider('Combine threshold (%)', 0, 20, 2, step=1)
combine_threshold = float(combine_pct) / 100.0

if csv_path:
    # st.header('Portfolio')
    try:
        if mode.startswith('Simple'):
            rows = load_simple_csv(csv_path)
            result = calculate_from_values(rows)
            asset_values = result['asset_values']
            category_distribution = result['category_distribution']
        else:
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

        # Render the two tables side-by-side so they align with the plots below
        col1, col2 = st.columns(2)
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

        fig = make_subplots(rows=1, cols=2, specs=[[{'type': 'domain'}, {'type': 'domain'}]],
                            subplot_titles=['Assets', 'Categories'])
        fig.add_trace(go.Pie(labels=a_labels, values=a_values, name='Assets'), 1, 1)
        fig.add_trace(go.Pie(labels=c_labels, values=c_values, name='Categories'), 1, 2)

        # show label + percent with one decimal, and hover shows value with one decimal
        fig.update_traces(textinfo='none',
                          texttemplate='%{label}<br>%{percent:.1%}',
                          hovertemplate='%{label}<br>%{value:,.1f} (%{percent:.1%})')
        fig.update_layout(margin=dict(t=50, b=0, l=0, r=0))

        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f'Failed to load or render CSV: {e}')
