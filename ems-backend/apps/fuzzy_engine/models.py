from django.db import models

from apps.houses.models import House


class Decision(models.Model):
    """A decision produced by the fuzzy expert system."""

    house = models.ForeignKey(
        House, on_delete=models.CASCADE, related_name="decisions"
    )
    forecast = models.ForeignKey(
        "forecasting.Forecast",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decisions",
    )
    action = models.CharField(max_length=80)
    reason = models.TextField(blank=True)
    confidence_score = models.FloatField(default=0)
    input_snapshot = models.JSONField(default=dict)
    activated_rules = models.JSONField(default=list)
    decision_code = models.CharField(max_length=80, blank=True)
    decision_label = models.CharField(max_length=160, blank=True)
    execution_mode = models.CharField(max_length=30, blank=True)
    alert_level = models.CharField(max_length=20, blank=True)
    risk_score = models.FloatField(default=0)
    shedding_level = models.FloatField(default=0)
    charge_battery_score = models.FloatField(default=0)
    discharge_battery_score = models.FloatField(default=0)
    protect_battery_score = models.FloatField(default=0)
    recommendation_score = models.FloatField(default=0)
    automatic_score = models.FloatField(default=0)
    blocked_score = models.FloatField(default=0)
    battery_action = models.CharField(max_length=30, blank=True)
    explanation = models.TextField(blank=True)
    fired_rules = models.JSONField(default=list)
    input_facts = models.JSONField(default=dict)
    fuzzy_values = models.JSONField(default=dict)
    # Piste d'audit du raisonnement : scores avant planchers de sûreté, détail
    # des rampes, évaluation par ligne, plan de l'optimiseur. Un seul champ JSON
    # plutôt qu'une colonne par étape — le moteur gagne des étapes, le schéma ne
    # doit pas gagner une migration à chaque fois.
    reasoning_trace = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} ({self.confidence_score}) - {self.house}"


class DecisionLine(models.Model):
    """Ce que la décision a conclu POUR CHAQUE LIGNE.

    LE DÉFAUT CORRIGÉ : le raisonnement par ligne — six règles, des vétos, un
    optimiseur — vivait uniquement dans `Decision.reasoning_trace`, un champ
    JSON. Il était donc consultable pour UNE décision qu'on regarde, et
    inexploitable en masse : impossible de demander « combien de fois la ligne 2
    a-t-elle été protégée par un veto ce mois-ci ? », ou « quelle ligne
    l'optimiseur coupe-t-il le plus souvent ? ».

    Un raisonnement qu'on ne peut pas interroger n'est explicable qu'au cas par
    cas. Ces lignes-là le rendent interrogeable.

    `was_applied` distingue ce que le système a DÉCIDÉ de ce qu'il a FAIT. Les
    deux diffèrent légitimement — en mode assisté la décision attend une
    validation humaine, en mode automatique elle attend la fenêtre de
    confirmation — et confondre les deux ferait croire à des coupures qui n'ont
    jamais eu lieu.
    """

    decision = models.ForeignKey(
        Decision, on_delete=models.CASCADE, related_name="line_decisions"
    )
    line = models.ForeignKey(
        "devices.Line", on_delete=models.CASCADE, related_name="decisions"
    )
    shed_score = models.FloatField()
    is_blocked = models.BooleanField()
    # Quel véto a joué : « L003 » (charge vitale), « L005 » (déjà coupée),
    # « L006 » (capteur muet). Le code plutôt qu'une phrase, pour pouvoir
    # compter — la phrase, elle, vit dans la trace.
    blocked_reason = models.CharField(max_length=40, blank=True)
    power_w = models.FloatField(null=True, blank=True)
    state_before = models.BooleanField()
    state_desired = models.BooleanField()
    was_applied = models.BooleanField(default=False)

    class Meta:
        ordering = ["line__number"]
        constraints = [
            models.UniqueConstraint(
                fields=["decision", "line"],
                name="une_conclusion_par_decision_et_ligne",
            )
        ]

    def __str__(self) -> str:
        etat = "coupée" if not self.state_desired else "maintenue"
        return f"{self.line} {etat} (score {self.shed_score})"
