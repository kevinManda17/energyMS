from django.conf import settings
from django.db import models


class House(models.Model):
    """A home / domestic micro-grid owned by a user."""

    class Status(models.TextChoices):
        ONLINE = "ONLINE", "Online"
        OFFLINE = "OFFLINE", "Offline"
        MAINTENANCE = "MAINTENANCE", "Maintenance"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="houses",
    )
    name = models.CharField(max_length=120)
    location = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    description = models.TextField(blank=True)
    # `pv_capacity_kw` et `battery_capacity_kwh` ont été RETIRÉS.
    #
    # Ils dupliquaient ce que portent déjà les `EnergyAsset`, et les deux
    # sources divergeaient : `forecasting/services.py` retombait sur
    # `House.pv_capacity_kw` quand aucun panneau n'était renseigné, tandis que
    # `fuzzy_engine/engine.py` l'ignorait purement et simplement. Le module de
    # prévision et le moteur expert raisonnaient donc sur des capacités
    # différentes pour la même maison.
    #
    # Les propriétés calculées ci-dessous les remplacent : une seule source,
    # les actifs eux-mêmes.
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.ONLINE
    )
    # Dernier accès applicatif à ce micro-réseau (dashboard / météo). Sert à
    # ne collecter la météo que pour les micro-réseaux réellement consultés,
    # au lieu de balayer toutes les maisons figées.
    last_activity_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def pv_nominal_power_w(self) -> float | None:
        """Puissance crête installée, somme des panneaux ACTIFS.

        None quand aucun panneau n'est renseigné — et c'est une réponse, pas un
        échec : une capacité inconnue ne doit pas être remplacée par une valeur
        plausible, sans quoi la mise à l'échelle des prévisions PV reposerait
        sur un chiffre que personne n'a saisi.
        """
        return self._somme_actifs("PV_PANEL", "nominal_power_w")

    @property
    def battery_capacity_wh(self) -> float | None:
        """Capacité de stockage installée, somme des batteries ACTIVES."""
        return self._somme_actifs("BATTERY", "capacity_wh")

    def _somme_actifs(self, asset_type: str, champ: str) -> float | None:
        valeurs = (
            self.energy_assets.filter(asset_type=asset_type, status="ACTIVE")
            .exclude(**{f"{champ}__isnull": True})
            .values_list(champ, flat=True)
        )
        total = sum(float(v or 0) for v in valeurs)
        return total or None
