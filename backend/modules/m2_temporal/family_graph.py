import networkx as nx
import structlog
import json
from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.timeline import Person

log = structlog.get_logger()

class FamilyGraph:
    """
    Constrói e gere o grafo de relações familiares usando NetworkX.
    
    Nós = Pessoas
    Arestas = Relações (pai/mãe, filho, cônjuge, irmão)
    
    Usado pelo M3 para dar contexto ao LLM sobre quem é quem.
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_person(self, person: Person) -> None:
        self.graph.add_node(
            person.id,
            name       = person.name,
            birth_date = str(person.birth_date) if person.birth_date else None,
            birth_place= person.birth_place,
            gedcom_id  = person.gedcom_id,
        )
        log.info("graph_person_added", name=person.name, id=person.id)

    def add_relation(self, from_id: int, to_id: int, relation: str) -> None:
        """
        relation: 'parent', 'child', 'spouse', 'sibling'
        """
        self.graph.add_edge(from_id, to_id, relation=relation)

    def get_family_context(self, person_id: int, depth: int = 2) -> dict:
        """
        Retorna o contexto familiar de uma pessoa até N graus de separação.
        Usado pelo M3 para construir prompts contextualizados.
        """
        if person_id not in self.graph:
            return {"person": None, "relatives": []}

        person_data = self.graph.nodes[person_id]
        relatives = []

        # Percorre vizinhos até profundidade `depth`
        for neighbor in nx.ego_graph(self.graph, person_id, radius=depth).nodes():
            if neighbor == person_id:
                continue
            node = self.graph.nodes[neighbor]
            edge_data = self.graph.get_edge_data(person_id, neighbor) or \
                        self.graph.get_edge_data(neighbor, person_id) or {}
            relatives.append({
                "name":     node.get("name"),
                "relation": edge_data.get("relation", "familiar"),
                "id":       neighbor,
            })

        return {
            "person":    person_data,
            "relatives": relatives,
        }

    def get_narrative_summary(self) -> str:
        """
        Gera um resumo textual do grafo para passar ao LLM.
        Ex: 'João (pai de Maria, marido de Ana)'
        """
        if not self.graph.nodes:
            return "Família sem dados genealógicos definidos."

        lines = []
        for node_id in self.graph.nodes:
            node = self.graph.nodes[node_id]
            name = node.get("name", f"Pessoa {node_id}")
            
            relations = []
            for _, to_id, data in self.graph.out_edges(node_id, data=True):
                to_name = self.graph.nodes[to_id].get("name", f"Pessoa {to_id}")
                rel = data.get("relation", "familiar")
                relations.append(f"{rel} de {to_name}")

            if relations:
                lines.append(f"{name} ({', '.join(relations)})")
            else:
                lines.append(name)

        return "; ".join(lines)

    def save(self, path: Path) -> None:
        data = nx.node_link_data(self.graph)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        log.info("graph_saved", path=str(path))

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        data = json.loads(path.read_text())
        self.graph = nx.node_link_graph(data)
        log.info("graph_loaded", nodes=len(self.graph.nodes), path=str(path))

    @property
    def stats(self) -> dict:
        return {
            "total_persons":   len(self.graph.nodes),
            "total_relations": len(self.graph.edges),
            "is_connected":    nx.is_weakly_connected(self.graph) if self.graph.nodes else False,
        }
