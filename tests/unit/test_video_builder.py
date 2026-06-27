"""Unit tests for the M4 video builder helpers.

We avoid the full MoviePy render here — that's covered by the smoke
test. The pieces tested below are the pure-PIL routines that
determine whether photos are displayed correctly.
"""

import io

from PIL import Image

from backend.modules.m4_multimedia.video_builder import (
    TARGET_H,
    TARGET_W,
    _fit_to_frame,
    _load_font,
    FONT_PATHS_SANS,
)


def _solid_image(size: tuple[int, int], color=(10, 120, 200)) -> Image.Image:
    return Image.new("RGB", size, color)


def test_fit_to_frame_returns_target_dimensions_for_portrait():
    img = _solid_image((600, 1200))  # portrait — needs pillarbox.
    out = _fit_to_frame(img)
    assert out.size == (TARGET_W, TARGET_H)
    assert out.mode == "RGB"


def test_fit_to_frame_returns_target_dimensions_for_landscape():
    img = _solid_image((4000, 3000))  # oversized landscape.
    out = _fit_to_frame(img)
    assert out.size == (TARGET_W, TARGET_H)


def test_fit_to_frame_does_not_crop_foreground():
    # Paint a red BLOCK in every corner on a blue canvas; after fitting, red
    # must still be present (i.e. none of the photo was cropped away). Blocks
    # (not single pixels) survive the resize at any target resolution.
    img = Image.new("RGB", (400, 800), (0, 0, 255))
    b = 30
    for x0, y0 in [(0, 0), (400 - b, 0), (0, 800 - b), (400 - b, 800 - b)]:
        for x in range(x0, x0 + b):
            for y in range(y0, y0 + b):
                img.putpixel((x, y), (255, 0, 0))

    out = _fit_to_frame(img)
    red_pixels = sum(
        1
        for px in out.getdata()
        if px[0] > 200 and px[1] < 80 and px[2] < 80
    )
    assert red_pixels >= 4  # The corner blocks must survive the resize.


def test_fit_to_frame_preserves_aspect_ratio_check():
    # A 2:1 image fitted into 16:9 must keep full width and leave vertical bars.
    img = Image.new("RGB", (2000, 1000), (255, 255, 255))
    out = _fit_to_frame(img)
    # Top-left pixel is part of the blurred/darkened background, not white.
    top_left = out.getpixel((0, 0))
    center   = out.getpixel((TARGET_W // 2, TARGET_H // 2))
    assert center == (255, 255, 255)
    assert top_left != (255, 255, 255)


def test_load_font_returns_usable_font():
    font = _load_font(FONT_PATHS_SANS, 24)
    # PIL fonts always expose getbbox/getmask — cheap smoke check.
    assert hasattr(font, "getmask")
