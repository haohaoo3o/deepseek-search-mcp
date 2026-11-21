# deepseek-search-mcp

Minimal single-file MCP server exposing the [DeepSeek Web Search API](https://api-docs.deepseek.com/zh-cn/guides/search) (`POST /v1/tools/search`) over stdio.

- **Single file** — `server.py` with inline [PEP 723](https://peps.python.org/pep-0723/) dependencies, nothing to install (`cryptography` is pinned to a prebuilt-friendly version so hosts without a Rust toolchain, e.g. Intel Macs, don't fail on source builds)
- **One tool** — `web_search`, no config surface beyond one environment variable
- **Drop-in friendly** — tool parameter names stay compatible with `mcp-server-askecho-search-infinity`, so prompts written for the retired server keep working
- Runs via [`uv`](https://docs.astral.sh/uv/), even straight from a raw GitHub URL — no clone, no pip

Not affiliated with DeepSeek. This is an independent community project.

## Setup

1. Get a DeepSeek API key from the [DeepSeek Open Platform](https://platform.deepseek.com/)
2. Point any stdio MCP client at `server.py` with `DEEPSEEK_API_KEY` set

Search requests are billed to your own DeepSeek account (about 5 CNY per 1,000 successful requests; failed or empty-result requests are free).

### Client configuration

Run-from-URL (no clone needed):

```json
{
  "mcpServers": {
    "deepseek-web-search": {
      "command": "uv",
      "args": [
        "run",
        "https://raw.githubusercontent.com/haohaoo3o/deepseek-search-mcp/main/server.py"
      ],
      "env": { "DEEPSEEK_API_KEY": "sk-..." }
    }
  }
}
```

Or after cloning:

```json
{
  "command": "uv",
  "args": ["run", "--no-project", "/absolute/path/to/deepseek-search-mcp/server.py"],
  "env": { "DEEPSEEK_API_KEY": "sk-..." }
}
```

`cryptography` is already pinned to `44.0.3` inside the script's inline metadata, so no extra flags are needed even on hosts without a Rust toolchain (e.g. Intel Macs, where newer releases fall back to a source build and fail).

## Tool: `web_search`

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `Query` | string | required | 1–128 chars; operators below are supported natively |
| `Count` | int | 10 | 1–50 |
| `SearchType` | string | `"web"` | only `web` is supported (DeepSeek has no image search) |
| `NeedContent` | bool | `false` | include page content per result |
| `NeedUrl` | bool | `true` | compatibility only; URLs are always returned |
| `Sites` | string | `""` | pipe-separated allowlist → `site:` operators |
| `BlockHosts` | string | `""` | pipe-separated blocklist → `-site:` operators |
| `TimeRange` | string | `""` | `OneDay` / `OneWeek` / `OneMonth` / `OneYear` → `after:` date |
| `AuthLevel` | int | 0 | `1` keeps only results with `authority >= 3` |
| `Industry`, `QueryRewrite`, `ContentFormats` | — | — | accepted for compatibility, ignored |

`Query` supports DeepSeek's search operators directly and they can be combined:
`site:github.com`, `-site:example.com`, `"exact phrase"`, `-exclude`, `lang:zh,en`, `after:2026-01-01`, `before:2026-06-01`.

## Response

```json
{
  "provider": "deepseek",
  "query": "mcp server example (site:github.com) after:2026-01-01",
  "count": 2,
  "results": [
    {
      "title": "...",
      "url": "https://...",
      "snippet": "short snippet",
      "summary": "longer summary",
      "content": "(empty unless NeedContent=true)",
      "site_name": "...",
      "date": "2026-07-28T00:00:00+00:00",
      "authority": 3,
      "rerank_score": 2.47
    }
  ]
}
```

Errors return `{"error": {"status": ..., "message": ...}}` instead of raising.

## Heavier alternative

If you want fetch-to-Markdown, structured extraction, or cited deep research on top of the same API, look at [radoxtech/deepseek-search-everywhere-mcp](https://github.com/radoxtech/deepseek-search-everywhere-mcp) — a full-featured, MCP-Registry-listed server. This project intentionally stays single-file and single-tool for setups that only need a lightweight `web_search`.

## License

[MIT](LICENSE)
