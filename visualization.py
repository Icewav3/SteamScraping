import marimo

__generated_with = "0.18.3"
app = marimo.App()


@app.cell
def _():
    import pandas as pd
    import seaborn as sns
    import matplotlib.pyplot as plt
    return pd, plt, sns


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Create dataframe
    """)
    return


@app.cell
def _(pd):
    df = pd.read_json("Data/steamspy_data.jsonl", lines=True)
    df.head()
    return (df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Quick and dirty cleaning
    """)
    return


@app.cell
def _(df):
    df_1 = df[df['genre'].notnull() & (df['genre'] != '')]
    df_1['genre_list'] = df_1['genre'].str.split(',')
    # make genres into list
    df_1['genre_list'] = df_1['genre_list'].apply(lambda x: [g.strip() for g in x])
    # remove trailing whitespace & explode
    genre_df = df_1.explode('genre_list')
    return df_1, genre_df


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Next, we count the number of times a genre appears.

    > **NOTE:** I am currently doing this under the assumption that don't have games with two of the same tag for simplicity.
    """)
    return


@app.cell
def _(genre_df):
    genre_counts = genre_df['genre_list'].value_counts().reset_index()
    genre_counts.columns = ['genre', 'count']
    return (genre_counts,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Visualization time!
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Top most common genres
    """)
    return


@app.cell
def _(genre_counts, plt, sns):
    GENRENUMBER = 12

    plt.figure(figsize=(12, GENRENUMBER * 0.25))
    sns.barplot(data=genre_counts.head(GENRENUMBER), x='count', y='genre', palette='viridis')
    plt.title("Top 20 Most Common Steam Genres")
    plt.xlabel("Number of Games")
    plt.ylabel("Genre")
    plt.tight_layout()
    plt.show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Now for the tags
    """)
    return


@app.cell
def _(df_1, pd):
    df_2 = df_1[df_1['tags'].notnull()]
    tag_rows = []
    for _, row in df_2.iterrows():
        appid = row['appid']
        tags = row['tags']
        if isinstance(tags, dict):
            for tag in tags.keys():
                tag_rows.append({'appid': appid, 'tag': tag})
    tags_df = pd.DataFrame(tag_rows)
    tags_df.head()
    return (tags_df,)


@app.cell
def _(plt, sns, tags_df):
    TAGNUMBER = 250

    plt.figure(figsize=(12, TAGNUMBER * 0.25))
    tag_counts = tags_df['tag'].value_counts().reset_index()
    tag_counts.columns = ['tag', 'count']
    sns.barplot(data=tag_counts.head(TAGNUMBER), x='count', y='tag', palette='viridis' )
    plt.title("Most Common Steam Tags")
    plt.xlabel("Number of Games")
    plt.ylabel("Tag")
    plt.tight_layout()
    return


@app.cell
def _():
    import marimo as mo
    return (mo,)


if __name__ == "__main__":
    app.run()
