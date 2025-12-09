import marimo as mo
app = mo.App()

@app.cell
def _():
    mo.md('hello')
    return ('ok',)

if __name__ == '__main__':
    app.run()
