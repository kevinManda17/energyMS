import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("alerts", "0002_initial"),
        ("fuzzy_engine", "0004_decision_forecast"),
    ]

    operations = [
        migrations.AddField(
            model_name="alert",
            name="decision",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="alerts",
                to="fuzzy_engine.decision",
            ),
        ),
    ]

