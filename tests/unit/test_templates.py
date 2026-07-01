"""Unit tests for M3 narrative templates.

Templates are the only place we enforce European Portuguese style on
the LLM, so we want to notice immediately if the rules get weakened.
"""

from backend.modules.m3_narrative.templates import (
    NARRATIVE_TEMPLATES,
    PT_PT_RULES,
)


EXPECTED_KEYS = {"default", "fotografia", "casamento", "viagem", "nascimento", "celebração"}


def test_every_expected_template_is_present():
    assert EXPECTED_KEYS.issubset(NARRATIVE_TEMPLATES.keys())


def test_templates_have_required_fields():
    for key, tpl in NARRATIVE_TEMPLATES.items():
        for field in ("name", "tone", "structure", "prompt"):
            assert field in tpl, f"{key} is missing {field}"
        assert tpl["prompt"].strip(), f"{key} has an empty prompt"


def test_all_templates_inline_pt_pt_rules():
    # The anti-Brazilian guardrails must be present everywhere so the LLM
    # cannot drift just because the user picked a different template.
    for key, tpl in NARRATIVE_TEMPLATES.items():
        assert PT_PT_RULES in tpl["prompt"], f"{key} dropped PT_PT_RULES"


def test_pt_pt_rules_reject_common_brazilianisms():
    rules = PT_PT_RULES.lower()
    # Must explicitly forbid you-form and gerúndio drift.
    assert "você" in rules
    assert "gerúndio" in rules
    # Must list at least a few european vocab anchors.
    for anchor in ["câmara", "ecrã", "autocarro", "telemóvel"]:
        assert anchor in rules


def test_prompts_expect_event_context_placeholders():
    # The generator formats each prompt with these fields — if any template
    # drops them we'd crash at runtime with a KeyError.
    for key, tpl in NARRATIVE_TEMPLATES.items():
        assert "{events_context}" in tpl["prompt"], key
        assert "{tone}" in tpl["prompt"], key


def test_length_specs_cover_all_levels_with_growing_caps():
    from backend.modules.m3_narrative.templates import LENGTH_SPECS

    levels = ["short", "medium", "long", "epic"]
    assert list(LENGTH_SPECS) == levels
    # Token caps grow with the requested duration.
    caps = [LENGTH_SPECS[lvl]["max_tokens"] for lvl in levels]
    assert caps == sorted(caps)
    assert caps[0] < caps[-1]
    # Every level has a PT and an EN guide.
    for lvl in levels:
        assert LENGTH_SPECS[lvl]["pt"].strip()
        assert LENGTH_SPECS[lvl]["en"].strip()
