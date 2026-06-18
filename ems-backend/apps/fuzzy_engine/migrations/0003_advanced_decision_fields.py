# Generated manually for the advanced fuzzy expert engine.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fuzzy_engine", "0002_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="decision",
            name="action",
            field=models.CharField(max_length=80),
        ),
        migrations.AddField(
            model_name="decision",
            name="decision_code",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="decision",
            name="decision_label",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="decision",
            name="execution_mode",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name="decision",
            name="alert_level",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="decision",
            name="risk_score",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="decision",
            name="shedding_level",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="decision",
            name="charge_battery_score",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="decision",
            name="discharge_battery_score",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="decision",
            name="protect_battery_score",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="decision",
            name="recommendation_score",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="decision",
            name="automatic_score",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="decision",
            name="blocked_score",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="decision",
            name="battery_action",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name="decision",
            name="explanation",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="decision",
            name="fired_rules",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="decision",
            name="input_facts",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="decision",
            name="fuzzy_values",
            field=models.JSONField(default=dict),
        ),
    ]
