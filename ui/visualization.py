import marimo

__generated_with = "0.18.3"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 📊 Visualization
    
    Analyze and visualize scraped Steam game data.
    """)
    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    return mo, pd, plt, sns


@app.cell
def _(mo):
    import os
    mo.md("## Load Data")
    
    # Find latest data folder
    data_dir = "Data"
    if os.path.isdir(data_dir):
        folders = [f for f in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, f))]
        if folders:
            latest_folder = sorted(folders)[-1]
            latest_file = os.path.join(data_dir, latest_folder, "steamspy_data.jsonl")
        else:
            latest_file = ""
    else:
        latest_file = ""
    
    return latest_file


@app.cell
def _(mo, latest_file):
    # File selection
    data_file = mo.ui.input_text(
        value=latest_file,
        label="Data file path (JSONL format)"
    )
    
    load_button = mo.ui.run_button(label="📂 Load Data", kind="info")
    
    return data_file, load_button


@app.cell
def _(load_button, data_file, pd, mo):
    df = None
    load_status = None
    
    if load_button.clicked and data_file.value:
        try:
            with mo.status.spinner(title="Loading data..."):
                df = pd.read_json(data_file.value, lines=True)
            load_status = mo.md(f"✅ **Loaded {len(df)} games** from {data_file.value}")
        except FileNotFoundError:
            load_status = mo.md(f"❌ **File not found:** {data_file.value}")
        except Exception as e:
            load_status = mo.md(f"❌ **Error loading file:** {e}")
    
    return df, load_status


@app.cell
def _(mo, df):
    if df is not None:
        mo.md(f"""
        ## Data Summary
        
        - **Columns:** {len(df.columns)}
        - **Games:** {len(df)}
        - **Genres represented:** {df['genre'].nunique() if 'genre' in df.columns else 'N/A'}
        """)
    return


@app.cell
def _(df, pd):
    # Clean data if loaded
    genre_df = None
    tags_df = None
    
    if df is not None:
        # Clean genre data
        df_clean = df[df['genre'].notnull() & (df['genre'] != '')].copy()
        df_clean['genre_list'] = df_clean['genre'].str.split(',').apply(
            lambda x: [g.strip() for g in x] if isinstance(x, list) else []
        )
        genre_df = df_clean.explode('genre_list')
        
        # Clean tag data
        df_tags = df[df['tags'].notnull()].copy()
        tag_rows = []
        for _, row in df_tags.iterrows():
            appid = row['appid']
            tags = row['tags']
            if isinstance(tags, dict):
                for tag in tags.keys():
                    tag_rows.append({'appid': appid, 'tag': tag})
        
        tags_df = pd.DataFrame(tag_rows)
    
    return genre_df, tags_df


@app.cell
def _(mo, genre_df):
    if genre_df is not None and len(genre_df) > 0:
        mo.md("## 🎮 Genre Analysis")
    return


@app.cell
def _(genre_df, plt, sns):
    if genre_df is not None and len(genre_df) > 0:
        genre_counts = genre_df['genre_list'].value_counts().head(15).reset_index()
        genre_counts.columns = ['genre', 'count']
        
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.barplot(data=genre_counts, x='count', y='genre', palette='viridis', ax=ax)
        ax.set_title("Top 15 Most Common Steam Genres")
        ax.set_xlabel("Number of Games")
        ax.set_ylabel("Genre")
        plt.tight_layout()
        plt.show()
    return


@app.cell
def _(mo, tags_df):
    if tags_df is not None and len(tags_df) > 0:
        mo.md("## 🏷️ Tag Analysis")
    return


@app.cell
def _(tags_df, plt, sns):
    if tags_df is not None and len(tags_df) > 0:
        tag_counts = tags_df['tag'].value_counts().head(20).reset_index()
        tag_counts.columns = ['tag', 'count']
        
        fig, ax = plt.subplots(figsize=(12, 8))
        sns.barplot(data=tag_counts, x='count', y='tag', palette='viridis', ax=ax)
        ax.set_title("Top 20 Most Common Steam Tags")
        ax.set_xlabel("Number of Games")
        ax.set_ylabel("Tag")
        plt.tight_layout()
        plt.show()
    return


if __name__ == "__main__":
    app.run()
