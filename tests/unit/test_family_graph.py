"""Unit tests for the M2 family graph."""

from types import SimpleNamespace

from backend.modules.m2_temporal.family_graph import FamilyGraph


def _person(pid: int, name: str, birth: str | None = None, place: str | None = None):
    return SimpleNamespace(
        id=pid,
        name=name,
        birth_date=birth,
        birth_place=place,
        gedcom_id=f"I{pid}",
    )


def test_empty_graph_summary():
    g = FamilyGraph()
    assert "sem dados" in g.get_narrative_summary()
    assert g.stats["total_persons"] == 0


def test_add_person_and_relations():
    g = FamilyGraph()
    g.add_person(_person(1, "João"))
    g.add_person(_person(2, "Maria"))
    g.add_relation(1, 2, "parent")

    assert g.stats["total_persons"] == 2
    assert g.stats["total_relations"] == 1
    summary = g.get_narrative_summary()
    assert "João" in summary and "Maria" in summary
    assert "parent" in summary


def test_family_context_depth():
    g = FamilyGraph()
    for i, n in enumerate(["Ana", "Bento", "Carla"], start=1):
        g.add_person(_person(i, n))
    g.add_relation(1, 2, "parent")
    g.add_relation(2, 3, "parent")

    ctx = g.get_family_context(1, depth=1)
    names = {r["name"] for r in ctx["relatives"]}
    assert names == {"Bento"}

    ctx2 = g.get_family_context(1, depth=2)
    names2 = {r["name"] for r in ctx2["relatives"]}
    assert names2 == {"Bento", "Carla"}


def test_persons_context_includes_birth_info():
    g = FamilyGraph()
    g.add_person(_person(1, "Rosa", birth="1950-03-04", place="Covilhã"))
    text = g.get_persons_context([1])
    assert "Rosa" in text
    assert "1950" in text
    assert "Covilhã" in text


def test_save_load_roundtrip(tmp_path):
    g = FamilyGraph()
    g.add_person(_person(1, "Ana"))
    g.add_person(_person(2, "Bento"))
    g.add_relation(1, 2, "spouse")

    path = tmp_path / "graph.json"
    g.save(path)

    g2 = FamilyGraph()
    g2.load(path)
    assert g2.stats["total_persons"] == 2
    assert g2.stats["total_relations"] == 1
