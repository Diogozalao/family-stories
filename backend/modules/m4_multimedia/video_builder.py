"""Family documentary video assembly.

Pipeline:
    1. Fit each photo to a 1280x720 frame (letterbox + blurred background
       fill) so photos are never cropped nor stretched.
    2. Apply a subtle Ken Burns motion — zoom in/out plus a directional
       pan picked per clip so two consecutive photos never move the same
       way.
    3. Crossfade transitions between clips for smooth flow.
    4. Optional title card, lower-third captions and background music.
    5. Final fade-to-black so the documentary closes cleanly instead of
       cutting off mid-frame.
    6. Export as H.264 MP4.
"""

import math
import random
from pathlib import Path

import numpy as np
import structlog
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from backend.core.config import settings

log = structlog.get_logger()

# Frame size / fps are env-overridable so the render can be made lighter on a
# memory-constrained host. Render's free tier (512MB) runs out of memory at
# 720p; set VIDEO_WIDTH=854, VIDEO_HEIGHT=480, VIDEO_FPS=20 (or lower) there to
# cut peak RAM and render time. Local dev keeps full 720p24 by default.
TARGET_W = settings.VIDEO_WIDTH
TARGET_H = settings.VIDEO_HEIGHT
FPS      = settings.VIDEO_FPS

# Per-clip motion & transition timing.
KEN_BURNS_ZOOM     = 1.06   # Max zoom at the end of motion (only in "kenburns" mode).
KEN_BURNS_PAN_FRAC = 0.06   # Max pan as fraction of frame (only in "kenburns" mode).
GENTLE_ZOOM        = 1.035  # Barely-perceptible slow zoom for "gentle" mode (no pan).
# Per-photo motion mode — "none" (still), "gentle", or "kenburns". See config.
MOTION             = (getattr(settings, "VIDEO_MOTION", "none") or "none").lower()
CROSSFADE_SECONDS  = 1.6    # Slow, gentle dissolve between photos — the main source
                            # of "life" now that photos are still by default.
TITLE_DURATION     = 4.0    # Length of the opening title card.
END_FADE_SECONDS   = 1.5    # Fade-to-black before the last frame.
END_CARD_DURATION  = 3.5    # Length of the closing "Fim" card.
MIN_PHOTO_DURATION = 5.5    # Floor per photo, even for long slideshows.

# Font lookup (Linux). Falls back to PIL default if none are present.
FONT_PATHS_SERIF = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
]
FONT_PATHS_SANS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
]


def _load_font(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    for candidate in paths:
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _fit_to_frame(img: Image.Image) -> Image.Image:
    """Return a TARGET_W x TARGET_H RGB image containing the whole photo.

    The photo is resized to fit entirely inside the frame preserving its
    aspect ratio (no cropping). Empty areas are filled with a heavily blurred
    and darkened copy of the same photo, giving a cinematic backdrop.
    """
    img = img.convert("RGB")

    # Foreground: scaled down so the entire image is visible.
    fg_scale = min(TARGET_W / img.width, TARGET_H / img.height)
    fg_w = max(1, int(img.width  * fg_scale))
    fg_h = max(1, int(img.height * fg_scale))
    foreground = img.resize((fg_w, fg_h), Image.LANCZOS)

    # Background: scaled up to cover the frame, blurred, darkened.
    bg_scale = max(TARGET_W / img.width, TARGET_H / img.height) * 1.05
    bg_w = int(img.width  * bg_scale)
    bg_h = int(img.height * bg_scale)
    background = img.resize((bg_w, bg_h), Image.BILINEAR)
    left = (bg_w - TARGET_W) // 2
    top  = (bg_h - TARGET_H) // 2
    background = background.crop((left, top, left + TARGET_W, top + TARGET_H))
    background = background.filter(ImageFilter.GaussianBlur(radius=28))
    background = Image.eval(background, lambda v: int(v * 0.45))

    # Composite foreground centered on top of the background.
    canvas = background.copy()
    off_x = (TARGET_W - fg_w) // 2
    off_y = (TARGET_H - fg_h) // 2
    canvas.paste(foreground, (off_x, off_y))
    return canvas


def _make_ken_burns_clip(
    image_path: Path,
    duration:   float,
    zoom_in:    bool = True,
    pan_angle:  float | None = None,
):
    """Build a per-photo clip from the fitted frame.

    Motion is controlled by ``VIDEO_MOTION`` (config):
      * ``"none"``     → a perfectly still photo (clean look; also the
        fastest to render — no per-frame transform). This is the default.
      * ``"gentle"``   → a barely-perceptible slow zoom, no panning.
      * ``"kenburns"`` → the classic zoom + directional pan.

    The fitted frame already contains the whole photo (letterboxed over a
    blurred backdrop), so any zoom operates on the composed canvas.
    """
    from moviepy.editor import ImageClip, VideoClip

    fitted = _fit_to_frame(Image.open(image_path))
    base = np.array(fitted)

    # ── Clean / still ─────────────────────────────────────────────────
    # A static image — the documentary's life comes from the smooth
    # crossfades between photos, not from constant motion.
    if MOTION == "none":
        clip = ImageClip(base).set_duration(duration)
        clip.fps = FPS
        return clip

    # ── Gentle: subtle slow zoom, no pan ──────────────────────────────
    if MOTION == "gentle":
        start_zoom, end_zoom = 1.0, GENTLE_ZOOM
        pan_dx = pan_dy = 0.0
    # ── Ken Burns: zoom + directional pan ─────────────────────────────
    else:
        start_zoom = 1.0             if zoom_in else KEN_BURNS_ZOOM
        end_zoom   = KEN_BURNS_ZOOM  if zoom_in else 1.0
        # Pan vector — deterministic from the file path so the same photo
        # always animates identically (useful for cache + tests).
        if pan_angle is None:
            rnd = random.Random(str(image_path))
            pan_angle = rnd.uniform(0.0, 2 * math.pi)
        pan_dx = math.cos(pan_angle) * KEN_BURNS_PAN_FRAC * TARGET_W
        pan_dy = math.sin(pan_angle) * KEN_BURNS_PAN_FRAC * TARGET_H

    def make_frame(t: float) -> np.ndarray:
        progress = min(max(t / max(duration, 0.001), 0.0), 1.0)
        # Smoothstep easing: slow at start and end, avoids mechanical feel.
        eased = progress * progress * (3.0 - 2.0 * progress)
        zoom  = start_zoom + (end_zoom - start_zoom) * eased

        crop_w = int(TARGET_W / zoom)
        crop_h = int(TARGET_H / zoom)
        # Pan from (-pan_dx/2, -pan_dy/2) to (+pan_dx/2, +pan_dy/2) over the
        # eased timeline so the camera glides instead of jumping.
        offset_x = int((eased - 0.5) * pan_dx)
        offset_y = int((eased - 0.5) * pan_dy)

        # Clamp the crop window so it never spills outside the canvas.
        x = max(0, min(TARGET_W - crop_w, (TARGET_W - crop_w) // 2 + offset_x))
        y = max(0, min(TARGET_H - crop_h, (TARGET_H - crop_h) // 2 + offset_y))
        window = base[y:y + crop_h, x:x + crop_w]
        return np.array(Image.fromarray(window).resize((TARGET_W, TARGET_H), Image.BILINEAR))

    clip = VideoClip(make_frame, duration=duration)
    clip.fps = FPS
    return clip


# Card palette — warm gold over a deep, vignetted backdrop.
GOLD      = (243, 226, 173)
GOLD_SOFT = (190, 168, 116)


def _elegant_backdrop() -> np.ndarray:
    """Deep, vignetted backdrop with a warm centre glow — the cinematic base
    shared by the title and end cards (far classier than a flat gradient)."""
    yy, xx = np.mgrid[0:TARGET_H, 0:TARGET_W].astype(np.float32)
    cx, cy = TARGET_W / 2.0, TARGET_H / 2.0
    dist = np.sqrt(((xx - cx) / cx) ** 2 + ((yy - cy) / cy) ** 2) / 1.4142
    dist = np.clip(dist, 0.0, 1.0)[..., None]
    centre = np.array([26, 23, 33], np.float32)    # deep charcoal-indigo
    edge   = np.array([6, 6, 9],  np.float32)       # near-black corners
    bg = centre * (1.0 - dist) + edge * dist
    glow = np.clip(1.0 - dist * 1.25, 0.0, 1.0)     # warm amber lift, centre
    bg = bg + glow * np.array([22, 16, 6], np.float32)
    return np.clip(bg, 0, 255).astype(np.uint8)


def _fit_serif(draw, text: str, max_w: int, start: int, floor: int):
    """Largest serif size that keeps ``text`` within ``max_w`` so long titles
    (e.g. 'Um fim de semana na Covilhã') never run off the frame."""
    size = start
    while size > floor:
        font = _load_font(FONT_PATHS_SERIF, size)
        bb = draw.textbbox((0, 0), text, font=font)
        if bb[2] - bb[0] <= max_w:
            return font
        size -= 3
    return _load_font(FONT_PATHS_SERIF, floor)


def _draw_center(draw, text: str, font, y: int, fill, shadow=(0, 0, 0)) -> None:
    """Draw ``text`` horizontally centred at vertical ``y``."""
    bb = draw.textbbox((0, 0), text, font=font)
    x = (TARGET_W - (bb[2] - bb[0])) // 2 - bb[0]
    if shadow:
        draw.text((x + 2, y + 2), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)


def _draw_ornament(draw, cy: int, half: int = 150, color=GOLD_SOFT) -> None:
    """A thin rule — small diamond — thin rule divider."""
    mid, gap = TARGET_W // 2, 16
    draw.line([(mid - half, cy), (mid - gap, cy)], fill=color, width=2)
    draw.line([(mid + gap, cy), (mid + half, cy)], fill=color, width=2)
    d = 5
    draw.polygon([(mid, cy - d), (mid + d, cy), (mid, cy + d), (mid - d, cy)], fill=color)


def _fade_clip(static: np.ndarray, duration: float, fade_out: bool):
    """Wrap a still card image in a gently-eased fade-in (and optional out)."""
    from moviepy.editor import VideoClip
    base = static.astype(np.float32)
    fade = min(1.0, duration / 4)

    def make_frame(t: float) -> np.ndarray:
        a = 1.0
        if t < fade:
            a = t / fade
        elif fade_out and t > duration - fade:
            a = max(0.0, (duration - t) / fade)
        a = a * a * (3.0 - 2.0 * a)     # smoothstep — gentle, not linear
        return (base * a).astype(np.uint8)

    clip = VideoClip(make_frame, duration=duration)
    clip.fps = FPS
    return clip


def _make_title_card(title: str, duration: float = TITLE_DURATION):
    """Opening title card — vignetted backdrop, auto-fitted gold serif title,
    an ornamental divider and a tracked subtitle. Gently fades in and out."""
    image = Image.fromarray(_elegant_backdrop())
    draw  = ImageDraw.Draw(image)
    cy    = TARGET_H // 2

    font_title = _fit_serif(draw, title, TARGET_W - 160, 74, 34)
    _draw_center(draw, title, font_title, cy - 104, GOLD)
    _draw_ornament(draw, cy + 2)
    _draw_center(draw, "H I S T Ó R I A S   F A M I L I A R E S",
                 _load_font(FONT_PATHS_SERIF, 23), cy + 24, GOLD_SOFT, shadow=None)

    return _fade_clip(np.array(image), duration, fade_out=True)


def _make_end_card(title: str, duration: float = END_CARD_DURATION):
    """Closing card — the same elegant backdrop with a gentle "Fim", the story
    title and a small wordmark. The global end-fade darkens it on the way out."""
    image = Image.fromarray(_elegant_backdrop())
    draw  = ImageDraw.Draw(image)
    cy    = TARGET_H // 2

    _draw_center(draw, "Fim", _load_font(FONT_PATHS_SERIF, 58), cy - 78, GOLD)
    _draw_ornament(draw, cy + 4, half=110)
    if title:
        font_sub = _fit_serif(draw, title, TARGET_W - 200, 30, 18)
        _draw_center(draw, title, font_sub, cy + 26, GOLD_SOFT, shadow=None)
    _draw_center(draw, "Living Memory", _load_font(FONT_PATHS_SERIF, 18),
                 TARGET_H - 72, (122, 112, 92), shadow=None)

    # No fade-out here — the global end-fade handles the close.
    return _fade_clip(np.array(image), duration, fade_out=False)


def _add_caption(base_clip, caption_text: str):
    """Draw a translucent lower-third bar with caption text over the clip."""
    if not caption_text:
        return base_clip

    from moviepy.editor import CompositeVideoClip, ImageClip

    bar_h = 58
    bar = Image.new("RGBA", (TARGET_W, bar_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bar)
    font = _load_font(FONT_PATHS_SANS, 22)

    draw.rectangle([(0, 0), (TARGET_W, bar_h)], fill=(0, 0, 0, 170))
    # Light beige text aligned with a small left padding.
    draw.text((24, 16), caption_text, fill=(240, 230, 180), font=font)

    caption_rgb = np.array(bar.convert("RGB"))
    caption_clip = (
        ImageClip(caption_rgb, duration=base_clip.duration)
        .set_position(("left", TARGET_H - bar_h))
    )
    return CompositeVideoClip([base_clip, caption_clip], size=(TARGET_W, TARGET_H))


def _wrap_text(draw, text: str, font, max_w: int) -> list[str]:
    """Word-wrap ``text`` so each line fits within ``max_w`` pixels."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if not cur or draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _split_n(text: str, n: int) -> list[str]:
    """Split ``text`` into exactly ``n`` contiguous, roughly-equal chunks, so a
    scene's narration flows across its photos (one slice spoken per photo)."""
    words = (text or "").split()
    if not words:
        return [""] * max(n, 1)
    if n <= 1:
        return [" ".join(words)]
    if len(words) <= n:
        return [words[i] if i < len(words) else "" for i in range(n)]
    per = len(words) / n
    return [" ".join(words[round(i * per):round((i + 1) * per)]) for i in range(n)]


SUBTITLE_MAX_WORDS = 8     # words per on-screen subtitle segment (≈ one line)
SUBTITLE_MIN_SECS  = 1.4   # never flash a segment faster than this


def _segment_text(text: str, max_words: int = SUBTITLE_MAX_WORDS) -> list[str]:
    """Break ``text`` into short, readable subtitle segments (≈ one line each),
    preferring sentence/clause boundaries so lines don't split awkwardly."""
    import re
    out: list[str] = []
    # Split on clause boundaries first, then pack words up to ``max_words``.
    for clause in re.split(r"(?<=[.!?,;:…])\s+", text.strip()):
        words = clause.split()
        for i in range(0, len(words), max_words):
            seg = " ".join(words[i:i + max_words]).strip()
            if seg:
                out.append(seg)
    return out


def _render_subtitle_overlay(text: str) -> tuple[np.ndarray, np.ndarray]:
    """Render one subtitle line as (rgb, alpha) arrays — text + shadow over a
    soft bottom gradient so it stays readable on any photo."""
    font  = _load_font(FONT_PATHS_SANS, 30)
    max_w = int(TARGET_W * 0.84)
    overlay = Image.new("RGBA", (TARGET_W, TARGET_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    lines = _wrap_text(draw, text.strip(), font, max_w)[:2]
    line_h  = font.size + 10
    block_h = line_h * len(lines)
    y0 = TARGET_H - 56 - block_h

    grad_h = block_h + 80
    grad = np.zeros((grad_h, TARGET_W, 4), np.uint8)
    grad[:, :, 3] = (165 * np.linspace(0, 1, grad_h)).astype(np.uint8)[:, None]
    overlay.alpha_composite(Image.fromarray(grad), (0, TARGET_H - grad_h))

    for i, line in enumerate(lines):
        w = draw.textlength(line, font=font)
        x = int((TARGET_W - w) / 2)
        y = y0 + i * line_h
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 215))   # shadow
        draw.text((x, y), line, font=font, fill=(248, 246, 240, 255))

    arr = np.array(overlay)
    return arr[:, :, :3], arr[:, :, 3] / 255.0


def _add_subtitle(base_clip, text: str):
    """Burn the narration in as subtitles that FLOW with the speech: the text
    is split into short segments, each shown for a slice of the clip
    proportional to its length (so reading pace ≈ speaking pace).

    Performance: each segment is pre-rendered ONCE and blended in a single
    ``make_frame`` (a NumPy alpha-composite). The old approach stacked one
    ``CompositeVideoClip`` layer per segment, which made long single-photo
    clips render for many minutes — this is dramatically faster.
    """
    if not text or not text.strip():
        return base_clip
    from moviepy.editor import VideoClip

    duration = base_clip.duration
    segments = _segment_text(text)
    if not segments:
        return base_clip

    # Don't let segments flash faster than the minimum readable time.
    max_segments = max(1, int(duration / SUBTITLE_MIN_SECS))
    if len(segments) > max_segments:
        per = len(segments) / max_segments
        segments = [" ".join(segments[round(i * per):round((i + 1) * per)])
                    for i in range(max_segments)]

    total = sum(len(s.split()) for s in segments) or 1
    timed: list[tuple] = []
    start = 0.0
    for i, seg in enumerate(segments):
        end = duration if i == len(segments) - 1 else start + duration * (len(seg.split()) / total)
        rgb, alpha = _render_subtitle_overlay(seg)
        timed.append((start, end, rgb.astype(np.float32), alpha[:, :, None].astype(np.float32)))
        start = end

    def make_frame(t: float) -> np.ndarray:
        frame = base_clip.get_frame(t)
        for s, e, rgb, a in timed:
            if s <= t < e:
                return (frame * (1.0 - a) + rgb * a).astype(np.uint8)
        return frame

    clip = VideoClip(make_frame, duration=duration)
    clip.fps = FPS
    return clip


def _concatenate_with_crossfade(clips: list, crossfade: float):
    """Concatenate clips with a smooth crossfade between them.

    The first clip plays fully; each following clip is overlapped by
    `crossfade` seconds and fades in over the same window. The total
    duration is shortened by crossfade * (n - 1).
    """
    from moviepy.editor import CompositeVideoClip

    if not clips:
        raise ValueError("No clips to concatenate.")
    if len(clips) == 1:
        return clips[0]

    composed = [clips[0]]
    running_start = clips[0].duration - crossfade
    for clip in clips[1:]:
        faded = clip.crossfadein(crossfade).set_start(running_start)
        composed.append(faded)
        running_start += clip.duration - crossfade

    total_duration = sum(c.duration for c in clips) - crossfade * (len(clips) - 1)
    final = CompositeVideoClip(composed, size=(TARGET_W, TARGET_H)).set_duration(total_duration)
    final.fps = FPS
    return final


def build_slideshow(
    photo_paths:           list[Path],
    audio_path:            Path,
    output_path:           Path,
    title:                 str,
    captions:              list[str] | None = None,
    background_music_path: Path | None = None,
) -> Path:
    """Assemble the full documentary from photos + narration.

    Order of events:
        title card -> fitted photos with Ken Burns + captions (crossfaded)
        -> narration track (padded to match video length) -> optional music
        -> H.264 MP4 on disk.
    """
    from moviepy.audio.AudioClip import AudioClip
    from moviepy.editor import AudioFileClip, ColorClip, concatenate_audioclips

    if not photo_paths:
        raise ValueError("No photos available to build the documentary.")

    narration   = AudioFileClip(str(audio_path))
    total_audio = narration.duration

    # Leave the title card with music-only, split narration across photos.
    photo_slots = len(photo_paths)
    remaining   = max(total_audio - TITLE_DURATION, photo_slots * MIN_PHOTO_DURATION)
    # Each crossfade shortens the timeline by CROSSFADE_SECONDS, so the
    # per-photo slot has to be inflated to keep the A/V length consistent.
    overlap_compensation = CROSSFADE_SECONDS * photo_slots / max(photo_slots, 1)
    photo_duration = max(MIN_PHOTO_DURATION, remaining / photo_slots + overlap_compensation)

    log.info(
        "m4_building",
        photos=photo_slots,
        total_audio=round(total_audio, 1),
        photo_duration=round(photo_duration, 1),
        crossfade=CROSSFADE_SECONDS,
    )

    clips = [_make_title_card(title, TITLE_DURATION)]

    # The slideshow fallback has no per-photo narration text to subtitle, so it
    # plays clean (no photo-description captions — the user didn't want those).
    for index, path in enumerate(photo_paths):
        try:
            clips.append(_make_ken_burns_clip(path, photo_duration, zoom_in=(index % 2 == 0)))
        except Exception as exc:
            log.warning("m4_photo_error", photo=str(path), error=str(exc))
            clips.append(ColorClip((TARGET_W, TARGET_H), color=[10, 10, 10],
                                   duration=photo_duration))

    video = _concatenate_with_crossfade(clips, CROSSFADE_SECONDS)

    # Close on a fade to black so the last frame doesn't hard-cut. The
    # ``fadeout`` MoviePy helper darkens the picture and (when present)
    # mixes the audio down to silence over the same window.
    fade_window = min(END_FADE_SECONDS, video.duration / 4)
    if fade_window > 0.2:
        video = video.fadeout(fade_window)

    # ── Audio track ──────────────────────────────────────────────────────
    # Silent lead-in while the title card plays, then narration. If the
    # narration ends before the visuals, pad with silence; if it's longer,
    # trim it to match so the file doesn't grow unexpectedly.
    lead_silence = AudioClip(lambda t: [0.0, 0.0], duration=TITLE_DURATION, fps=44100)
    narration_track = concatenate_audioclips([lead_silence, narration])

    if narration_track.duration < video.duration:
        tail = AudioClip(lambda t: [0.0, 0.0],
                         duration=video.duration - narration_track.duration,
                         fps=44100)
        narration_track = concatenate_audioclips([narration_track, tail])
    else:
        narration_track = narration_track.subclip(0, video.duration)

    if background_music_path and background_music_path.exists():
        try:
            music = AudioFileClip(str(background_music_path))
            loops = int(video.duration / music.duration) + 2
            music_track = concatenate_audioclips([music] * loops).subclip(0, video.duration)
            music_track = music_track.volumex(0.12)

            from moviepy.audio.AudioClip import CompositeAudioClip
            final_audio = CompositeAudioClip([narration_track, music_track])
        except Exception as exc:
            log.warning("m4_music_skip", error=str(exc))
            final_audio = narration_track
    else:
        final_audio = narration_track

    video = video.set_audio(final_audio)

    # ── Export ───────────────────────────────────────────────────────────
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_audio = output_path.with_suffix(".tmp.m4a")

    video.write_videofile(
        str(output_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=str(tmp_audio),
        remove_temp=True,
        logger=None,
        preset="veryfast",
        ffmpeg_params=["-crf", "23", "-pix_fmt", "yuv420p"],
    )

    narration.close()
    video.close()

    size_mb = round(output_path.stat().st_size / 1024 / 1024, 2)
    log.info("m4_complete", output=str(output_path), size_mb=size_mb)
    return output_path


# Slightly lower per-photo floor for scene mode: here the pacing is driven
# by each scene's narration, so we want to respect the audio rather than
# stretch every photo to the slideshow minimum.
MIN_SCENE_PHOTO_DURATION = 4.0   # Floor per photo in scene mode — 3.0 felt rushed against the 1.2s crossfade.


def plan_scene_durations(scene_audio_durations: list[float],
                         scene_photo_counts: list[int]) -> list[float]:
    """Per-photo on-screen duration for each scene (pure, unit-testable).

    Each scene's narration time is split across its photos, with a floor
    so individual photos never flash by. The crossfade overlap is added
    back per photo so the concatenated timeline stays close to the
    narration length. Returns one duration per scene (applied to every
    photo of that scene).
    """
    durations: list[float] = []
    for audio_dur, n_photos in zip(scene_audio_durations, scene_photo_counts):
        if n_photos <= 0:
            durations.append(0.0)
            continue
        per_photo = max(MIN_SCENE_PHOTO_DURATION,
                        audio_dur / n_photos + CROSSFADE_SECONDS)
        durations.append(per_photo)
    return durations


def build_documentary(
    scenes:                list[dict],
    output_path:           Path,
    title:                 str,
    background_music_path: Path | None = None,
    subtitles:             bool = True,
) -> Path:
    """Assemble a documentary that *syncs* each photo to its narration.

    ``scenes`` is an ordered list of already-prepared scene dicts:

        {"audio_path": Path, "photo_paths": [Path, ...], "caption": str|None}

    Each scene's photos are shown for (roughly) the duration of that
    scene's narration, so the viewer sees the photo being talked about.
    The narration track is the concatenation of the per-scene audio, in
    order, after a silent lead-in for the title card — which keeps audio
    and visuals aligned scene by scene instead of by a flat even split.
    """
    from moviepy.audio.AudioClip import AudioClip
    from moviepy.editor import AudioFileClip, ColorClip, concatenate_audioclips

    usable = [s for s in scenes if s.get("photo_paths") and s.get("audio_path")]
    if not usable:
        raise ValueError("No usable scenes (need photos + narration) to build the documentary.")

    scene_audios   = [AudioFileClip(str(s["audio_path"])) for s in usable]
    photo_counts   = [len(s["photo_paths"]) for s in usable]
    per_photo_durs = plan_scene_durations([a.duration for a in scene_audios], photo_counts)

    log.info("m4_building_scenes", scenes=len(usable),
             photos=sum(photo_counts),
             total_audio=round(sum(a.duration for a in scene_audios), 1))

    clips = [_make_title_card(title, TITLE_DURATION)]
    for s_index, scene in enumerate(usable):
        per = per_photo_durs[s_index]
        # Subtitles = the scene's narration, split across its photos so the
        # text on screen tracks what's being said (not the photo's description).
        subs = (_split_n(scene.get("text") or "", len(scene["photo_paths"]))
                if subtitles else None)
        for p_index, photo in enumerate(scene["photo_paths"]):
            try:
                base = _make_ken_burns_clip(photo, per, zoom_in=(p_index % 2 == 0))
                clips.append(_add_subtitle(base, subs[p_index]) if subs else base)
            except Exception as exc:
                log.warning("m4_scene_photo_error", photo=str(photo), error=str(exc))
                clips.append(ColorClip((TARGET_W, TARGET_H), color=[10, 10, 10], duration=per))

    clips.append(_make_end_card(title))

    video = _concatenate_with_crossfade(clips, CROSSFADE_SECONDS)

    fade_window = min(END_FADE_SECONDS, video.duration / 4)
    if fade_window > 0.2:
        video = video.fadeout(fade_window)

    # ── Audio: silent lead-in over the title, then the scene narrations ──
    lead_silence = AudioClip(lambda t: [0.0, 0.0], duration=TITLE_DURATION, fps=44100)
    narration_track = concatenate_audioclips([lead_silence, *scene_audios])

    if narration_track.duration < video.duration:
        tail = AudioClip(lambda t: [0.0, 0.0],
                         duration=video.duration - narration_track.duration, fps=44100)
        narration_track = concatenate_audioclips([narration_track, tail])
    else:
        narration_track = narration_track.subclip(0, video.duration)

    if background_music_path and background_music_path.exists():
        try:
            music = AudioFileClip(str(background_music_path))
            loops = int(video.duration / music.duration) + 2
            music_track = concatenate_audioclips([music] * loops).subclip(0, video.duration)
            music_track = music_track.volumex(0.12)
            from moviepy.audio.AudioClip import CompositeAudioClip
            final_audio = CompositeAudioClip([narration_track, music_track])
        except Exception as exc:
            log.warning("m4_music_skip", error=str(exc))
            final_audio = narration_track
    else:
        final_audio = narration_track

    video = video.set_audio(final_audio)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_audio = output_path.with_suffix(".tmp.m4a")
    video.write_videofile(
        str(output_path), fps=FPS, codec="libx264", audio_codec="aac",
        temp_audiofile=str(tmp_audio), remove_temp=True, logger=None,
        preset="veryfast", ffmpeg_params=["-crf", "23", "-pix_fmt", "yuv420p"],
    )

    for a in scene_audios:
        a.close()
    video.close()

    size_mb = round(output_path.stat().st_size / 1024 / 1024, 2)
    log.info("m4_complete_scenes", output=str(output_path), size_mb=size_mb)
    return output_path
