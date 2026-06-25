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


def _make_title_card(title: str, duration: float = TITLE_DURATION):
    """Opening title card: dark gradient, serif title, subtitle and rule."""
    from moviepy.editor import VideoClip

    background = np.zeros((TARGET_H, TARGET_W, 3), dtype=np.uint8)
    for y in range(TARGET_H):
        shade = int(12 + 32 * y / TARGET_H)
        background[y] = [shade, shade, int(shade * 1.4)]

    font_title = _load_font(FONT_PATHS_SERIF, 58)
    font_sub   = _load_font(FONT_PATHS_SERIF, 30)

    image = Image.fromarray(background)
    draw  = ImageDraw.Draw(image)

    title_bbox = draw.textbbox((0, 0), title, font=font_title)
    title_w = title_bbox[2] - title_bbox[0]
    title_x = max(40, (TARGET_W - title_w) // 2)
    title_y = TARGET_H // 2 - 60
    # Drop shadow + foreground for readability.
    draw.text((title_x + 2, title_y + 2), title, fill=(0, 0, 0), font=font_title)
    draw.text((title_x, title_y), title, fill=(240, 220, 160), font=font_title)

    subtitle = "Histórias Familiares"
    sub_bbox = draw.textbbox((0, 0), subtitle, font=font_sub)
    sub_x = (TARGET_W - (sub_bbox[2] - sub_bbox[0])) // 2
    draw.text((sub_x, title_y + 80), subtitle, fill=(170, 150, 100), font=font_sub)

    rule_x = (TARGET_W - 200) // 2
    draw.line([(rule_x, title_y + 120), (rule_x + 200, title_y + 120)],
              fill=(200, 180, 100), width=2)

    static = np.array(image)

    def make_frame(t: float) -> np.ndarray:
        # Fade in for the first 0.8s, fade out in the last 0.8s.
        alpha = 1.0
        if t < 0.8:
            alpha = t / 0.8
        elif t > duration - 0.8:
            alpha = max(0.0, (duration - t) / 0.8)
        return (static * alpha).astype(np.uint8)

    clip = VideoClip(make_frame, duration=duration)
    clip.fps = FPS
    return clip


def _make_end_card(title: str, duration: float = END_CARD_DURATION):
    """Closing card — same look as the title card, with a gentle "Fim".

    Gives the documentary a proper ending instead of just fading on the last
    photo. Plays over silence (the narration track is padded to the video
    length), and the global end-fade darkens it on the way out.
    """
    from moviepy.editor import VideoClip

    background = np.zeros((TARGET_H, TARGET_W, 3), dtype=np.uint8)
    for y in range(TARGET_H):
        shade = int(12 + 32 * y / TARGET_H)
        background[y] = [shade, shade, int(shade * 1.4)]

    font_main = _load_font(FONT_PATHS_SERIF, 52)
    font_sub  = _load_font(FONT_PATHS_SERIF, 28)

    image = Image.fromarray(background)
    draw  = ImageDraw.Draw(image)

    main = "Fim"
    mb = draw.textbbox((0, 0), main, font=font_main)
    mx = (TARGET_W - (mb[2] - mb[0])) // 2
    my = TARGET_H // 2 - 50
    draw.text((mx + 2, my + 2), main, fill=(0, 0, 0), font=font_main)
    draw.text((mx, my), main, fill=(240, 220, 160), font=font_main)

    rule_x = (TARGET_W - 160) // 2
    draw.line([(rule_x, my + 70), (rule_x + 160, my + 70)], fill=(200, 180, 100), width=2)

    if title:
        sb = draw.textbbox((0, 0), title, font=font_sub)
        sx = (TARGET_W - (sb[2] - sb[0])) // 2
        draw.text((sx, my + 86), title, fill=(170, 150, 100), font=font_sub)

    static = np.array(image)

    def make_frame(t: float) -> np.ndarray:
        alpha = 1.0
        if t < 0.8:                      # fade in; the global end-fade handles the out
            alpha = t / 0.8
        return (static * alpha).astype(np.uint8)

    clip = VideoClip(make_frame, duration=duration)
    clip.fps = FPS
    return clip


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

    for index, path in enumerate(photo_paths):
        try:
            base = _make_ken_burns_clip(path, photo_duration, zoom_in=(index % 2 == 0))
            caption = captions[index] if captions and index < len(captions) else None
            clips.append(_add_caption(base, caption))
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
        caption = scene.get("caption")
        for p_index, photo in enumerate(scene["photo_paths"]):
            try:
                base = _make_ken_burns_clip(photo, per, zoom_in=(p_index % 2 == 0))
                clips.append(_add_caption(base, caption))
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
