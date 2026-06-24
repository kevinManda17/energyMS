import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("forecasting", "0004_imported_model_forecast"),
        ("fuzzy_engine", "0003_advanced_decision_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="decision",
            name="forecast",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="decisions",
                to="forecasting.forecast",
            ),
        ),
    ]

