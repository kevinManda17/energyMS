# Agent conversationnel — perspective future (NON développé)

> ⚠️ L'agent conversationnel **n'est pas** développé dans la version actuelle.
> Il est documenté ici uniquement comme **module futur / placeholder désactivé**
> et ne doit pas être considéré comme une fonctionnalité centrale.

## Idée
Un assistant en langage naturel permettant de :
- interroger l'état énergétique (« Quelle est ma production aujourd'hui ? »)
- expliquer une décision du moteur flou
- recommander des actions d'optimisation

## Pourquoi désactivé maintenant
La priorité v1 porte sur la supervision, la prévision et la décision. L'agent
sera ajouté ultérieurement sans impacter l'architecture existante (il consommera
les mêmes endpoints REST).

## Emplacement prévu
- Backend : future app `apps/assistant/` (placeholder).
- Frontend / mobile : écran « Agent IA » déjà présent côté Paramètres, marqué
  **Désactivé — perspective future**.
