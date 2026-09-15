from __future__ import annotations

from pathlib import Path

from aus_gov_ingest.config import settings
from aus_gov_ingest.models import HearingIn


def _constraints_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "infra" / "neo4j" / "constraints.cypher"
        if candidate.exists():
            return candidate
    return here.parents[5] / "infra" / "neo4j" / "constraints.cypher"


CONSTRAINTS = _constraints_path()


class Neo4jStore:
    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password

    def _driver(self):
        from neo4j import GraphDatabase

        if not self.uri:
            raise RuntimeError("NEO4J_URI is not set")
        return GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def ping(self) -> bool:
        try:
            driver = self._driver()
            with driver.session() as session:
                session.run("RETURN 1").consume()
            driver.close()
            return True
        except Exception:
            return False

    def apply_constraints(self) -> None:
        statements = [
            stmt.strip()
            for stmt in CONSTRAINTS.read_text().split(";")
            if stmt.strip() and not stmt.strip().startswith("//")
        ]
        # strip comment-only leftovers
        clean: list[str] = []
        for stmt in statements:
            lines = [
                line
                for line in stmt.splitlines()
                if line.strip() and not line.strip().startswith("//")
            ]
            if lines:
                clean.append("\n".join(lines))
        driver = self._driver()
        with driver.session() as session:
            for stmt in clean:
                session.run(stmt)
        driver.close()

    def upsert_hearing(self, hearing: HearingIn, ids: dict[str, str]) -> None:
        """ids: hearing_id, committee_id?, person_ids[{slug: id}], topic_ids, document_ids."""
        driver = self._driver()
        with driver.session() as session:
            session.run(
                """
                MERGE (h:Hearing {id: $id})
                SET h.slug = $slug, h.title = $title, h.held_on = $held_on,
                    h.hearing_type = $hearing_type, h.source_key = $source_key,
                    h.portfolio = $portfolio
                """,
                id=ids["hearing_id"],
                slug=hearing.slug,
                title=hearing.title,
                held_on=str(hearing.held_on) if hearing.held_on else None,
                hearing_type=hearing.hearing_type,
                source_key=hearing.source_key,
                portfolio=hearing.portfolio,
            )
            if hearing.committee and ids.get("committee_id"):
                session.run(
                    """
                    MERGE (c:Committee {id: $cid})
                    SET c.slug = $slug, c.name = $name, c.chamber = $chamber
                    WITH c
                    MATCH (h:Hearing {id: $hid})
                    MERGE (h)-[:HELD_BY]->(c)
                    """,
                    cid=ids["committee_id"],
                    slug=hearing.committee.slug,
                    name=hearing.committee.name,
                    chamber=hearing.committee.chamber,
                    hid=ids["hearing_id"],
                )
            person_ids: dict[str, str] = ids.get("person_ids") or {}
            for appearance in hearing.people:
                person = appearance.person
                slug = appearance.person_slug or (person.slug if person else None)
                if not slug or slug not in person_ids:
                    continue
                session.run(
                    """
                    MERGE (p:Person {id: $pid})
                    SET p.slug = $slug, p.name = $name, p.party = $party,
                        p.role_title = $role_title
                    WITH p
                    MATCH (h:Hearing {id: $hid})
                    MERGE (p)-[r:APPEARED_AT]->(h)
                    SET r.role = $role
                    """,
                    pid=person_ids[slug],
                    slug=slug,
                    name=person.name if person else slug,
                    party=person.party if person else None,
                    role_title=person.role_title if person else None,
                    hid=ids["hearing_id"],
                    role=appearance.role,
                )
                if hearing.committee and ids.get("committee_id") and appearance.role == "chair":
                    session.run(
                        """
                        MATCH (p:Person {id: $pid})
                        MATCH (c:Committee {id: $cid})
                        MERGE (p)-[r:MEMBER_OF]->(c)
                        SET r.role = 'chair'
                        """,
                        pid=person_ids[slug],
                        cid=ids["committee_id"],
                    )
            topic_ids: dict[str, str] = ids.get("topic_ids") or {}
            for topic in hearing.topics:
                if topic.slug not in topic_ids:
                    continue
                session.run(
                    """
                    MERGE (t:Topic {id: $tid})
                    SET t.slug = $slug, t.name = $name
                    WITH t
                    MATCH (h:Hearing {id: $hid})
                    MERGE (h)-[:DISCUSSES]->(t)
                    """,
                    tid=topic_ids[topic.slug],
                    slug=topic.slug,
                    name=topic.name,
                    hid=ids["hearing_id"],
                )
            for doc_id in ids.get("document_ids") or []:
                session.run(
                    """
                    MERGE (d:Document {id: $did})
                    WITH d
                    MATCH (h:Hearing {id: $hid})
                    MERGE (d)-[:TRANSCRIPT_OF]->(h)
                    """,
                    did=doc_id,
                    hid=ids["hearing_id"],
                )
        driver.close()
