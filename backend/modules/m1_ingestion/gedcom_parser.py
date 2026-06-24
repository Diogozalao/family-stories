"""
Parser GEDCOM completo para árvores genealógicas.

GEDCOM (GEnealogical Data COMmunication) é o formato standard
exportado por Ancestry, MyHeritage, FamilySearch, etc.

O que extraímos:
- Pessoas (nome, nascimento, morte, local, notas)
- Famílias (casamentos, filhos)
- Relações (pai, mãe, filho, cônjuge)
"""

import structlog
from pathlib import Path
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.timeline import Person, Relationship

log = structlog.get_logger()


def display_gedcom_id(gedcom_id: Optional[str]) -> Optional[str]:
    """Strip the per-family namespace from a stored gedcom_id for display.

    Persisted ids look like ``"Dinis::I1"`` (see ``gedcom_to_database``);
    the user only ever wants to see the raw ``"I1"``.
    """
    if gedcom_id and "::" in gedcom_id:
        return gedcom_id.split("::", 1)[1]
    return gedcom_id


class GEDCOMParser:
    """
    Parser GEDCOM implementado de raiz para máximo controlo.
    Lê o ficheiro linha a linha e extrai toda a informação genealógica.
    """

    def __init__(self):
        self.individuals = {}   # @I1@ → dados da pessoa
        self.families    = {}   # @F1@ → dados da família
        self.notes       = {}   # @N1@ → notas

    def parse(self, file_path: Path) -> dict:
        """
        Lê ficheiro GEDCOM e devolve dicionário com pessoas e famílias.
        """
        log.info("gedcom_parsing", file=str(file_path))

        try:
            # Tenta UTF-8 primeiro, depois latin-1 (ficheiros antigos)
            try:
                lines = file_path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                lines = file_path.read_text(encoding="latin-1").splitlines()

            self._parse_lines(lines)

            result = {
                "individuals": self.individuals,
                "families":    self.families,
                "stats": {
                    "total_persons":  len(self.individuals),
                    "total_families": len(self.families),
                }
            }

            log.info("gedcom_parsed",
                persons=len(self.individuals),
                families=len(self.families)
            )
            return result

        except Exception as e:
            log.error("gedcom_parse_error", file=str(file_path), error=str(e))
            return {"individuals": {}, "families": {}, "stats": {}}

    def _parse_lines(self, lines: list[str]):
        current_record = None
        current_type   = None
        current_sub    = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            parts = line.split(" ", 2)
            if len(parts) < 2:
                continue

            level = parts[0]
            tag   = parts[1] if len(parts) > 1 else ""
            value = parts[2] if len(parts) > 2 else ""

            # Nível 0 — início de um novo registo
            if level == "0":
                if tag.startswith("@") and value == "INDI":
                    current_record = tag
                    current_type   = "INDI"
                    current_sub    = None
                    self.individuals[current_record] = {
                        "id":           current_record,
                        "name":         None,
                        "given_name":   None,
                        "surname":      None,
                        "sex":          None,
                        "birth_date":   None,
                        "birth_place":  None,
                        "death_date":   None,
                        "death_place":  None,
                        "notes":        [],
                        "gedcom_id":    current_record.strip("@"),
                    }
                elif tag.startswith("@") and value == "FAM":
                    current_record = tag
                    current_type   = "FAM"
                    current_sub    = None
                    self.families[current_record] = {
                        "id":       current_record,
                        "husband":  None,
                        "wife":     None,
                        "children": [],
                        "marr_date": None,
                        "marr_place": None,
                    }
                else:
                    current_record = None
                    current_type   = None

            # Nível 1 — atributos principais
            elif level == "1" and current_record:
                current_sub = tag

                if current_type == "INDI":
                    if tag == "NAME":
                        # Nome no formato "Primeiro /Apelido/"
                        name = value.replace("/", "").strip()
                        self.individuals[current_record]["name"] = name
                        # Separa próprio e apelido
                        if "/" in value:
                            parts_name = value.split("/")
                            self.individuals[current_record]["given_name"] = parts_name[0].strip()
                            if len(parts_name) > 1:
                                self.individuals[current_record]["surname"] = parts_name[1].strip()
                    elif tag == "SEX":
                        self.individuals[current_record]["sex"] = value
                    elif tag == "NOTE":
                        if value:
                            self.individuals[current_record]["notes"].append(value)

                elif current_type == "FAM":
                    if tag == "HUSB":
                        self.families[current_record]["husband"] = value
                    elif tag == "WIFE":
                        self.families[current_record]["wife"] = value
                    elif tag == "CHIL":
                        self.families[current_record]["children"].append(value)

            # Nível 2 — sub-atributos (datas, locais)
            elif level == "2" and current_record:
                if current_type == "INDI":
                    if current_sub == "BIRT":
                        if tag == "DATE":
                            self.individuals[current_record]["birth_date"] = self._parse_date(value)
                        elif tag == "PLAC":
                            self.individuals[current_record]["birth_place"] = value
                    elif current_sub == "DEAT":
                        if tag == "DATE":
                            self.individuals[current_record]["death_date"] = self._parse_date(value)
                        elif tag == "PLAC":
                            self.individuals[current_record]["death_place"] = value
                    elif current_sub == "NOTE":
                        if tag == "CONT" and value:
                            if self.individuals[current_record]["notes"]:
                                self.individuals[current_record]["notes"][-1] += " " + value

                elif current_type == "FAM":
                    if current_sub == "MARR":
                        if tag == "DATE":
                            self.families[current_record]["marr_date"] = self._parse_date(value)
                        elif tag == "PLAC":
                            self.families[current_record]["marr_place"] = value

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parseia datas GEDCOM — vários formatos possíveis.
        Ex: "15 MAR 1945", "MAR 1945", "1945", "ABT 1950"
        """
        if not date_str:
            return None

        # Remove qualificadores (ABT = about, BEF = before, AFT = after)
        for prefix in ["ABT ", "BEF ", "AFT ", "CAL ", "EST ", "INT "]:
            date_str = date_str.replace(prefix, "")
        date_str = date_str.strip()

        MESES = {
            "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
            "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
            # Português
            "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
            "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
        }

        parts = date_str.upper().split()
        try:
            if len(parts) == 3:
                day   = int(parts[0])
                month = MESES.get(parts[1], 1)
                year  = int(parts[2])
                return datetime(year, month, day)
            elif len(parts) == 2:
                month = MESES.get(parts[0], 1)
                year  = int(parts[1])
                return datetime(year, month, 1)
            elif len(parts) == 1:
                year = int(parts[0])
                return datetime(year, 1, 1)
        except (ValueError, KeyError):
            pass
        return None


async def gedcom_to_database(
    file_path: Path,
    db: AsyncSession,
    user_id,
    family_label: str | None = None,
    project_id: int | None = None,
) -> dict:
    """
    Lê ficheiro GEDCOM e guarda pessoas na BD para o ``user_id`` indicado.

    ``family_label`` (ex.: "Dinis", "Nogueira") é gravado em cada Person
    importada para a UI poder agrupar várias árvores num mesmo arquivo.

    O grafo é serializado para ``data/processed/graphs/{user_id}.json`` —
    assim os parentes importados por um utilizador nunca aparecem para
    outro. As pessoas dedupedam-se por ``(user_id, gedcom_id)``, que é o
    índice único definido em SQL.
    """
    from backend.core.config import settings
    from backend.modules.m2_temporal.family_graph import FamilyGraph

    import uuid as _uuid

    parser = GEDCOMParser()
    data   = parser.parse(file_path)

    # Namespace the *persisted* gedcom_id so two different GEDCOM files never
    # collide on the ``(user_id, gedcom_id)`` unique index. Genealogy exports
    # almost always restart their ids at ``@I1@`` per file, so importing a
    # second family would otherwise UPDATE (overwrite) the first family's
    # people — silently merging unrelated trees. The label is the natural,
    # stable namespace: re-importing the SAME labelled family stays idempotent;
    # an unlabelled import gets a one-off batch id so it can never clobber an
    # existing tree. The raw id is kept for display (see ``display_gedcom_id``).
    namespace = (family_label or "").strip() or f"f{_uuid.uuid4().hex[:8]}"

    def _scoped(raw_gid: str) -> str:
        return f"{namespace}::{raw_gid}"

    # Track entries the parser saw but had no usable ``NAME`` tag — these are
    # silently skipped below, and historically that left users wondering why
    # a 50-person file only produced 20 rows. Surfacing the count in the
    # response makes the gap obvious instead of mysterious.
    skipped_no_name = sum(
        1 for indi in data["individuals"].values() if not indi.get("name")
    )

    graph_folder = settings.PROCESSED_DIR / "graphs"
    graph_folder.mkdir(parents=True, exist_ok=True)
    graph_path = graph_folder / f"{user_id}.json"

    graph = FamilyGraph()
    graph.load(graph_path)

    # Batch the existence check: one SELECT instead of N per-person SELECTs.
    # For a tree with hundreds of individuals this is the difference between
    # a few hundred milliseconds and tens of seconds.
    incoming_gedcom_ids = [
        _scoped(indi["gedcom_id"]) for indi in data["individuals"].values() if indi.get("name")
    ]
    existing_by_gedcom_id: dict[str, Person] = {}
    if incoming_gedcom_ids:
        existing_rows = (await db.execute(
            select(Person).where(
                Person.user_id == user_id,
                Person.gedcom_id.in_(incoming_gedcom_ids),
            )
        )).scalars().all()
        existing_by_gedcom_id = {p.gedcom_id: p for p in existing_rows}

    persons_created = 0
    persons_updated = 0
    pending_persons: list[tuple[str, Person]] = []   # (gedcom_local_id, Person)

    for gedcom_id, indi in data["individuals"].items():
        if not indi.get("name"):
            continue

        notes_text = " ".join(indi.get("notes", []))
        person = existing_by_gedcom_id.get(_scoped(indi["gedcom_id"]))

        if person:
            person.name         = indi["name"]
            person.sex          = indi.get("sex") or person.sex
            person.birth_date   = indi.get("birth_date")
            person.death_date   = indi.get("death_date")
            person.birth_place  = indi.get("birth_place")
            person.notes        = notes_text or None
            # Only overwrite the label when the caller supplied one — re-
            # importing without a label keeps the existing grouping.
            if family_label:
                person.family_label = family_label
            if project_id is not None:
                person.project_id = project_id
            persons_updated += 1
        else:
            person = Person(
                user_id      = user_id,
                project_id   = project_id,   # None = global Family; set = project-only.
                name         = indi["name"],
                sex          = indi.get("sex"),
                birth_date   = indi.get("birth_date"),
                death_date   = indi.get("death_date"),
                birth_place  = indi.get("birth_place"),
                gedcom_id    = _scoped(indi["gedcom_id"]),
                notes        = notes_text or None,
                family_label = family_label,
            )
            db.add(person)
            persons_created += 1

        pending_persons.append((gedcom_id, person))

    # Single flush — every autogenerated ``person.id`` is populated in one
    # roundtrip, instead of one round-trip per row.
    await db.flush()

    person_id_map: dict[str, int] = {}
    for gedcom_id, person in pending_persons:
        person_id_map[gedcom_id] = person.id
        graph.add_person(person)

    await db.commit()

    # Persist relations in the DB too (idempotent). The on-disk graph
    # stays for the narrative summaries, but the database is now the
    # durable source of truth used by the tree view and the editor.
    existing_rel_rows = (await db.execute(
        select(Relationship.from_person_id, Relationship.to_person_id, Relationship.kind)
        .where(Relationship.user_id == user_id)
    )).all()
    existing_rel = {(r[0], r[1], r[2]) for r in existing_rel_rows}

    def add_rel(frm: int, to: int, kind: str) -> None:
        key = (frm, to, kind)
        if key in existing_rel:
            return
        db.add(Relationship(user_id=user_id, from_person_id=frm, to_person_id=to, kind=kind))
        existing_rel.add(key)

    relations_added = 0
    for fam_id, fam in data["families"].items():
        husband_id = person_id_map.get(fam.get("husband"))
        wife_id    = person_id_map.get(fam.get("wife"))

        if husband_id and wife_id:
            graph.add_relation(husband_id, wife_id, "cônjuge")
            graph.add_relation(wife_id, husband_id, "cônjuge")
            add_rel(husband_id, wife_id, "cônjuge")
            relations_added += 2

            if fam.get("marr_date"):
                from backend.models.timeline import ConfidenceLevel, TimelineEvent
                marr_event = TimelineEvent(
                    user_id         = user_id,
                    project_id      = project_id,
                    event_date      = fam["marr_date"],
                    date_confidence = ConfidenceLevel.HIGH,
                    date_label      = fam["marr_date"].strftime("%d/%m/%Y") if fam["marr_date"] else None,
                    event_type      = "casamento",
                    title           = "Casamento",
                    location        = fam.get("marr_place"),
                    person_ids      = [husband_id, wife_id],
                    sort_order      = int(fam["marr_date"].timestamp()) if fam["marr_date"] else 0,
                )
                db.add(marr_event)

        for child_gedcom_id in fam.get("children", []):
            child_id = person_id_map.get(child_gedcom_id)
            if child_id:
                if husband_id:
                    graph.add_relation(husband_id, child_id, "pai")
                    graph.add_relation(child_id, husband_id, "filho de")
                    add_rel(husband_id, child_id, "pai")
                    relations_added += 2
                if wife_id:
                    graph.add_relation(wife_id, child_id, "mãe")
                    graph.add_relation(child_id, wife_id, "filho de")
                    add_rel(wife_id, child_id, "mãe")
                    relations_added += 2

    await db.commit()

    graph.save(graph_path)

    total_seen = len(data["individuals"])
    log.info("gedcom_imported",
        persons_seen     = total_seen,
        persons_created  = persons_created,
        persons_updated  = persons_updated,
        persons_skipped  = skipped_no_name,
        relations        = relations_added,
        graph_nodes      = len(graph.graph.nodes),
    )

    return {
        "persons_seen":       total_seen,
        "persons_created":    persons_created,
        "persons_updated":    persons_updated,
        "persons_skipped":    skipped_no_name,
        "families_processed": len(data["families"]),
        "relations_added":    relations_added,
        "graph_nodes":        len(graph.graph.nodes),
        "graph_edges":        len(graph.graph.edges),
    }
