def load_csv_data(file_path):
    import pandas as pd

    # Load the CSV file into a DataFrame
    df = pd.read_csv(file_path)

    # Normalize column names
    df.columns = [c.strip() for c in df.columns]

    # Ensure numeric columns are parsed
    if 'Quantity' in df.columns:
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
    if 'Avg Buy Price' in df.columns:
        df['Avg Buy Price'] = pd.to_numeric(df['Avg Buy Price'], errors='coerce').fillna(0)

    # Preserve optional Bucket column if present
    if 'Bucket' in df.columns:
        df['Bucket'] = df['Bucket'].astype(str).str.strip().replace({'': None})

    # Convert the DataFrame to a list of dictionaries
    data = df.to_dict(orient='records')

    return data


def load_simple_csv(file_path):
    """
    Load a simple CSV with columns: Asset, Category, Amount
    - Strips commas from Amount and coerces to numeric
    - Returns list[dict] with keys 'Asset','Category','Amount'
    """
    import pandas as pd

    df = pd.read_csv(file_path)
    df.columns = [c.strip() for c in df.columns]

    # Expect required columns; optional 'Bucket' allowed
    expected = {'asset', 'category', 'amount'}
    found = {c.strip().lower() for c in df.columns}
    if not expected.issubset(found):
        raise ValueError(f"Simple CSV must contain headers: Asset, Category, Amount. Found: {df.columns.tolist()}")

    # Normalize column names to expected casing
    col_map = {}
    for c in df.columns:
        lc = c.strip().lower()
        if lc == 'asset':
            col_map[c] = 'Asset'
        elif lc == 'category':
            col_map[c] = 'Category'
        elif lc == 'amount':
            col_map[c] = 'Amount'

    df = df.rename(columns=col_map)

    # Strip commas (e.g., 1,000) from Amount and coerce to numeric
    df['Amount'] = df['Amount'].astype(str).str.replace(',', '')
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)

    # Normalize optional Bucket column
    if 'Bucket' in df.columns or 'bucket' in found:
        # map case-insensitive name to actual column if needed
        for c in df.columns:
            if c.strip().lower() == 'bucket':
                df = df.rename(columns={c: 'Bucket'})
                break
        df['Bucket'] = df['Bucket'].astype(str).str.strip().replace({'': None})

    return df.to_dict(orient='records')