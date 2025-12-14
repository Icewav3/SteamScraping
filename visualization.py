# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.18.3",
#     "pandas>=2.2.0",
#     "matplotlib>=3.8.0",
#     "seaborn>=0.13.0",
#     "numpy>=1.26.0",
# ]
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 🎮 Game Industry Market Analysis Dashboard

    > **Interactive exploration of gaming market trends from SteamSpy data**

    This dashboard provides comprehensive analysis of game market data including genre distributions,
    tag frequencies, temporal trends, and comparative insights across multiple scraping sessions.
    """)
    return


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np
    from pathlib import Path
    from datetime import datetime
    import json

    # Set style for professional visualizations
    sns.set_theme(style="whitegrid", palette="viridis")
    plt.rcParams['figure.figsize'] = (12, 6)
    plt.rcParams['figure.dpi'] = 100

    return Path, mo, pd, plt, sns


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 📂 Data Loading
    """)
    return


@app.cell
def _(Path, mo, pd):
    def load_available_dates():
        """Scan Data directory for available scrape dates."""
        data_dir = Path("Data")
        if not data_dir.exists():
            return []

        dates = []
        for folder in data_dir.iterdir():
            if folder.is_dir() and (folder / "steamspy_data.jsonl").exists():
                dates.append(folder.name)
        return sorted(dates, reverse=True)


    def load_dataset(date_folder):
        """Load dataset from specific date folder."""
        filepath = Path("Data") / date_folder / "steamspy_data.jsonl"

        if not filepath.exists():
            return None, None

        # Load main data
        df = pd.read_json(filepath, lines=True)

        # Load metadata if available
        metadata_path = filepath.parent / "metadata.json"
        metadata = None
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = pd.json_normalize(pd.read_json(f, typ='series'))

        return df, metadata


    available_dates = load_available_dates()

    if not available_dates:
        mo.md("⚠️ **No data found!** Please run the scraper first (`main.py`)").callout(kind="warn")
        mo.stop()

    mo.md(f"✅ Found **{len(available_dates)}** scraping session(s)").callout(kind="success")
    return available_dates, load_dataset


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## ⚙️ Dashboard Controls
    """)
    return


@app.cell
def _(available_dates, mo):
    # Date selector
    date_selector = mo.ui.dropdown(
        options=available_dates,
        value=available_dates[0] if available_dates else None,
        label="📅 Select Scraping Date:"
    )

    # Multi-date selector for comparisons
    multi_date_selector = mo.ui.multiselect(
        options=available_dates,
        value=[available_dates[0]] if len(available_dates) == 1 else available_dates[:2],
        label="📊 Compare Multiple Dates:"
    )

    # Top N selector for charts
    top_n_slider = mo.ui.slider(
        start=5,
        stop=50,
        step=5,
        value=15,
        label="🔢 Number of Items to Display:"
    )

    # Chart type selector
    chart_type = mo.ui.radio(
        options=["Bar Chart", "Pie Chart"],
        value="Bar Chart",
        label="📈 Visualization Type:"
    )

    mo.hstack([date_selector, top_n_slider], justify="start", gap=2)
    return chart_type, date_selector, multi_date_selector, top_n_slider


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 📊 Dataset Overview
    """)
    return


@app.cell
def _(date_selector, load_dataset, mo):
    # Load selected dataset
    df, metadata = load_dataset(date_selector.value)

    if df is None:
        mo.md("❌ Failed to load dataset").callout(kind="danger")
        mo.stop()

    # Display key metrics
    total_apps = len(df)
    apps_with_genre = df['genre'].notnull().sum()
    apps_with_tags = df['tags'].notnull().sum()
    unique_developers = df['developer'].nunique() if 'developer' in df.columns else 0

    metric_cards = mo.hstack([
        mo.md(f"""
        ### 🎮 Total Games
        **{total_apps:,}**
        """).center().callout(kind="info"),

        mo.md(f"""
        ### 🏷️ With Genres
        **{apps_with_genre:,}**
        ({apps_with_genre/total_apps*100:.1f}%)
        """).center().callout(kind="success"),

        mo.md(f"""
        ### 🔖 With Tags
        **{apps_with_tags:,}**
        ({apps_with_tags/total_apps*100:.1f}%)
        """).center().callout(kind="success"),

        mo.md(f"""
        ### 👥 Developers
        **{unique_developers:,}**
        """).center().callout(kind="neutral"),
    ], justify="space-between", gap=2)

    metric_cards
    return (df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 🎨 Genre Analysis
    """)
    return


@app.cell
def _(df):
    # Process genre data
    df_genres = df[df['genre'].notnull() & (df['genre'] != '')].copy()
    df_genres['genre_list'] = df_genres['genre'].str.split(',').apply(
        lambda x: [g.strip() for g in x] if isinstance(x, list) else []
    )
    genre_exploded = df_genres.explode('genre_list')
    genre_counts = genre_exploded['genre_list'].value_counts().reset_index()
    genre_counts.columns = ['genre', 'count']

    genre_counts
    return df_genres, genre_counts


@app.cell
def _(chart_type, genre_counts, mo, plt, sns, top_n_slider):
    # Genre visualization
    top_genres = genre_counts.head(top_n_slider.value)

    fig_genre, ax_genre = plt.subplots(figsize=(14, max(8, top_n_slider.value * 0.4)))

    if chart_type.value == "Bar Chart":
        sns.barplot(
            data=top_genres,
            y='genre',
            x='count',
            hue='genre',
            palette='viridis',
            legend=False,
            ax=ax_genre
        )
        ax_genre.set_title(f'Top {top_n_slider.value} Most Common Game Genres', 
                           fontsize=16, fontweight='bold', pad=20)
        ax_genre.set_xlabel('Number of Games', fontsize=12)
        ax_genre.set_ylabel('Genre', fontsize=12)

        # Add value labels
        for _i, (_idx, _row) in enumerate(top_genres.iterrows()):
            ax_genre.text(_row['count'], _i, f" {_row['count']:,}", 
                         va='center', fontsize=10)

    elif chart_type.value == "Pie Chart":
        colors = sns.color_palette('viridis', len(top_genres))
        wedges, texts, autotexts = ax_genre.pie(
            top_genres['count'],
            labels=top_genres['genre'],
            autopct='%1.1f%%',
            colors=colors,
            startangle=90
        )
        ax_genre.set_title(f'Genre Distribution (Top {top_n_slider.value})', 
                          fontsize=16, fontweight='bold', pad=20)

        # Improve text readability
        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(9)

    plt.tight_layout()

    _genre_description = mo.md(f"""
    ### 🎮 Genre Distribution

    Analyzing the top **{top_n_slider.value}** most common genres across all games in the dataset.
    """)

    _genre_description
    return (fig_genre,)


@app.cell
def _(fig_genre, mo):
    mo.mpl.interactive(fig_genre)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 🏷️ Tag Analysis
    """)
    return


@app.cell
def _(df, pd):
    # Process tag data
    df_tags = df[df['tags'].notnull()].copy()
    tag_rows = []

    for _, _row in df_tags.iterrows():
        appid = _row['appid']
        tags = _row['tags']
        if isinstance(tags, dict):
            for tag, votes in tags.items():
                tag_rows.append({
                    'appid': appid,
                    'tag': tag,
                    'votes': votes
                })

    tags_df = pd.DataFrame(tag_rows)
    tag_counts = tags_df.groupby('tag').agg({
        'appid': 'count',
        'votes': 'sum'
    }).reset_index()
    tag_counts.columns = ['tag', 'game_count', 'total_votes']
    tag_counts = tag_counts.sort_values('game_count', ascending=False)

    tag_counts
    return (tag_counts,)


@app.cell
def _(mo, plt, sns, tag_counts, top_n_slider):
    # Tag visualization
    top_tags = tag_counts.head(top_n_slider.value)

    fig_tags, ax_tags = plt.subplots(figsize=(14, max(8, top_n_slider.value * 0.4)))

    sns.barplot(
        data=top_tags,
        y='tag',
        x='game_count',
        hue='tag',
        palette='magma',
        legend=False,
        ax=ax_tags
    )

    ax_tags.set_title(f'Top {top_n_slider.value} Most Common Game Tags', 
                      fontsize=16, fontweight='bold', pad=20)
    ax_tags.set_xlabel('Number of Games', fontsize=12)
    ax_tags.set_ylabel('Tag', fontsize=12)

    # Add value labels
    for _i, (idx, row) in enumerate(top_tags.iterrows()):
        ax_tags.text(row['game_count'], _i, f" {row['game_count']:,}", 
                    va='center', fontsize=10)

    plt.tight_layout()

    _tag_description = mo.md(f"""
    ### 🔖 Tag Distribution

    Most frequently applied user tags across the gaming catalog.
    """)

    _tag_description
    return (fig_tags,)


@app.cell
def _(fig_tags, mo):
    mo.mpl.interactive(fig_tags)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 📈 Temporal Trends Analysis
    """)
    return


@app.cell
def _(available_dates, mo):
    # Multi-date comparison
    if len(available_dates) < 2:
        mo.md("""
        ⚠️ **Need more data for temporal analysis**

        Run the scraper on different dates to enable trend comparison.
        """).callout(kind="warn")
    else:
        mo.md(f"""
        ### 📊 Compare Market Trends Over Time

        Analyze how genre and tag popularity changes across **{len(available_dates)}** scraping sessions.
        """)
    return


@app.cell
def _(available_dates, load_dataset, multi_date_selector, pd):
    # Load multiple datasets for comparison
    if len(available_dates) >= 2 and multi_date_selector.value:
        comparison_data = {}

        for date in multi_date_selector.value:
            df_temp, _ = load_dataset(date)
            if df_temp is not None:
                # Process genres
                df_temp_genres = df_temp[df_temp['genre'].notnull() & (df_temp['genre'] != '')].copy()
                df_temp_genres['genre_list'] = df_temp_genres['genre'].str.split(',').apply(
                    lambda x: [g.strip() for g in x] if isinstance(x, list) else []
                )
                genre_temp = df_temp_genres.explode('genre_list')
                genre_temp_counts = genre_temp['genre_list'].value_counts()

                comparison_data[date] = {
                    'total_games': len(df_temp),
                    'genre_counts': genre_temp_counts
                }

        comparison_df_list = []
        for date, data in comparison_data.items():
            temp_df = data['genre_counts'].head(15).reset_index()
            temp_df.columns = ['genre', 'count']
            temp_df['date'] = date
            comparison_df_list.append(temp_df)

        if comparison_df_list:
            comparison_df = pd.concat(comparison_df_list, ignore_index=True)
        else:
            comparison_df = None
    else:
        comparison_df = None

    comparison_df
    return (comparison_df,)


@app.cell
def _(available_dates, comparison_df, mo, plt, sns):
    # Temporal comparison visualization
    if len(available_dates) >= 2 and comparison_df is not None:
        fig_temporal, ax_temporal = plt.subplots(figsize=(16, 10))

        sns.barplot(
            data=comparison_df,
            x='count',
            y='genre',
            hue='date',
            palette='Set2',
            ax=ax_temporal
        )

    ax_temporal.set_title('Genre Popularity Comparison Across Scraping Sessions', 
                         fontsize=16, fontweight='bold', pad=20)
    ax_temporal.set_xlabel('Number of Games', fontsize=12)
    ax_temporal.set_ylabel('Genre', fontsize=12)
    ax_temporal.legend(title='Scrape Date', bbox_to_anchor=(1.05, 1), loc='upper left')

    plt.tight_layout()

    mo.mpl.interactive(fig_temporal)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 🔍 Advanced Insights
    """)
    return


@app.cell
def _(mo):
    # Genre correlation analysis
    mo.md("""
    ### 🎯 Genre Co-occurrence Matrix

    Which genres frequently appear together in the same games?
    """)
    return


@app.cell
def _(df_genres, mo, plt, sns):
    # Build co-occurrence matrix
    from itertools import combinations

    cooccurrence = {}

    for genres in df_genres['genre_list'].dropna():
        if len(genres) > 1:
            for g1, g2 in combinations(sorted(genres), 2):
                pair = (g1, g2)
                cooccurrence[pair] = cooccurrence.get(pair, 0) + 1

    # Get top genre pairs
    top_pairs = sorted(cooccurrence.items(), key=lambda x: x[1], reverse=True)[:15]

    if top_pairs:
        fig_cooccur, ax_cooccur = plt.subplots(figsize=(12, 8))

        pairs_labels = [f"{p[0]} + {p[1]}" for p, _ in top_pairs]
        pairs_counts = [count for _, count in top_pairs]

        sns.barplot(
            x=pairs_counts,
            y=pairs_labels,
            hue=pairs_labels,
            palette='coolwarm',
            legend=False,
            ax=ax_cooccur
        )

        ax_cooccur.set_title('Top Genre Combinations', fontsize=16, fontweight='bold', pad=20)
        ax_cooccur.set_xlabel('Number of Games', fontsize=12)
        ax_cooccur.set_ylabel('Genre Pair', fontsize=12)

        for i, count in enumerate(pairs_counts):
            ax_cooccur.text(count, i, f" {count:,}", va='center', fontsize=10)

        plt.tight_layout()
    else:
        mo.md("No significant genre co-occurrences found.").callout(kind="neutral")

    mo.mpl.interactive(fig_cooccur)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 📋 Raw Data Explorer
    """)
    return


@app.cell
def _(mo):
    # Data table with search
    search_box = mo.ui.text(placeholder="Search games...", label="🔍 Filter:")

    search_box
    return (search_box,)


@app.cell
def _(df, mo, search_box):
    # Filter dataframe based on search
    if search_box.value:
        filtered_df = df[
            df['name'].str.contains(search_box.value, case=False, na=False) |
            df['developer'].str.contains(search_box.value, case=False, na=False)
        ]
    else:
        filtered_df = df

    # Display subset of columns
    display_columns = ['appid', 'name', 'developer', 'genre', 'positive', 'negative', 'owners']
    available_columns = [col for col in display_columns if col in filtered_df.columns]

    mo.ui.table(
        filtered_df[available_columns].head(100),
        selection=None,
        label=f"Showing {min(100, len(filtered_df))} of {len(filtered_df):,} games"
    )

    filtered_df
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---

    <div style="text-align: center; padding: 20px;">
        <p style="color: #666; font-size: 14px;">
            Built with ❤️ using <strong>Marimo</strong> | Data from <strong>SteamSpy</strong>
        </p>
    </div>
    """)
    return


if __name__ == "__main__":
    app.run()
