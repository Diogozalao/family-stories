"""Unit tests for the European-Portuguese post-processor (M3)."""

from backend.modules.m3_narrative.pt_pt import (
    count_brasileirismos,
    pt_pt_postprocess,
)


def test_vocabulary_is_corrected():
    text = "Peguei o celular e o ônibus, depois comprei um sorvete."
    fixed, n = pt_pt_postprocess(text)
    assert "telemóvel" in fixed
    assert "autocarro" in fixed
    assert "gelado" in fixed
    assert "celular" not in fixed and "ônibus" not in fixed
    assert n == 3


def test_gerund_becomes_a_infinitivo():
    fixed, _ = pt_pt_postprocess("A avó estava chorando e ele continuava sorrindo.")
    assert "estava a chorar" in fixed
    assert "continuava a sorrir" in fixed


def test_case_is_preserved():
    fixed, _ = pt_pt_postprocess("Sorvete ao lanche.")
    assert fixed.startswith("Gelado")


def test_count_detects_tells_without_mutating():
    text = "O garoto pegou o trem; você viu?"
    before = count_brasileirismos(text)
    # garoto + trem + você  → 3 tells
    assert before == 3
    # counting must not change the text
    assert "garoto" in text


def test_clean_european_text_is_untouched():
    text = "A neta agarrou a câmara e fotografou o autocarro a passar."
    fixed, n = pt_pt_postprocess(text)
    assert n == 0
    assert fixed == text


def test_gender_flipping_words_are_not_naively_swapped():
    # "calçada"/"banheiro" were removed from the map precisely so we never
    # emit a broken article like "na passeio".
    fixed, _ = pt_pt_postprocess("Sentou-se na calçada perto do banheiro.")
    assert "na passeio" not in fixed
    assert "o casa de banho" not in fixed
