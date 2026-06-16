"""Export persons + relationships back to a GEDCOM 5.5.1 file.

The inverse of ``gedcom_parser``: lets the user download the family they
built (by hand or imported) as the genealogy standard, re-importable into
Ancestry / MyHeritage / FamilySearch / etc. Useful for a technical project
because it demonstrates standards interoperability and round-trip import.

The relationship graph (``pai`` / ``mãe`` / ``cônjuge`` edges) is folded
into GEDCOM ``FAM`` records: each distinct (father, mother) pair becomes a
family, with its children and any childless spouse pairs included.
"""

from collections import OrderedDict

_MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
           "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def _date_line(dt) -> str | None:
    if not dt:
        return None
    try:
        return f"{dt.day:02d} {_MONTHS[dt.month - 1]} {dt.year}"
    except Exception:
        return None


def _name_line(name: str | None) -> str:
    name = (name or "").strip()
    if " " in name:
        given, surname = name.rsplit(" ", 1)
        return f"{given} /{surname}/"
    return name


def persons_to_gedcom(persons: list, relationships: list) -> str:
    """Render ``persons`` + ``relationships`` (ORM objects) as GEDCOM text."""
    lines: list[str] = []
    add = lines.append

    add("0 HEAD")
    add("1 SOUR LivingMemory")
    add("2 NAME Living Memory")
    add("1 GEDC")
    add("2 VERS 5.5.1")
    add("2 FORM LINEAGE-LINKED")
    add("1 CHAR UTF-8")

    pid = {p.id: f"@I{i + 1}@" for i, p in enumerate(persons)}
    sex = {p.id: (p.sex or "") for p in persons}

    # child_id -> {"pai": parent_id, "mãe": parent_id}; plus spouse pairs.
    parents: dict[int, dict[str, int]] = {}
    spouses: list[tuple[int, int]] = []
    for r in relationships:
        if r.kind in ("pai", "mãe"):
            parents.setdefault(r.to_person_id, {})[r.kind] = r.from_person_id
        elif r.kind == "cônjuge":
            spouses.append((r.from_person_id, r.to_person_id))

    # Fold into families keyed by (father, mother).
    fams: "OrderedDict[tuple, dict]" = OrderedDict()

    def ensure_fam(father, mother) -> dict:
        key = (father, mother)
        if key not in fams:
            fams[key] = {"husband": father, "wife": mother, "children": []}
        return fams[key]

    for child_id, pr in parents.items():
        ensure_fam(pr.get("pai"), pr.get("mãe"))["children"].append(child_id)

    for a, b in spouses:
        # Order by sex when known (M = husband).
        if sex.get(a) == "F" or sex.get(b) == "M":
            husband, wife = b, a
        else:
            husband, wife = a, b
        if (husband, wife) not in fams and (wife, husband) not in fams:
            ensure_fam(husband, wife)

    fams_list = list(fams.values())
    fam_id = {i: f"@F{i + 1}@" for i in range(len(fams_list))}

    fams_as_spouse: dict[int, list[int]] = {}
    fams_as_child:  dict[int, int] = {}
    for i, f in enumerate(fams_list):
        if f["husband"]:
            fams_as_spouse.setdefault(f["husband"], []).append(i)
        if f["wife"]:
            fams_as_spouse.setdefault(f["wife"], []).append(i)
        for c in f["children"]:
            fams_as_child[c] = i

    # ── INDI records ──
    for p in persons:
        add(f"0 {pid[p.id]} INDI")
        add(f"1 NAME {_name_line(p.name)}")
        if sex.get(p.id) in ("M", "F"):
            add(f"1 SEX {sex[p.id]}")
        bd = _date_line(getattr(p, "birth_date", None))
        if bd or getattr(p, "birth_place", None):
            add("1 BIRT")
            if bd:
                add(f"2 DATE {bd}")
            if getattr(p, "birth_place", None):
                add(f"2 PLAC {p.birth_place}")
        dd = _date_line(getattr(p, "death_date", None))
        if dd:
            add("1 DEAT")
            add(f"2 DATE {dd}")
        if getattr(p, "notes", None):
            note_lines = str(p.notes).split("\n")
            add(f"1 NOTE {note_lines[0]}")
            for nl in note_lines[1:]:
                add(f"2 CONT {nl}")
        for fi in fams_as_spouse.get(p.id, []):
            add(f"1 FAMS {fam_id[fi]}")
        if p.id in fams_as_child:
            add(f"1 FAMC {fam_id[fams_as_child[p.id]]}")

    # ── FAM records ──
    for i, f in enumerate(fams_list):
        if not f["husband"] and not f["wife"] and not f["children"]:
            continue
        add(f"0 {fam_id[i]} FAM")
        if f["husband"] in pid:
            add(f"1 HUSB {pid[f['husband']]}")
        if f["wife"] in pid:
            add(f"1 WIFE {pid[f['wife']]}")
        for c in f["children"]:
            if c in pid:
                add(f"1 CHIL {pid[c]}")

    add("0 TRLR")
    return "\n".join(lines) + "\n"
