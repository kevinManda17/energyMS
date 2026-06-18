"""Lightweight internal dataset validation / cleaning helpers."""
import pandas as pd

# Accepted columns for optional admin imports.
EXPECTED_COLUMN_SETS = {
    "production": ({"horizon", "production"}, {"timestamp", "production"}),
    "consumption": ({"horizon", "consumption"}, {"timestamp", "consumption"}),
}


def load_dataframe(file_obj) -> pd.DataFrame:
    """Read a CSV or JSON upload into a DataFrame."""
    name = getattr(file_obj, "name", "").lower()
    if name.endswith(".json"):
        return pd.read_json(file_obj)
    return pd.read_csv(file_obj)


def validate_and_clean(df: pd.DataFrame, kind: str):
    """
    Basic validation + cleaning.
    Returns (is_valid, message, cleaned_df, columns).
    """
    columns = list(df.columns)
    expected_sets = EXPECTED_COLUMN_SETS.get(kind, ())
    present = set(columns)
    if expected_sets and not any(expected <= present for expected in expected_sets):
        choices = [" + ".join(sorted(expected)) for expected in expected_sets]
        return False, f"Colonnes attendues: {' ou '.join(choices)}", df, columns

    # Basic cleaning: drop fully empty rows, forward-fill, drop duplicates.
    cleaned = df.dropna(how="all").drop_duplicates()
    time_column = "horizon" if "horizon" in cleaned.columns else "timestamp"
    if time_column in cleaned.columns:
        cleaned[time_column] = pd.to_datetime(
            cleaned[time_column], errors="coerce"
        )
        cleaned = cleaned.dropna(subset=[time_column]).sort_values(time_column)

    return True, "Import admin valide.", cleaned, columns
