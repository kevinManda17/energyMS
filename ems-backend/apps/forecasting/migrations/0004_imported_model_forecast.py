import django.db.models.deletion
from django.db import migrations, models


def migrate_model_names(apps, schema_editor):
    ImportedModel = apps.get_model("forecasting", "ImportedModel")
    for model in ImportedModel.objects.all():
        if not getattr(model, "name", ""):
            model.name = f"{model.model_type} {model.target}"
            model.save(update_fields=["name"])


class Migration(migrations.Migration):

    dependencies = [
        ("forecasting", "0003_hourly_profile_forecast"),
        ("houses", "0003_energy_assets_migration"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ForecastModel",
            new_name="ImportedModel",
        ),
        migrations.RenameModel(
            old_name="Prediction",
            new_name="Forecast",
        ),
        migrations.RenameField(
            model_name="importedmodel",
            old_name="algorithm",
            new_name="model_type",
        ),
        migrations.RenameField(
            model_name="importedmodel",
            old_name="created_at",
            new_name="imported_at",
        ),
        migrations.RenameField(
            model_name="forecast",
            old_name="value",
            new_name="forecast_value",
        ),
        migrations.AddField(
            model_name="importedmodel",
            name="name",
            field=models.CharField(default="", max_length=120),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="importedmodel",
            name="file",
            field=models.FileField(blank=True, null=True, upload_to="models/"),
        ),
        migrations.AddField(
            model_name="importedmodel",
            name="version",
            field=models.CharField(default="v1", max_length=50),
        ),
        migrations.AddField(
            model_name="importedmodel",
            name="input_schema",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="importedmodel",
            name="metrics",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="forecast",
            name="horizon_minutes",
            field=models.PositiveIntegerField(default=60),
        ),
        migrations.AddField(
            model_name="forecast",
            name="input_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name="importedmodel",
            name="file_path",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="importedmodel",
            name="model_type",
            field=models.CharField(default="profile", max_length=50),
        ),
        migrations.AlterField(
            model_name="importedmodel",
            name="target",
            field=models.CharField(
                choices=[
                    ("production", "Production"),
                    ("consumption", "Consommation"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="forecast",
            name="house",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="forecasts",
                to="houses.house",
            ),
        ),
        migrations.AlterField(
            model_name="forecast",
            name="model",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="forecasts",
                to="forecasting.importedmodel",
            ),
        ),
        migrations.AlterModelOptions(
            name="forecast",
            options={"ordering": ["horizon"]},
        ),
        migrations.AlterModelOptions(
            name="importedmodel",
            options={"ordering": ["-imported_at"]},
        ),
        migrations.RunPython(migrate_model_names, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="importedmodel",
            name="mae",
        ),
        migrations.RemoveField(
            model_name="importedmodel",
            name="rmse",
        ),
        migrations.RemoveField(
            model_name="importedmodel",
            name="r2",
        ),
        migrations.RemoveField(
            model_name="importedmodel",
            name="n_samples",
        ),
        migrations.AddIndex(
            model_name="importedmodel",
            index=models.Index(
                fields=["target", "is_active"],
                name="forecasting_target_700456_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="importedmodel",
            index=models.Index(fields=["model_type"], name="forecasting_model_t_9ea059_idx"),
        ),
        migrations.AddIndex(
            model_name="forecast",
            index=models.Index(fields=["house", "created_at"], name="forecasting_house_i_c79370_idx"),
        ),
        migrations.AddIndex(
            model_name="forecast",
            index=models.Index(
                fields=["house", "target", "horizon"],
                name="forecasting_house_i_e747a5_idx",
            ),
        ),
    ]

