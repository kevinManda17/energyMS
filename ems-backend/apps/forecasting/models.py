from django.db import models

from apps.houses.models import House


class ImportedModel(models.Model):
    """Metadata for a pre-trained forecasting model imported into EMS."""

    class Target(models.TextChoices):
        PRODUCTION = "production", "Production"
        CONSUMPTION = "consumption", "Consommation"

    class ModelType(models.TextChoices):
        PROFILE = "profile", "Profil horaire (fallback)"
        SKLEARN = "sklearn", "Scikit-learn (joblib)"
        KERAS_GRU = "keras_gru", "Keras GRU"
        KERAS_LSTM = "keras_lstm", "Keras LSTM"
        KERAS_CNN_LSTM = "keras_cnn_lstm", "Keras CNN-LSTM"
        KERAS_LSTM_ATT = "keras_lstm_att", "Keras LSTM-Attention"

    name = models.CharField(max_length=120)
    target = models.CharField(max_length=20, choices=Target.choices)
    model_type = models.CharField(max_length=50, default="profile")
    file = models.FileField(upload_to="models/", blank=True, null=True)
    file_path = models.CharField(max_length=255, blank=True)
    # For Keras models: path to preprocessing.joblib (imputer + scalers)
    preprocessing_path = models.CharField(max_length=255, blank=True)
    # Sequence length for RNN models (number of past steps)
    sequence_length = models.PositiveIntegerField(default=1)
    # Ordered list of feature column names the model expects
    feature_columns = models.JSONField(default=list, blank=True)
    version = models.CharField(max_length=50, default="v1")
    input_schema = models.JSONField(default=dict, blank=True)
    metrics = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-imported_at"]
        indexes = [
            models.Index(
                fields=["target", "is_active"],
                name="forecasting_target_700456_idx",
            ),
            models.Index(fields=["model_type"], name="forecasting_model_t_9ea059_idx"),
        ]

    @property
    def resolved_path(self) -> str:
        if self.file:
            return self.file.path
        return self.file_path

    def __str__(self) -> str:
        return f"{self.name} [{self.target}/{self.model_type}]"


class Forecast(models.Model):
    """Stored forecast generated from an imported model or a profile fallback."""

    house = models.ForeignKey(
        House,
        on_delete=models.CASCADE,
        related_name="forecasts",
        null=True,
        blank=True,
    )
    model = models.ForeignKey(
        ImportedModel,
        on_delete=models.SET_NULL,
        related_name="forecasts",
        null=True,
        blank=True,
    )
    target = models.CharField(max_length=20)
    horizon = models.DateTimeField()
    horizon_minutes = models.PositiveIntegerField(default=60)
    forecast_value = models.FloatField()
    input_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["horizon"]
        indexes = [
            models.Index(fields=["house", "created_at"], name="forecasting_house_i_c79370_idx"),
            models.Index(
                fields=["house", "target", "horizon"],
                name="forecasting_house_i_e747a5_idx",
            ),
        ]

    @property
    def value(self) -> float:
        return self.forecast_value

    def __str__(self) -> str:
        return f"{self.target}={self.forecast_value} @ {self.horizon:%Y-%m-%d %H:%M}"


# Backward-compatible aliases for older imports inside the project/tests.
ForecastModel = ImportedModel
Prediction = Forecast
