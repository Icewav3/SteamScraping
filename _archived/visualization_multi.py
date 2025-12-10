import marimo as mo

__generated_with = "0.18.3"
app = mo.App()


@app.cell
def _():
    # Local imports for notebook compatibility and to keep cells self-contained
    import pandas as pd
    import seaborn as sns
    import matplotlib.pyplot as plt
    return pd, plt, sns


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Create combined dataframe from Data/* snapshots
    """)
    return


@app.cell
def _(pd):
    import os
    import glob

    files = glob.glob(os.path.join("Data", "*/steamspy_data.jsonl"))
    if not files:
        mo.md("No data files found under Data/")
        return (pd.DataFrame(),)

    dfs = []
    for f in sorted(files):
        date = os.path.basename(os.path.dirname(f))
        df = pd.read_json(f, lines=True)
        df["snapshot_date"] = date
        dfs.append(df)

    if dfs:
        full = pd.concat(dfs, ignore_index=True)
    else:
        full = pd.DataFrame()
    return (full,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Unique apps per snapshot
    """)
    return


@app.cell
def _(df, plt, sns):
    if df.empty:
        mo.md("No data to visualize")
        return
    counts = df.groupby("snapshot_date").appid.nunique().reset_index()
    counts.columns = ["snapshot_date", "unique_apps"]
    counts["snapshot_date"] = pd.to_datetime(counts["snapshot_date"])  # type: ignore
    plt.figure(figsize=(12, 5))
    sns.lineplot(data=counts.sort_values("snapshot_date"), x="snapshot_date", y="unique_apps", marker="o")
    plt.title("Unique Apps per Snapshot")
    plt.xlabel("Date")
    plt.ylabel("Unique Apps")
    plt.tight_layout()
    plt.show()
    return (counts,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Top Genres across snapshots
    """)
    return


@app.cell
def _(df, pd, plt, sns):
    if df.empty:
        return
    df = df[df["genre"].notnull() & (df["genre"] != "")]
    df["genre_list"] = df["genre"].str.split(",")
    df["genre_list"] = df["genre_list"].apply(lambda x: [g.strip() for g in x])
    exploded = df.explode("genre_list")
    genre_counts = exploded["genre_list"].value_counts().reset_index()
    genre_counts.columns = ["genre", "count"]
    plt.figure(figsize=(10, 8))
    sns.barplot(data=genre_counts.head(20), x="count", y="genre", palette="viridis")
    plt.title("Top Genres")
    plt.tight_layout()
    plt.show()
    return (genre_counts,)


@app.cell
def _():
    import marimo as mo
    return (mo,)


if __name__ == "__main__":
    app.run()
import marimo as mo

__generated_with = "0.18.3"
app = mo.App()


@app.cell
def _():
    import pandas as pd
    import seaborn as sns
    import matplotlib.pyplot as plt
    return pd, plt, sns


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Create combined dataframe from Data/* snapshots
    """)
    return


@app.cell
def _(pd):
    import os, glob
    files = glob.glob(os.path.join("Data", "*/steamspy_data.jsonl"))
    if not files:
        mo.md("No data files found under Data/")
        return (pd.DataFrame(),)
    dfs = []
    for f in sorted(files):
        date = os.path.basename(os.path.dirname(f))
        df = pd.read_json(f, lines=True)
        df["snapshot_date"] = date
        dfs.append(df)
    if dfs:
        full = pd.concat(dfs, ignore_index=True)
    else:
        full = pd.DataFrame()
    return (full,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Unique apps per snapshot
    """)
    return


@app.cell
def _(df, plt, sns):
    if df.empty:
        mo.md("No data to visualize")
        return
    counts = df.groupby("snapshot_date").appid.nunique().reset_index()
    counts.columns = ["snapshot_date", "unique_apps"]
    counts["snapshot_date"] = pd.to_datetime(counts["snapshot_date"])  # type: ignore
    plt.figure(figsize=(12, 5))
    sns.lineplot(data=counts.sort_values("snapshot_date"), x="snapshot_date", y="unique_apps", marker="o")
    plt.title("Unique Apps per Snapshot")
    plt.xlabel("Date")
    plt.ylabel("Unique Apps")
    plt.tight_layout()
    plt.show()
    return (counts,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Top Genres across snapshots
    """)
    return


@app.cell
def _(df, pd, plt, sns):
    if df.empty:
        return
    df = df[df["genre"].notnull() & (df["genre"] != "")]
    df["genre_list"] = df["genre"].str.split(",")
    df["genre_list"] = df["genre_list"].apply(lambda x: [g.strip() for g in x])
    exploded = df.explode("genre_list")
    genre_counts = exploded["genre_list"].value_counts().reset_index()
    genre_counts.columns = ["genre", "count"]
    plt.figure(figsize=(10, 8))
    sns.barplot(data=genre_counts.head(20), x="count", y="genre", palette="viridis")
    plt.title("Top Genres")
    plt.tight_layout()
    plt.show()
    return (genre_counts,)


@app.cell
def _():
    return (mo,)


if __name__ == '__main__':
    app.run()
import marimo as mo
import pandas as pd
import os
import glob
import matplotlib.pyplot as plt
import seaborn as sns

app = mo.App()


@app.cell
def _():
    data_dir = "Data"
    # Placeholder: return empty frame until we add file loading logic back safely
    return (pd.DataFrame(),)


@app.cell
def _(df):
    """Basic dataset counts and a timeseries of number of apps recorded per day."""
    if df.empty:
        mo.md("No data to visualize")
        return

    counts = df.groupby("snapshot_date").appid.nunique().reset_index()
    counts.columns = ["snapshot_date", "unique_apps"]
    counts["snapshot_date"] = pd.to_datetime(counts["snapshot_date"])

    plt.figure(figsize=(12, 5))
    sns.lineplot(data=counts.sort_values("snapshot_date"), x="snapshot_date", y="unique_apps", marker="o")
    plt.title("Unique Apps per Snapshot")
    plt.xlabel("Date")
    plt.ylabel("Unique Apps")
    plt.tight_layout()
    plt.show()
    return (counts,)


@app.cell
def _(df):
    """Top genres across all snapshots as a bar chart (exploded genre lists)."""
    if df.empty:
        return
    df = df[df["genre"].notnull() & (df["genre"] != "")]
    df["genre_list"] = df["genre"].str.split(",")
    df["genre_list"] = df["genre_list"].apply(lambda x: [g.strip() for g in x])
    exploded = df.explode("genre_list")
    genre_counts = exploded["genre_list"].value_counts().reset_index()
    genre_counts.columns = ["genre", "count"]
    plt.figure(figsize=(10, 8))
    sns.barplot(data=genre_counts.head(20), x="count", y="genre", palette="viridis")
    plt.title("Top Genres")
    plt.tight_layout()
    plt.show()
    return (genre_counts,)


@app.cell
def _():
    return (mo,)


if __name__ == "__main__":
    app.run()
