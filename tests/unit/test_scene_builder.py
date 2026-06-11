"""Unit tests for the scene segmentation that powers synced documentaries."""

from datetime import datetime
from types import SimpleNamespace

import pytest

from backend.modules.m3_narrative.scene_builder import (
    build_scenes,
    split_paragraphs,
)


def _media(id, *, desc=None, tags=None, setting=None, hint=None,
           ocr=None, place=None, date=None):
    return SimpleNamespace(
        id=id, ai_description=desc, ai_tags=tags, ai_setting=setting,
        ai_narrative_hint=hint, ocr_text=ocr, location_name=place,
        date_taken=date,
    )


def test_split_paragraphs_handles_blank_and_single_newlines():
    text = "Primeiro parágrafo.\n\nSegundo.\nTerceiro."
    assert split_paragraphs(text) == ["Primeiro parágrafo.", "Segundo.", "Terceiro."]


def test_split_paragraphs_empty():
    assert split_paragraphs("") == []
    assert split_paragraphs("   \n  ") == []


def test_build_scenes_matches_photos_to_relevant_paragraph():
    narrative = (
        "O casamento na praia foi inesquecível, com areia dourada.\n\n"
        "Mais tarde, o comboio levou-os para a montanha coberta de neve."
    )
    praia = _media(1, desc="praia areia casamento celebração")
    neve  = _media(2, desc="montanha neve comboio viagem")

    scenes = build_scenes(narrative, [praia, neve])

    assert len(scenes) == 2
    assert scenes[0]["photo_ids"] == [1]   # beach photo -> beach paragraph
    assert scenes[1]["photo_ids"] == [2]   # mountain photo -> mountain paragraph
    # Every photo is used exactly once.
    used = [pid for s in scenes for pid in s["photo_ids"]]
    assert sorted(used) == [1, 2]


def test_build_scenes_no_media_yields_empty_photo_lists():
    narrative = "Um parágrafo.\n\nOutro parágrafo."
    scenes = build_scenes(narrative, [])
    assert len(scenes) == 2
    assert all(s["photo_ids"] == [] for s in scenes)


def test_build_scenes_distributes_unscored_photos_without_empty_scene():
    # Photos with no textual fingerprint cannot be matched lexically; they
    # must still be spread so no scene is left without a photo.
    narrative = "Parágrafo um.\n\nParágrafo dois."
    blanks = [_media(10), _media(11)]
    scenes = build_scenes(narrative, blanks)
    assert len(scenes) == 2
    assert all(len(s["photo_ids"]) >= 1 for s in scenes)
    used = sorted(pid for s in scenes for pid in s["photo_ids"])
    assert used == [10, 11]


def test_build_scenes_caption_from_date_and_setting():
    narrative = "Apenas um parágrafo sobre a quinta."
    m = _media(5, desc="quinta campo", setting="Quinta da Avó",
               date=datetime(1975, 6, 1))
    scenes = build_scenes(narrative, [m])
    assert scenes[0]["caption"] == "01/06/1975 · Quinta da Avó"


def test_plan_scene_durations_respects_floor_and_proportion():
    from backend.modules.m4_multimedia.video_builder import (
        CROSSFADE_SECONDS,
        MIN_SCENE_PHOTO_DURATION,
        plan_scene_durations,
    )
    durs = plan_scene_durations([10.0, 1.0], [2, 2])
    # Scene 0: 10/2 + crossfade compensation, above the floor.
    assert durs[0] == pytest.approx(5.0 + CROSSFADE_SECONDS)
    # Scene 1: 1/2 + crossfade would be below the floor -> clamped.
    assert durs[1] == pytest.approx(MIN_SCENE_PHOTO_DURATION)
