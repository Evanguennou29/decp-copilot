"""Builds the prompt sent to the generation model.

The instructions demand a citation — the market's ``uid`` — for every
figure or market the model mentions, so ``decp.answer.generate`` has
something concrete to check the response against.
"""

from __future__ import annotations

from collections.abc import Sequence

from decp.retrieval.search import SearchResult

SYSTEM_INSTRUCTIONS = (
    "Tu es un assistant qui compare des marchés publics français déjà attribués, "
    "à partir de la liste ci-dessous uniquement. Réponds en français, en euros. "
    "Pour CHAQUE marché ou montant que tu mentionnes, cite son identifiant exact "
    "entre crochets, par exemple [uid: 12345678900011M001]. N'invente aucun "
    "marché, montant, acheteur ou date qui ne figure pas dans la liste. Tu ne "
    "donnes ni conseil juridique ni recommandation de prix : tu restitues et "
    "compares les marchés fournis. Si la liste ne permet pas de répondre, dis-le "
    "explicitement plutôt que d'inventer."
)


def _format_montant(montant: float | None) -> str:
    if montant is None:
        return "montant inconnu"
    return f"{montant:,.0f} €".replace(",", " ")


def format_market(result: SearchResult) -> str:
    date_str = (
        result.date_notification.isoformat() if result.date_notification else "date inconnue"
    )
    departement = result.departement_nom or "département inconnu"
    return (
        f"- [uid: {result.uid}] {result.acheteur_nom} ({departement}), "
        f"notifié le {date_str}, montant {_format_montant(result.montant)} : {result.objet}"
    )


def build_prompt(question: str, results: Sequence[SearchResult]) -> str:
    markets_block = "\n".join(format_market(r) for r in results) or "(aucun marché trouvé)"
    return (
        f"{SYSTEM_INSTRUCTIONS}\n\n"
        f"Question : {question}\n\n"
        f"Marchés disponibles :\n{markets_block}\n\n"
        "Réponse :"
    )
