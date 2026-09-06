"""MCP server: hybrid search and single-market lookup as tools for any MCP
client (e.g. Claude Desktop, Claude Code).

Reuses the same ``Dependencies`` bundle and ``load_real_dependencies()``
as the HTTP API (``decp.api.app``) — same database, encoder, and vector
index, no separate loading logic. See README.md, "MCP server", for how to
connect a client. ``create_server`` takes an explicit ``Dependencies``
bundle (like ``decp.api.app.create_app``) so tests can inject a tiny
fixture-built database and a fake encoder — never the real, network- or
model-loading path.
"""

from __future__ import annotations

from dataclasses import asdict

import duckdb
from mcp.server.mcpserver import MCPServer

from decp.api.app import Dependencies, load_real_dependencies
from decp.retrieval.search import search


def search_marches(deps: Dependencies, question: str, top_k: int = 10) -> list[dict]:
    """Pure logic behind the ``search_marches`` tool — testable without MCP."""
    results = search(
        question,
        database_path=deps.database_path,
        vector_index=deps.vector_index,
        encoder=deps.encoder,
        top_k=top_k,
    )
    markets = []
    for result in results:
        data = asdict(result)
        if data["date_notification"] is not None:
            data["date_notification"] = result.date_notification.isoformat()
        markets.append(data)
    return markets


def get_marche(deps: Dependencies, uid: str) -> dict:
    """Pure logic behind the ``get_marche`` tool — testable without MCP."""
    con = duckdb.connect(str(deps.database_path), read_only=True)
    try:
        row = con.execute(
            "SELECT uid, acheteur_nom, objet, montant, dateNotification, "
            "acheteur_departement_nom, codeCPV, type, procedure "
            "FROM marches WHERE uid = ? LIMIT 1",
            [uid],
        ).fetchone()
    finally:
        con.close()

    if row is None:
        return {"error": f"Aucun marché trouvé pour l'identifiant {uid!r}."}

    columns = (
        "uid",
        "acheteur_nom",
        "objet",
        "montant",
        "date_notification",
        "departement_nom",
        "code_cpv",
        "type",
        "procedure",
    )
    data = dict(zip(columns, row, strict=True))
    if data["date_notification"] is not None:
        data["date_notification"] = data["date_notification"].isoformat()
    return data


def create_server(deps: Dependencies) -> MCPServer:
    mcp = MCPServer(
        "decp-copilot",
        instructions=(
            "Recherche et consultation des marchés publics français attribués "
            "depuis 2024 (DECP). Cite toujours l'identifiant (uid) d'un marché "
            "en le mentionnant."
        ),
    )

    @mcp.tool()
    def search_marches_tool(question: str, top_k: int = 10) -> list[dict]:
        """Recherche hybride de marchés publics (montant, département, type,
        date, et/ou description libre — ex. "moins de 50000 euros dans le
        Finistère"). Renvoie les marchés les plus pertinents avec leur uid,
        montant, acheteur, département, date et objet."""
        return search_marches(deps, question, top_k=top_k)

    @mcp.tool()
    def get_marche_tool(uid: str) -> dict:
        """Consulte un marché public par son identifiant exact (uid), tel
        que renvoyé par search_marches_tool."""
        return get_marche(deps, uid)

    return mcp


def main() -> None:
    create_server(load_real_dependencies()).run()


if __name__ == "__main__":
    main()
