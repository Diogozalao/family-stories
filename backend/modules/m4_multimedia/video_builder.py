"""
Montagem do vídeo documentário familiar.

Pipeline:
1. Efeito Ken Burns em cada fotografia (zoom lento)
2. Sincronização com narração TTS
3. Títulos em sobreposição (PIL — sem dependência ImageMagick)
4. Mistura de música de fundo (opcional)
5. Exportação MP4 H.264
"""

import structlog
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

log = structlog.get_logger()

TARGET_W = 1280
TARGET_H = 720
FPS      = 24

# Fontes por ordem de preferência (Linux)
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
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _scale_image(img: Image.Image, scale_factor: float = 1.2) -> np.ndarray:
    """Escala a imagem para TARGET com margem para zoom."""
    scale = max(TARGET_W / img.width, TARGET_H / img.height) * scale_factor
    new_w = int(img.width * scale)
    new_h = int(img.height * scale)
    return np.array(img.resize((new_w, new_h), Image.BILINEAR))


def _make_ken_burns_clip(image_path: Path, duration: float, zoom_in: bool = True):
    """
    Cria clip com efeito Ken Burns (zoom lento).
    zoom_in=True  → começa grande, termina no alvo (zoom out visual)
    zoom_in=False → começa no alvo, termina grande (zoom in visual)
    """
    from moviepy.editor import VideoClip

    img = Image.open(image_path).convert("RGB")
    arr = _scale_image(img, scale_factor=1.25)
    h, w = arr.shape[:2]

    start_factor = 1.18 if zoom_in else 1.0
    end_factor   = 1.0  if zoom_in else 1.18

    def make_frame(t: float) -> np.ndarray:
        p  = t / max(duration, 0.001)
        f  = start_factor + (end_factor - start_factor) * p
        cw = min(int(TARGET_W * f), w)
        ch = min(int(TARGET_H * f), h)
        x  = (w - cw) // 2
        y  = (h - ch) // 2
        crop = arr[y:y + ch, x:x + cw]
        return np.array(Image.fromarray(crop).resize((TARGET_W, TARGET_H), Image.BILINEAR))

    clip = VideoClip(make_frame, duration=duration)
    clip.fps = FPS
    return clip


def _make_title_card(title: str, duration: float = 4.0):
    """Cria cartão de título com gradiente e tipografia."""
    from moviepy.editor import VideoClip

    # Fundo com gradiente escuro
    arr_base = np.zeros((TARGET_H, TARGET_W, 3), dtype=np.uint8)
    for y in range(TARGET_H):
        shade = int(10 + 35 * y / TARGET_H)
        arr_base[y] = [shade, shade, int(shade * 1.5)]

    font_title = _load_font(FONT_PATHS_SERIF, 58)
    font_sub   = _load_font(FONT_PATHS_SERIF, 30)

    img = Image.fromarray(arr_base)
    draw = ImageDraw.Draw(img)

    # Título
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw = bbox[2] - bbox[0]
    tx = max(40, (TARGET_W - tw) // 2)
    ty = TARGET_H // 2 - 60
    draw.text((tx + 2, ty + 2), title, fill=(0, 0, 0), font=font_title)
    draw.text((tx, ty), title, fill=(240, 220, 160), font=font_title)

    # Subtítulo
    sub = "Histórias Familiares"
    bbox2 = draw.textbbox((0, 0), sub, font=font_sub)
    sx = (TARGET_W - (bbox2[2] - bbox2[0])) // 2
    draw.text((sx, ty + 80), sub, fill=(170, 150, 100), font=font_sub)

    # Linha decorativa
    lx = (TARGET_W - 200) // 2
    draw.line([(lx, ty + 120), (lx + 200, ty + 120)], fill=(200, 180, 100), width=2)

    static = np.array(img)

    def make_frame(t: float) -> np.ndarray:
        # Fade in nos primeiros 0.8s
        if t < 0.8:
            alpha = t / 0.8
            return (static * alpha).astype(np.uint8)
        return static

    clip = VideoClip(make_frame, duration=duration)
    clip.fps = FPS
    return clip


def _add_caption(base_clip, caption_text: str):
    """Adiciona legenda no fundo do clip usando PIL + CompositeVideoClip."""
    if not caption_text:
        return base_clip

    from moviepy.editor import ImageClip, CompositeVideoClip

    bar  = Image.new("RGBA", (TARGET_W, 50), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bar)
    font = _load_font(FONT_PATHS_SANS, 22)

    # Barra semi-transparente
    draw.rectangle([(0, 0), (TARGET_W, 50)], fill=(0, 0, 0, 160))
    draw.text((16, 12), caption_text, fill=(240, 230, 180), font=font)

    caption_arr = np.array(bar.convert("RGB"))
    caption_clip = (
        ImageClip(caption_arr, duration=base_clip.duration)
        .set_position(("left", TARGET_H - 50))
    )
    return CompositeVideoClip([base_clip, caption_clip], size=(TARGET_W, TARGET_H))


def build_slideshow(
    photo_paths:           list[Path],
    audio_path:            Path,
    output_path:           Path,
    title:                 str,
    captions:              list[str] | None = None,
    background_music_path: Path | None = None,
) -> Path:
    """
    Monta o documentário familiar completo.

    Fluxo:
        cartão título → fotos com Ken Burns + legendas → narração → exporta MP4
    """
    from moviepy.editor import (
        AudioFileClip, concatenate_videoclips, ColorClip,
        concatenate_audioclips,
    )
    from moviepy.audio.AudioClip import AudioClip

    if not photo_paths:
        raise ValueError("Sem fotografias para criar o documentário.")

    narration      = AudioFileClip(str(audio_path))
    total_audio    = narration.duration
    title_duration = 4.0
    photo_duration = max(6.0, (total_audio - title_duration) / len(photo_paths))

    log.info("m4_building",
        photos=len(photo_paths),
        total_audio=round(total_audio, 1),
        photo_duration=round(photo_duration, 1),
    )

    # ── Clips de imagem ──────────────────────────────────────────────────────
    clips = [_make_title_card(title, title_duration)]

    for i, path in enumerate(photo_paths):
        try:
            clip = _make_ken_burns_clip(path, photo_duration, zoom_in=(i % 2 == 0))
            caption = (captions[i] if captions and i < len(captions) else None)
            clip = _add_caption(clip, caption)
            clips.append(clip)
        except Exception as e:
            log.warning("m4_photo_error", photo=str(path), error=str(e))
            clips.append(ColorClip((TARGET_W, TARGET_H), color=[10, 10, 10], duration=photo_duration))

    video = concatenate_videoclips(clips, method="compose")

    # ── Áudio ────────────────────────────────────────────────────────────────
    # Silêncio durante o cartão de título
    silence_title = AudioClip(lambda t: [0.0, 0.0], duration=title_duration, fps=44100)
    full_narration = concatenate_audioclips([silence_title, narration])

    # Ajusta comprimento se necessário
    if full_narration.duration < video.duration:
        extra = video.duration - full_narration.duration
        silence_end = AudioClip(lambda t: [0.0, 0.0], duration=extra, fps=44100)
        full_narration = concatenate_audioclips([full_narration, silence_end])
    else:
        full_narration = full_narration.subclip(0, video.duration)

    # Mistura com música de fundo
    if background_music_path and background_music_path.exists():
        try:
            music    = AudioFileClip(str(background_music_path))
            loops    = int(video.duration / music.duration) + 2
            music_l  = concatenate_audioclips([music] * loops).subclip(0, video.duration)
            music_l  = music_l.volumex(0.12)

            from moviepy.audio.AudioClip import CompositeAudioClip
            final_audio = CompositeAudioClip([full_narration, music_l])
        except Exception as e:
            log.warning("m4_music_skip", error=str(e))
            final_audio = full_narration
    else:
        final_audio = full_narration

    video = video.set_audio(final_audio)

    # ── Exportação ───────────────────────────────────────────────────────────
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
        preset="ultrafast",
        ffmpeg_params=["-crf", "28"],
    )

    narration.close()
    video.close()

    size_mb = round(output_path.stat().st_size / 1024 / 1024, 2)
    log.info("m4_complete", output=str(output_path), size_mb=size_mb)
    return output_path
