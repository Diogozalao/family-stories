"""Unit tests for the European-Portuguese post-processor (M3)."""

from backend.modules.m3_narrative.pt_pt import (
    count_brasileirismos,
    dedupe_and_trim,
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


def test_gender_agreement_is_corrected():
    # "lã" is feminine — a masculine determiner before it is fixed.
    fixed, n = pt_pt_postprocess("Lembro-me do cheiro do lã e da textura do lã.")
    assert "da lã" in fixed
    assert "do lã" not in fixed
    assert n == 2


def test_repeated_paragraphs_are_removed():
    rep = "A viagem foi das melhores memórias da nossa família."
    text = "Primeiro, a chegada à aldeia.\n\n" + "\n\n".join([rep, rep, rep])
    out, info = dedupe_and_trim(text)
    assert info["removed_paragraphs"] == 2
    assert out.count(rep) == 1


def test_incomplete_final_sentence_is_trimmed():
    text = "A neta abriu o álbum e sorriu. Depois virou a página e"
    out, info = dedupe_and_trim(text)
    assert info["trimmed"] is True
    assert out.endswith("sorriu.")


def test_dedupe_leaves_clean_text_untouched():
    text = "Primeiro parágrafo completo.\n\nSegundo parágrafo, também completo."
    out, info = dedupe_and_trim(text)
    assert info == {"removed_paragraphs": 0, "trimmed": False}
    assert out == text
