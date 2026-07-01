"""
Management command: register models from ml_models/ into the EMS database.

Reads the flat structure:
    ml_models/
    ├── consumption/
    │   ├── model.keras          (or model.joblib for sklearn)
    │   ├── preprocessing.joblib
    │   └── metrics.json
    └── production/
        ├── model.keras
        ├── preprocessing.joblib
        └── metrics.json

Usage:
    python manage.py register_models
    python manage.py register_models --models-dir /path/to/ml_models
"""

import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.forecasting.models import ImportedModel

BASE_DIR = Path(__file__).resolve().parents[4]
DEFAULT_MODELS_DIR = str(BASE_DIR / "ml_models")

MODEL_TYPE_MAP = {
    "GRU": "keras_gru",
    "LSTM": "keras_lstm",
    "LSTM-CNN": "keras_cnn_lstm",
    "LSTM-ATTENTION": "keras_lstm_att",
    "RF": "sklearn",
    "GB": "sklearn",
    "DT": "sklearn",
}

CONFIGS = [
    {"target": "consumption", "label": "Consommation"},
    {"target": "production", "label": "Production PV"},
]


def _load_preprocessing_meta(preprocessing_path: str) -> tuple[list, int]:
    """Return (feature_columns, sequence_length) from preprocessing.joblib."""
    if not preprocessing_path or not Path(preprocessing_path).exists():
        return [], 1
    try:
        import joblib
        prep = joblib.load(preprocessing_path)
        cols = list(prep.get("feature_columns", []))
        seq = int(prep.get("sequence_length", 1))
        return cols, seq
    except Exception:
        return [], 1


class Command(BaseCommand):
    help = "Register ML models from ml_models/ into the EMS ImportedModel table."

    def add_arguments(self, parser):
        parser.add_argument(
            "--models-dir",
            type=str,
            default=DEFAULT_MODELS_DIR,
            help=f"Path to the ml_models directory (default: {DEFAULT_MODELS_DIR})",
        )
        parser.add_argument(
            "--deactivate-old",
            action="store_true",
            default=False,
            help="Deactivate any existing active models for the same target first.",
        )

    def handle(self, *args, **options):
        models_dir = Path(options["models_dir"])
        if not models_dir.exists():
            raise CommandError(f"ml_models directory not found: {models_dir}")

        self.stdout.write(f"Reading models from: {models_dir}\n")

        for cfg in CONFIGS:
            target = cfg["target"]
            folder = models_dir / target

            if not folder.exists():
                self.stderr.write(f"  [{target}] Folder not found: {folder}")
                continue

            # Load metrics.json to identify model name and type
            metrics_path = folder / "metrics.json"
            if not metrics_path.exists():
                self.stderr.write(f"  [{target}] metrics.json not found in {folder}")
                continue

            with open(metrics_path, encoding="utf-8") as f:
                metrics = json.load(f)

            model_name = metrics.get("model", "Unknown")
            ems_model_type = MODEL_TYPE_MAP.get(model_name, "sklearn")

            # Locate model file (Keras takes priority over sklearn)
            keras_file = folder / "model.keras"
            sklearn_file = folder / "model.joblib"
            preprocessing_file = folder / "preprocessing.joblib"

            if ems_model_type in {"keras_gru", "keras_lstm", "keras_cnn_lstm", "keras_lstm_att"}:
                model_file = keras_file
            else:
                model_file = sklearn_file

            if not model_file.exists():
                self.stderr.write(f"  [{target}] Model file not found: {model_file}")
                continue

            preprocessing_path = str(preprocessing_file) if preprocessing_file.exists() else ""
            feature_columns, sequence_length = _load_preprocessing_meta(preprocessing_path)

            if options["deactivate_old"]:
                deactivated = (
                    ImportedModel.objects.filter(target=target, is_active=True)
                    .exclude(model_type="profile")
                    .update(is_active=False)
                )
                if deactivated:
                    self.stdout.write(f"  [{target}] Deactivated {deactivated} existing model(s).")

            r2 = metrics.get("R2")
            rmse = metrics.get("RMSE")
            r2_str = f"{float(r2):.3f}" if r2 is not None else "N/A"
            rmse_str = f"{float(rmse):.4f}" if rmse is not None else "N/A"

            record, created = ImportedModel.objects.update_or_create(
                target=target,
                model_type=ems_model_type,
                defaults={
                    "name": f"{cfg['label']} — {model_name}",
                    "file_path": str(model_file),
                    "preprocessing_path": preprocessing_path,
                    "sequence_length": sequence_length,
                    "feature_columns": feature_columns,
                    "version": model_name,
                    "input_schema": {
                        "features": feature_columns,
                        "sequence_length": sequence_length,
                    },
                    "metrics": {
                        k: metrics.get(k)
                        for k in ("MAE", "RMSE", "R2", "sMAPE", "model_type",
                                  "train_rows", "test_rows", "features_used",
                                  "feature_columns")
                        if metrics.get(k) is not None
                    },
                    "is_active": True,
                },
            )

            action = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"  [{target}] {action} #{record.pk}: "
                    f"{model_name} ({ems_model_type}) "
                    f"R²={r2_str} RMSE={rmse_str}"
                )
            )
            self.stdout.write(f"    file:            {model_file}")
            self.stdout.write(f"    preprocessing:   {preprocessing_path or '(none)'}")
            self.stdout.write(f"    sequence_length: {sequence_length}")
            self.stdout.write(f"    features:        {len(feature_columns)}")

        self.stdout.write(self.style.SUCCESS(
            "\nModels registered. Test with:\n"
            "  python manage.py run_forecast --house-id 1"
        ))
