"""Lightweight dataset validation / cleaning helpers."""
import pandas as pd

# Minimal expected columns per dataset kind.
EXPECTED_COLUMNS = {
    "production": {"timestamp", "production"},
    "consumption": {"timestamp", "consumption"},
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
    expected = EXPECTED_COLUMNS.get(kind, set())
    missing = expected - set(columns)
    if missing:
        return False, f"Colonnes manquantes: {sorted(missing)}", df, columns

    # Basic cleaning: drop fully empty rows, forward-fill, drop duplicates.
    cleaned = df.dropna(how="all").drop_duplicates()
    if "timestamp" in cleaned.columns:
        cleaned["timestamp"] = pd.to_datetime(
            cleaned["timestamp"], errors="coerce"
        )
        cleaned = cleaned.dropna(subset=["timestamp"]).sort_values("timestamp")

    return True, "Dataset valide.", cleaned, columns
