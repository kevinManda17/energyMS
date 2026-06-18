from django.db import migrations, models


def migrate_forecast_models(apps, schema_editor):
    ForecastModel = apps.get_model("forecasting", "ForecastModel")
    for model in ForecastModel.objects.all():
        model.algorithm = "HourlyProfileForecast"
        model.file_path = f"internal://hourlyprofileforecast/{model.target}"
        model.save(update_fields=["algorithm", "file_path"])


class Migration(migrations.Migration):
    dependencies = [
        ("forecasting", "0002_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="forecastmodel",
            name="algorithm",
            field=models.CharField(default="HourlyProfileForecast", max_length=40),
        ),
        migrations.RunPython(migrate_forecast_models, migrations.RunPython.noop),
    ]
