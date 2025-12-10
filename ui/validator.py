import marimo

__generated_with = "0.18.3"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Data Validation
    
    Check the integrity and continuity of scraped data.
    """)
    return


@app.cell
def _():
    import marimo as mo
    import os
    from datetime import datetime, timedelta
    from src.validation import DataValidator
    return mo, os, datetime, timedelta, DataValidator


@app.cell
def _(mo):
    mo.md("## Validation Settings")
    return


@app.cell
def _(mo):
    data_dir = mo.ui.text(value="Data", label="Data directory")
    start_date = mo.ui.input_text(placeholder="2025-11-01", label="Start date (YYYY-MM-DD)")
    end_date = mo.ui.input_text(placeholder="2025-11-30", label="End date (YYYY-MM-DD)")
    max_folders = mo.ui.slider(1, 100, value=30, label="Max folders to check")
    
    return data_dir, start_date, end_date, max_folders


@app.cell
def _(mo):
    mo.md("## Run Validation")
    return


@app.cell
def _(mo, data_dir, start_date, end_date, max_folders):
    validate_button = mo.ui.run_button(label="✅ Validate Data", kind="success")
    return validate_button


@app.cell
def _(validate_button, mo, os, datetime, timedelta, DataValidator, data_dir, start_date, end_date, max_folders):
    if validate_button.clicked:
        # Parse dates
        try:
            start = datetime.fromisoformat(start_date.value).date() if start_date.value else datetime.now().date()
            end = datetime.fromisoformat(end_date.value).date() if end_date.value else datetime.now().date()
        except Exception as e:
            mo.md(f"❌ Invalid date format: {e}")
        else:
            if end < start:
                mo.md("❌ End date must be on or after start date")
            else:
                results = []
                date = start
                checked = 0
                
                with mo.status.spinner(title="Validating folders..."):
                    while date <= end and checked < max_folders.value:
                        folder = os.path.join(data_dir.value, date.isoformat())
                        if os.path.isdir(folder):
                            validator = DataValidator(folder)
                            result = validator.validate()
                            results.append((date.isoformat(), result))
                            checked += 1
                        date = date + timedelta(days=1)
                
                # Display results
                valid_count = sum(1 for _, r in results if r.is_valid)
                invalid_count = len(results) - valid_count
                
                mo.md(f"""
                ## Validation Results
                
                - ✅ Valid: {valid_count}
                - ❌ Invalid: {invalid_count}
                """)
                
                for date_str, result in results:
                    if result.is_valid:
                        status = "✅"
                    else:
                        status = "❌"
                    
                    mo.md(f"{status} **{date_str}**")
                    if result.errors:
                        for err in result.errors:
                            mo.md(f"  - {err}")
    return


if __name__ == "__main__":
    app.run()
