"""
Management command: register pre-trained ML models from AI2 into the EMS database.

This command reads the best_model_info.json files from the AI2 training results
and creates ImportedModel records so the forecasting service can use them.

Usage:
    python manage.py register_ml_models
    python manage.py register_ml_models --ai2-path /path/to/AI2
    python manage.py register_ml_models --deactivate-old   (deactivate existing models first)

Expected AI2 directory structure:
    AI2/
    ├── consumption_eda_train/result_training/models/
    │   ├── GRU/model.keras + preprocessing.joblib
    │   └── best_model/best_model_info.json
    └── pv_dataset/result_training/models/
        ├── LSTM/model.keras + preprocessing.joblib
        └── best_model/best_model_info.json
"""

import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.forecasting.models import ImportedModel

# Default path to the AI2 folder (relative to the project root or absolute)
DEFAULT_AI2_PATH = os.getenv(
    "AI2_PATH",
    str(Path(__file__).resolve().parents[7] / "AI2"),
)

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
    {
        "target": "consumption",
        "subdir": "consumption_eda_train",
        "name_prefix": "Consommation",
    },
    {
        "target": "production",
        "subdir": "pv_dataset",
        "name_prefix": "Production PV",
    },
]


def _load_best_model_info(result_dir: Path) -> dict:
    info_path = result_dir / "models" / "best_model" / "best_model_info.json"
    if not info_path.exists():
        raise FileNotFoundError(f"best_model_info.json not found at {info_path}")
    with open(info_path, encoding="utf-8") as f:
        return json.load(f)


def _load_metrics(model_dir: Path, model_name: str) -> dict:
    metrics_path = model_dir / model_name / "metrics.json"
    if not metrics_path.exists():
        return {}
    with open(metrics_path, encoding="utf-8") as f:
        data = json.load(f)
    # metrics.json can be a flat dict or nested under "metrics" key
    if isinstance(data, dict) and "metrics" in data and isinstance(data["metrics"], dict):
        return data["metrics"]
    return data


def _get_feature_columns(preprocessing_path: str) -> list[str]:
    if not preprocessing_path or not Path(preprocessing_path).exists():
        return []
    try:
        import joblib
        prep = joblib.load(preprocessing_path)
        return list(prep.get("feature_columns", []))
    except Exception:
        return []


def _get_sequence_length(preprocessing_path: str) -> int:
    if not preprocessing_path or not Path(preprocessing_path).exists():
        return 1
    try:
        import joblib
        prep = joblib.load(preprocessing_path)
        return int(prep.get("sequence_length", 1))
    except Exception:
        return 1


class Command(BaseCommand):
    help = "Register AI2 pre-trained models into the EMS ImportedModel table."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ai2-path",
            type=str,
            default=DEFAULT_AI2_PATH,
            help=f"Absolute path to the AI2 folder (default: {DEFAULT_AI2_PATH})",
        )
        parser.add_argument(
            "--deactivate-old",
            action="store_true",
            default=False,
            help="Deactivate existing active models for the same target before registering.",
        )
        parser.add_argument(
            "--model",
            type=str,
            default=None,
            help="Register only this model name (e.g. GRU, LSTM, RF). Default: best model.",
        )

    def handle(self, *args, **options):
        ai2_root = Path(options["ai2_path"])
        if not ai2_root.exists():
            raise CommandError(
                f"AI2 directory not found: {ai2_root}\n"
                "Set AI2_PATH in your .env or pass --ai2-path."
            )

        self.stdout.write(f"Using AI2 directory: {ai2_root}")

        for config in CONFIGS:
            target = config["target"]
            result_dir = ai2_root / config["subdir"] / "result_training"

            if not result_dir.exists():
                self.stderr.write(f"  [{target}] result_training not found: {result_dir}")
                continue

            try:
                info = _load_best_model_info(result_dir)
            except FileNotFoundError as exc:
                self.stderr.write(f"  [{target}] {exc}")
                continue

            if info.get("status") != "ok":
                self.stderr.write(f"  [{target}] No valid best model in best_model_info.json")
                continue

            model_name = options["model"] or info["best_model"]
            ems_model_type = MODEL_TYPE_MAP.get(model_name, "sklearn")

            # Locate model file
            model_dir = result_dir / "models" / model_name
            if not model_dir.exists():
                self.stderr.write(f"  [{target}] Model directory not found: {model_dir}")
                continue

            # Keras model uses .keras; sklearn uses .joblib
            if ems_model_type in {"keras_gru", "keras_lstm", "keras_cnn_lstm", "keras_lstm_att"}:
                model_file = model_dir / "model.keras"
            else:
                model_file = model_dir / "model.joblib"

            if not model_file.exists():
                self.stderr.write(f"  [{target}] Model file not found: {model_file}")
                continue

            preprocessing_file = model_dir / "preprocessing.joblib"
            preprocessing_path = str(preprocessing_file) if preprocessing_file.exists() else ""

            metrics = _load_metrics(result_dir, model_name)
            feature_columns = _get_feature_columns(preprocessing_path)
            sequence_length = _get_sequence_length(preprocessing_path)

            if options["deactivate_old"]:
                deactivated = ImportedModel.objects.filter(
                    target=target, is_active=True
                ).update(is_active=False)
                if deactivated:
                    self.stdout.write(f"  [{target}] Deactivated {deactivated} existing model(s).")

            record, created = ImportedModel.objects.update_or_create(
                target=target,
                model_type=ems_model_type,
                file_path=str(model_file),
                defaults={
                    "name": f"{config['name_prefix']} — {model_name}",
                    "version": metrics.get("model", model_name),
                    "preprocessing_path": preprocessing_path,
                    "sequence_length": sequence_length,
                    "feature_columns": feature_columns,
                    "input_schema": {
                        "features": feature_columns,
                        "sequence_length": sequence_length,
                    },
                    "metrics": {
                        k: metrics.get(k)
                        for k in ("MAE", "RMSE", "R2", "sMAPE", "model_type",
                                  "train_rows", "test_rows")
                    },
                    "is_active": True,
                },
            )

            action = "Created" if created else "Updated"
            r2_str = f"{float(metrics['R2']):.3f}" if metrics.get("R2") is not None else "N/A"
            rmse_str = f"{float(metrics['RMSE']):.4f}" if metrics.get("RMSE") is not None else "N/A"
            self.stdout.write(
                self.style.SUCCESS(
                    f"  [{target}] {action} ImportedModel #{record.pk}: "
                    f"{model_name} ({ems_model_type}) R²={r2_str} RMSE={rmse_str}"
                )
            )
            self.stdout.write(f"    model file:       {model_file}")
            self.stdout.write(f"    preprocessing:    {preprocessing_path or '(none)'}")
            self.stdout.write(f"    sequence_length:  {sequence_length}")
            self.stdout.write(f"    feature_columns:  {len(feature_columns)} features")

        self.stdout.write(self.style.SUCCESS("\nDone. Run: python manage.py run_forecast --help"))
