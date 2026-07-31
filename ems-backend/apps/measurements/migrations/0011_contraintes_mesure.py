"""Contraintes de `Measurement`, posees APRES le remplissage (§2.4).

Deux garanties que le schema ne donnait pas :

  - une grandeur n'a qu'UNE valeur a un instant donne. Sans elle, deux
    collectes meteo dans la meme heure creaient deux lignes contradictoires,
    et le moteur lisait « la derniere ecrite » — c'est-a-dire l'arbitraire ;
  - une donnee qui se DIT mesuree doit nommer son capteur. C'est ce qui
    empeche une estimation de se faire passer pour une lecture.

La contrainte d'unicite est conditionnelle (`quantity` non vide) : les lignes
dont le type n'a pas de correspondance connue restent tolerees telles quelles
plutot que d'etre forcees dans une grandeur inventee.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("measurements", "0010_migrer_types_vers_grandeurs"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='measurement',
            constraint=models.UniqueConstraint(condition=models.Q(('quantity', ''), _negated=True), fields=('house', 'quantity', 'timestamp'), name='une_mesure_par_grandeur_et_instant'),
        ),
        migrations.AddConstraint(
            model_name='measurement',
            constraint=models.CheckConstraint(check=models.Q(models.Q(('source', 'SENSOR'), _negated=True), ('sensor__isnull', False), _connector='OR'), name='mesure_capteur_a_un_capteur'),
        ),
    ]
