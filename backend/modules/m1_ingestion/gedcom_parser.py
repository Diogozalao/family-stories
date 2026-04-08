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

from backend.models.timeline import Person

log = structlog.get_logger()


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
    db: AsyncSession
) -> dict:
    """
    Lê ficheiro GEDCOM e guarda pessoas na BD.
    Retorna estatísticas do que foi importado.
    """
    from backend.modules.m2_temporal.family_graph import FamilyGraph
    from backend.core.config import settings

    parser = GEDCOMParser()
    data   = parser.parse(file_path)

    graph  = FamilyGraph()
    graph_path = settings.PROCESSED_DIR / "family_graph.json"
    graph.load(graph_path)

    persons_created = 0
    persons_updated = 0

    # Cria/atualiza pessoas na BD
    person_id_map = {}  # gedcom_id → BD id

    for gedcom_id, indi in data["individuals"].items():
        if not indi.get("name"):
            continue

        # Verifica se já existe
        existing = await db.execute(
            select(Person).where(Person.gedcom_id == indi["gedcom_id"])
        )
        person = existing.scalar_one_or_none()

        notes_text = " ".join(indi.get("notes", []))

        if person:
            # Atualiza
            person.name        = indi["name"]
            person.birth_date  = indi.get("birth_date")
            person.death_date  = indi.get("death_date")
            person.birth_place = indi.get("birth_place")
            person.notes       = notes_text or None
            persons_updated += 1
        else:
            # Cria
            person = Person(
                name        = indi["name"],
                birth_date  = indi.get("birth_date"),
                death_date  = indi.get("death_date"),
                birth_place = indi.get("birth_place"),
                gedcom_id   = indi["gedcom_id"],
                notes       = notes_text or None,
            )
            db.add(person)
            persons_created += 1

        await db.flush()  # Obtem o ID
        person_id_map[gedcom_id] = person.id

        # Adiciona ao grafo
        graph.add_person(person)

    await db.commit()

    # Adiciona relações familiares ao grafo
    relations_added = 0
    for fam_id, fam in data["families"].items():
        husband_id = person_id_map.get(fam.get("husband"))
        wife_id    = person_id_map.get(fam.get("wife"))

        if husband_id and wife_id:
            graph.add_relation(husband_id, wife_id, "cônjuge")
            graph.add_relation(wife_id, husband_id, "cônjuge")
            relations_added += 2

            # Evento de casamento na timeline
            if fam.get("marr_date"):
                from backend.models.timeline import TimelineEvent, ConfidenceLevel
                marr_event = TimelineEvent(
                    event_date      = fam["marr_date"],
                    date_confidence = ConfidenceLevel.HIGH,
                    date_label      = fam["marr_date"].strftime("%d/%m/%Y") if fam["marr_date"] else None,
                    event_type      = "casamento",
                    title           = f"Casamento",
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
                    relations_added += 2
                if wife_id:
                    graph.add_relation(wife_id, child_id, "mãe")
                    graph.add_relation(child_id, wife_id, "filho de")
                    relations_added += 2

    await db.commit()

    # Guarda grafo atualizado
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph.save(graph_path)

    log.info("gedcom_imported",
        persons_created=persons_created,
        persons_updated=persons_updated,
        relations=relations_added,
        graph_nodes=len(graph.graph.nodes)
    )

    return {
        "persons_created":  persons_created,
        "persons_updated":  persons_updated,
        "families_processed": len(data["families"]),
        "relations_added":  relations_added,
        "graph_nodes":      len(graph.graph.nodes),
        "graph_edges":      len(graph.graph.edges),
    }
