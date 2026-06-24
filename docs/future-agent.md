# Agent conversationnel - perspective future

L'agent conversationnel n'est pas developpe dans la version actuelle. Il reste une perspective future et ne doit pas etre presente comme une fonctionnalite centrale du systeme.

## Idee

Un assistant en langage naturel pourrait plus tard permettre de :

- interroger l'etat energetique ;
- expliquer une decision du moteur flou ;
- recommander des actions d'optimisation ;
- aider a interpreter les rapports.

## Pourquoi il reste hors perimetre

La version actuelle se concentre sur la chaine :

```text
IoT -> mesures -> prevision -> decision floue -> alerte -> supervision
```

L'agent pourra consommer les memes endpoints REST sans modifier le coeur metier.

## Emplacement futur possible

- Backend : future app `apps/assistant/`.
- Frontend/mobile : ecran dedie, marque comme perspective future tant que non implemente.
