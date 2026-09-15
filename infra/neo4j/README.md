# Neo4j graph model

Applied automatically by the `neo4j-init` Compose service, or:

```bash
python -m aus_gov_ingest graph-init
```

## Stage 1 nodes

| Label | Keys | Meaning |
| --- | --- | --- |
| `Person` | `id`, `slug`, `name` | Senator, minister, or official |
| `Hearing` | `id`, `slug`, `title`, `held_on` | Estimates or committee hearing |
| `Committee` | `id`, `slug`, `name` | Senate committee |
| `Topic` | `id`, `slug`, `name` | Coarse subject tag |
| `Document` | `id`, `title`, `doc_type` | Hansard / program / QON stub |

## Stage 1 relationships

```
(Person)-[:APPEARED_AT {role}]->(Hearing)
(Hearing)-[:HELD_BY]->(Committee)
(Person)-[:MEMBER_OF {role}]->(Committee)
(Hearing)-[:DISCUSSES]->(Topic)
(Document)-[:TRANSCRIPT_OF]->(Hearing)
```

`role` on `APPEARED_AT` is one of: `chair`, `senator`, `minister`, `official`, `witness`.

## Browser

http://localhost:7474 — user `neo4j`, password `ausgovmap`.
