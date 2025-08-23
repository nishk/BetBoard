from matplotlib import pyplot as plt
from matplotlib import font_manager as fm
from typing import Dict, Tuple
import os
import io


def ensure_lora_font():
    """Ensure the 'Lora' font is available to Matplotlib.

    - If already installed, do nothing.
    - Otherwise try to download Lora TTFs from the Google Fonts GitHub repo and register them.
    - If download/register fails, silently fall back to default fonts.
    """
    try:
        # Check existing fonts
        for f in fm.fontManager.ttflist:
            if getattr(f, 'name', '').lower() == 'lora':
                return True

        # Attempt to download Lora fonts (Regular + Bold)
        urls = [
            'https://github.com/google/fonts/raw/main/ofl/lora/Lora-Regular.ttf',
            'https://github.com/google/fonts/raw/main/ofl/lora/Lora-Bold.ttf',
        ]
        try:
            import requests
        except Exception:
            return False

        fonts_dir = os.path.join(os.getcwd(), 'fonts')
        os.makedirs(fonts_dir, exist_ok=True)
        downloaded = False
        for url in urls:
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    fname = os.path.basename(url)
                    dst = os.path.join(fonts_dir, fname)
                    with open(dst, 'wb') as fh:
                        fh.write(r.content)
                    # register
                    fm.fontManager.addfont(dst)
                    downloaded = True
            except Exception:
                # continue trying other fonts
                continue

        if downloaded:
            # rebuild cache
            try:
                fm._rebuild()
            except Exception:
                pass
            return True
    except Exception:
        return False
    return False




def plot_pie(data: Dict[str, float], title: str, ax=None, combine_threshold: float = 0.02, direction: str = 'clockwise') -> Tuple[plt.Figure, plt.Axes]:
    """
    Plot a pie chart with strategies to reduce label overlap.

    - combine_threshold: fractions < this (of total) will be grouped into an 'Other' slice.
    """
    labels = list(data.keys())
    sizes = [float(v) for v in data.values()]
    total = sum(sizes) if sizes else 0.0

    # Optionally combine small slices into 'Other' to avoid clutter
    if total > 0 and combine_threshold and combine_threshold > 0:
        # detect if input already contains an 'other' label (case-insensitive)
        existing_other_idx = None
        for i, lbl in enumerate(labels):
            if 'other' in str(lbl).strip().lower():
                existing_other_idx = i
                break

        large_labels = []
        large = []
        small_sum = 0.0
        for i, (lbl, val) in enumerate(zip(labels, sizes)):
            # always keep existing 'Other' as a major bucket and add smalls into it
            if existing_other_idx is not None and i == existing_other_idx:
                large_labels.append(lbl)
                large.append(val)
            elif val / total < combine_threshold:
                small_sum += val
            else:
                large_labels.append(lbl)
                large.append(val)

        if small_sum > 0:
            if existing_other_idx is not None:
                # add small_sum into the existing 'Other' bucket
                for j, lbl in enumerate(large_labels):
                    if 'other' in str(lbl).strip().lower():
                        large[j] = large[j] + small_sum
                        break
            else:
                large_labels.append('Other')
                large.append(small_sum)

        labels, sizes = large_labels, large

    # Order by descending size (Pareto) to reduce label overlap and follow power-law ordering
    if sizes:
        combined = list(zip(labels, sizes))
        # sort by size descending
        combined.sort(key=lambda x: x[1], reverse=True)
        labels, sizes = zip(*combined)
        labels = list(labels)
        sizes = list(sizes)

    # Try to ensure Lora font is available; if so, use it for titles and legend
    lora_ok = ensure_lora_font()
    if lora_ok:
        plt.rcParams['font.family'] = 'Lora'

    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 6))
    else:
        fig = ax.figure

    # Styling to improve readability
    wedgeprops = {'linewidth': 0.5, 'edgecolor': 'white'}
    textprops = {'fontsize': 9}
    if lora_ok:
        textprops['fontfamily'] = 'Lora'

    # Hide very small autopct values to avoid collisions
    def _autopct(pct):
        return ('%1.1f%%' % pct) if pct > (combine_threshold * 100) else ''

    # Determine counterclockwise boolean from direction
    ccw = False if direction == 'clockwise' else True
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=None,  # label via legend to avoid overlap
        autopct=_autopct,
        startangle=140,
        counterclock=False if direction == 'clockwise' else True,
        pctdistance=0.65,
        labeldistance=1.05,
        wedgeprops=wedgeprops,
        textprops=textprops,
    )

    # Use an external legend for labels to avoid overlap on the pie
    leg = ax.legend(wedges, labels, title=title, loc='center left', bbox_to_anchor=(1, 0, 0.5, 1))
    if lora_ok:
        try:
            leg.set_title(title)
            for text in leg.get_texts():
                text.set_fontfamily('Lora')
        except Exception:
            pass
    ax.set_title(title)
    ax.axis('equal')  # keep pie circular
    return fig, ax


def generate_pie_charts(asset_values: Dict[str, float], category_distribution: Dict[str, float], detailed: bool = False):
    """
    Create side-by-side pie charts for assets and categories.
    This function shows the charts; for testing you can call `plot_pie`.
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    # If detailed is True, do not combine small asset slices (show all individually)
    if detailed:
        plot_pie(asset_values, "Asset Distribution", ax=axes[0], combine_threshold=0)
    else:
        plot_pie(asset_values, "Asset Distribution", ax=axes[0])
    plot_pie(category_distribution, "Category Distribution", ax=axes[1])
    plt.tight_layout()
    # Only call plt.show() when using an interactive backend. For headless/backends like 'Agg'
    # save the figure to a PNG so users running on servers still get the output.
    try:
        import matplotlib as mpl
        backend = mpl.get_backend().lower()
    except Exception:
        backend = ''

    if backend.startswith('agg') or backend in ('template', ''):
        # Ensure results directory exists at repo root
        import os
        from datetime import date

        results_dir = os.path.join(os.getcwd(), 'results')
        os.makedirs(results_dir, exist_ok=True)

        filename = date.today().strftime('Portfolio-%Y-%m-%d.png')
        out_path = os.path.join(results_dir, filename)
        # Save a high-resolution PNG (300 DPI) for crisp viewing/printing
        try:
            fig.savefig(out_path, dpi=300, bbox_inches='tight')
            # concise hip message
            print(f'Saved ➜ {out_path}')
        except Exception:
            # Fallback to a simple save if high-res fails
            fig.savefig(out_path)
            print(f'Saved ➜ {out_path} (fallback)')
    else:
        plt.show()