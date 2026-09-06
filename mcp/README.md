# MCP server

Exposes the same hybrid search and market lookup as the HTTP API, as MCP
tools for any MCP client (Claude Desktop, Claude Code, etc.) — SPEC.md
lot 6.

## Tools

- **`search_marches_tool(question, top_k=10)`** — hybrid search (montant,
  département, type, date, and/or free text). Returns a list of markets,
  each with its `uid` (cite this), `montant`, `acheteur_nom`,
  `departement_nom`, `date_notification`, `objet`, and relevance `score`.
- **`get_marche_tool(uid)`** — full details for one market by its exact
  `uid` (as returned by `search_marches_tool`). Returns
  `{"error": "..."}` if the `uid` doesn't exist.

Both reuse `decp.api.app`'s `Dependencies`/`load_real_dependencies()` —
same database, embedding model, and vector index as the HTTP API; see the
main README's "Indexed corpus scope" for what's covered.

## Running it

Requires `python -m decp ingest` and `python -m decp index` to have been
run first (same prerequisite as `decp serve`):

```bash
make mcp   # python mcp/server.py — runs over stdio
```

## Connecting a client

For Claude Desktop, add to `claude_desktop_config.json` (Settings →
Developer → Edit Config):

```json
{
  "mcpServers": {
    "decp-copilot": {
      "command": "python",
      "args": ["mcp/server.py"],
      "cwd": "/absolute/path/to/decp-copilot"
    }
  }
}
```

`cwd` matters: by default the server reads `data/decp.duckdb` and
`data/index/decp.index.npz` relative to the working directory it's
launched from (see `decp.config.Settings`). Set `DECP_DATA_DIR` instead
(as an `env` entry alongside `command`) if you'd rather point at an
absolute data directory. Restart the client after editing the config.

Any other MCP client that can launch a local stdio command works the
same way — point it at `python mcp/server.py` with the repo as its
working directory.
