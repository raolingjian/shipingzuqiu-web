import os, random, math
import numpy as np
from moviepy import (
    VideoFileClip, TextClip, AudioFileClip,
    CompositeVideoClip, CompositeAudioClip, concatenate_audioclips, concatenate_videoclips,
    ImageClip
)
from moviepy.video.fx import FadeIn, FadeOut, Resize
from PIL import Image, ImageDraw, ImageFont

W = 1080
H = 1920
FONT = None
MEME_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "materials", "images", "memes")
EMOJI_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "materials", "images", "emoji")
MEME_INDEX_FILE = os.path.join(MEME_DIR, ".meme_index")


def _find_font():
    """自动检测可用的中文字体路径"""
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts", "msyh.ttc"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts", "NotoSansSC.ttf"),
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


SCENE_TAGS = [
    ("消防证|消防工程师|操作员|考证|报名", "考证热点", "#FF4500"),
    ("火灾|隐患|危险|爆炸|事故", "安全第一", "#FF0000"),
    ("逃生|自救|灭火|救援|疏散", "保命技能", "#FF8C00"),
    ("考试|通过|拿证|就业|高薪", "入行必看", "#00BFFF"),
]

def _ken_burns(clip, duration, zoom_ratio=0.06):
    start = 1.0
    end = 1.0 + zoom_ratio
    if random.random() > 0.5:
        zoom_clip = clip.with_effects([Resize(lambda t: start + (end - start) * t / duration)])
    else:
        zoom_clip = clip.with_effects([Resize(lambda t: end - (end - start) * t / duration)])
    return zoom_clip.with_position("center")

def _make_subtitle_bar(duration):
    bar = np.zeros((140, W, 3), dtype=np.uint8)
    return ImageClip(bar).with_duration(duration).with_position(("center", H * 0.82 - 70)).with_opacity(0.55)

def _make_progress(current, total, duration):
    return TextClip(
        font=FONT, text=f"· {current}/{total} ·", font_size=22,
        color="white", stroke_color="black", stroke_width=1,
    ).with_duration(duration).with_position((W - 110, 35))

def _pick_scene_tag(text):
    for pattern, tag, color in SCENE_TAGS:
        if any(word in text for word in pattern.split("|")):
            return tag, color
    return "消防科普", "#FF4500"

def _make_tag_chip(text, duration, bg_color="#FF4500"):
    chip = Image.new("RGBA", (250, 70), (0, 0, 0, 0))
    draw = ImageDraw.Draw(chip)
    draw.rounded_rectangle((0, 0, 250, 70), radius=28, fill=bg_color)
    return CompositeVideoClip(
        [
            ImageClip(np.array(chip)).with_duration(duration),
            TextClip(font=FONT, text=text, font_size=32, color="white", stroke_color="black", stroke_width=1)
            .with_duration(duration).with_position((35, 14)),
        ],
        size=(250, 70),
    ).with_position((52, 72))

def _make_info_card(text, duration, accent="#FF4500"):
    card_w, card_h = 760, 160
    img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, card_w, card_h), radius=28, fill=(10, 10, 10, 210))
    draw.rounded_rectangle((0, 0, 18, card_h), radius=8, fill=accent)
    return CompositeVideoClip(
        [
            ImageClip(np.array(img)).with_duration(duration),
            TextClip(font=FONT, text=text, font_size=54, color="white", stroke_color="black", stroke_width=2,
                     size=(card_w - 80, None), method="caption", text_align="left",
            ).with_duration(duration).with_position((42, 28)),
        ],
        size=(card_w, card_h),
    ).with_position((70, 168))

def _segment_durations(audio_files, expected_count):
    if len(audio_files) != expected_count:
        return []
    durations = []
    for path in audio_files:
        clip = AudioFileClip(path)
        try:
            durations.append(clip.duration)
        finally:
            clip.close()
    return durations

def _get_animated_text(text, duration, font_size=42, color="white", stroke_color="black", stroke_width=3):
    final_y = H * 0.82
    text_clip = TextClip(
        font=FONT, text=text, font_size=font_size,
        color=color, stroke_color=stroke_color, stroke_width=stroke_width,
        text_align="center", horizontal_align="center", vertical_align="center",
        method="label",
    ).with_duration(duration)
    text_clip = text_clip.with_position(lambda t: (
        "center",
        final_y + 60 * max(0, 1 - t / 0.3)
    ))
    return text_clip.with_effects([FadeIn(0.2)])

def _get_static_text(text, duration, font_size=42, color="white", stroke_color="black", stroke_width=3):
    return TextClip(
        font=FONT, text=text, font_size=font_size,
        color=color, stroke_color=stroke_color, stroke_width=stroke_width,
        text_align="center", horizontal_align="center", vertical_align="center",
        method="label",
    ).with_duration(duration).with_position(("center", H * 0.82))

def _pick_meme(used_set=None):
    meme_files = []
    if os.path.isdir(MEME_DIR):
        meme_files = sorted([f for f in os.listdir(MEME_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))])
    if not meme_files and os.path.isdir(EMOJI_DIR):
        meme_files = sorted([f for f in os.listdir(EMOJI_DIR) if f.endswith(".png")])
    if not meme_files:
        return None
    idx = 0
    try:
        if os.path.exists(MEME_INDEX_FILE):
            with open(MEME_INDEX_FILE, "r") as f:
                idx = int(f.read().strip())
    except Exception:
        idx = 0
    if idx >= len(meme_files):
        idx = 0
    chosen = meme_files[idx]
    idx += 1
    if idx >= len(meme_files):
        idx = 0
    try:
        with open(MEME_INDEX_FILE, "w") as f:
            f.write(str(idx))
    except Exception:
        pass
    if used_set is not None:
        used_set.add(chosen)
    return os.path.join(MEME_DIR if os.path.isdir(MEME_DIR) and os.path.exists(os.path.join(MEME_DIR, chosen)) else EMOJI_DIR, chosen)

def _make_fire_bg(duration):
    try:
        img = Image.new("RGB", (W, H))
        draw = ImageDraw.Draw(img)
        stripe_colors = [(180, 40, 30), (160, 35, 25)]
        for y in range(0, H, 6):
            color = stripe_colors[(y // 6) % 2]
            draw.rectangle([(0, y), (W, y + 6)], fill=color)
        cx, cy = W // 2, H // 2
        for r, col in [(300, (255, 200, 50, 30)), (200, (255, 150, 30, 20)), (120, (255, 100, 20, 15))]:
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            odraw = ImageDraw.Draw(overlay)
            odraw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=col)
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img)
        bg_clip = ImageClip(np.array(img)).with_duration(duration)
        meme_path = _pick_meme()
        if meme_path:
            try:
                meme_pil = Image.open(meme_path).convert("RGBA")
                scale = min(W * 0.35 / meme_pil.width, H * 0.22 / meme_pil.height)
                new_w = int(meme_pil.width * scale)
                new_h = int(meme_pil.height * scale)
                meme_pil = meme_pil.resize((new_w, new_h))
                meme_clip = ImageClip(np.array(meme_pil)).with_duration(duration).with_position(("center", "center"))
                return CompositeVideoClip([bg_clip, meme_clip], size=(W, H))
            except Exception:
                pass
        return bg_clip
    except Exception:
        colors = [(180, 40, 30), (200, 60, 40), (160, 35, 25)]
        color = random.choice(colors)
        arr = np.zeros((H, W, 3), dtype=np.uint8)
        arr[:, :] = color
        return ImageClip(arr).with_duration(duration)

_make_fallback_bg = _make_fire_bg

def _fit_video_to_vertical(video_path, duration):
    if not video_path or not os.path.exists(video_path):
        return _make_fire_bg(duration)
    try:
        clip = VideoFileClip(video_path)
        if clip.duration < 0.5:
            clip.close()
            return _make_fire_bg(duration)
        orig_w, orig_h = clip.w, clip.h
        bg = clip.resized(width=W)
        if bg.h < H:
            bg = clip.resized(height=H)
        try:
            bg = bg.with_effects([Resize(lambda t: 1.0)]).cropped(x_center=bg.w/2, y_center=bg.h/2, width=W, height=H)
        except Exception:
            bg = bg.resized((W, H))
        bg = bg.with_effects([FadeIn(0.0)])
        target_w = W
        target_h = int(orig_h * target_w / orig_w)
        if target_h > H:
            target_h = H
            target_w = int(orig_w * target_h / orig_h)
        fg = clip.resized((target_w, target_h))
        fg = fg.with_position("center")
        result = CompositeVideoClip([bg, fg], size=(W, H))
        if result.duration > duration:
            result = result.subclipped(0, duration)
        elif result.duration < duration:
            result = result.loop(duration=duration)
        return result
    except Exception as e:
        print(f"  [视频裁剪异常] {str(e)[:60]}")
        return _make_fire_bg(duration)

def compose_video(script_dict, audio_files, full_audio_path, font_path, output_path, bgm_config=None, title=None):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    global FONT
    FONT = font_path
    if not FONT or not os.path.exists(FONT):
        FONT = _find_font()
        if FONT:
            print(f"  [字体] 自动检测: {FONT}")
        else:
            print("  [字体] ⚠️ 未找到中文字体，字幕可能无法显示")

    scenes = script_dict.get("scenes", [])
    hook = script_dict.get("hook", "")
    outro = script_dict.get("outro", "")
    if not title:
        title = script_dict.get("title", "消防考证知识")

    if not audio_files or not os.path.exists(full_audio_path):
        raise FileNotFoundError("配音文件未生成")

    full_audio = AudioFileClip(full_audio_path)
    total_duration = full_audio.duration

    expected_segments = (1 if hook else 0) + len(scenes) + (1 if outro else 0)
    measured_durations = _segment_durations(audio_files, expected_segments)
    current_time = 0.0
    duration_cursor = 0

    if measured_durations:
        base_durations = measured_durations[:]
    else:
        base_durations = []
        if hook:
            base_durations.append(2.0)
        base_durations.extend([3.0] * len(scenes))
        if outro:
            base_durations.append(2.5)

    base_total = sum(base_durations) or total_duration
    duration_scale = total_duration / base_total
    base_durations = [d * duration_scale for d in base_durations]

    clips = []

    if hook:
        hook_duration = base_durations[duration_cursor]
        duration_cursor += 1
        hook_bg = _make_fire_bg(hook_duration)
        hook_bg = _ken_burns(hook_bg, hook_duration, zoom_ratio=0.09)

        title_text = TextClip(
            font=FONT, text=title, font_size=120,
            color="#FFD700", stroke_color="black", stroke_width=4,
            text_align="center", horizontal_align="center", vertical_align="center",
            method="label",
        ).with_duration(hook_duration).with_position(("center", H * 0.28))

        subtitle_text = TextClip(
            font=FONT, text=hook, font_size=46,
            color="#FFFFFF", stroke_color="black", stroke_width=2,
            text_align="center", horizontal_align="center", vertical_align="center",
            method="label",
        ).with_duration(hook_duration).with_position(("center", H * 0.28 + 150))

        subtitle_bar = _make_subtitle_bar(hook_duration)
        hook_tag = _make_tag_chip("消防科普", hook_duration)
        hook_bg = hook_bg.with_effects([FadeIn(0.15)])
        hook_clip = CompositeVideoClip([hook_bg, hook_tag, subtitle_bar, title_text, subtitle_text], size=(W, H))
        clips.append(hook_clip)
        current_time += hook_duration

    n = len(scenes)
    per_scene_durations = base_durations[duration_cursor:duration_cursor + n] if n else []
    duration_cursor += n

    for i, scene in enumerate(scenes):
        clip_paths = scene.get("_clips", [])
        clip_path = clip_paths[i % max(len(clip_paths), 1)] if clip_paths and isinstance(clip_paths, list) else None
        sd = per_scene_durations[i]
        bg_clip = _fit_video_to_vertical(clip_path, sd)

        subtitle_bar = _make_subtitle_bar(sd)
        animated_text = _get_animated_text(scene["text"], sd, font_size=50)
        progress = _make_progress(i + 1, n, sd)
        tag_text, accent = _pick_scene_tag(scene["text"])
        tag_chip = _make_tag_chip(tag_text, sd, bg_color=accent)
        info_card = _make_info_card(scene["text"][:20], sd, accent=accent)

        layers = [bg_clip, info_card, tag_chip, subtitle_bar, animated_text, progress]
        scene_clip = CompositeVideoClip(layers, size=(W, H))
        scene_clip = scene_clip.with_effects([FadeIn(0.12)])
        clips.append(scene_clip)
        current_time += sd

    if outro:
        outro_duration = base_durations[duration_cursor] if duration_cursor < len(base_durations) else min(3.0, total_duration * 0.1)
        outro_bg = _make_fire_bg(outro_duration)
        outro_bg = _ken_burns(outro_bg, outro_duration, zoom_ratio=0.08)
        outro_tag = _make_tag_chip("立即咨询", outro_duration, bg_color="#FF4500")

        cta_text = TextClip(
            font=FONT, text=outro, font_size=60,
            color="#FFD700", stroke_color="black", stroke_width=3,
            text_align="center", horizontal_align="center", vertical_align="center",
            method="label",
        ).with_duration(outro_duration).with_position(("center", "center"))

        outro_clip = CompositeVideoClip([outro_bg, outro_tag, cta_text], size=(W, H))
        outro_clip = outro_clip.with_effects([FadeIn(0.15), FadeOut(0.3)])
        clips.append(outro_clip)

    final = concatenate_videoclips(clips, method="compose")
    final = final.with_duration(total_duration)

    audio_layers = [full_audio]

    if bgm_config and bgm_config.get("enabled") and bgm_config.get("paths"):
        bgm_paths = bgm_config["paths"]
        bgm_volume_db = bgm_config.get("volume", -25)
        bgm_random = bgm_config.get("random", True)
        valid_bgms = [p for p in bgm_paths if os.path.exists(p)]
        if valid_bgms:
            chosen = random.choice(valid_bgms) if bgm_random else valid_bgms[0]
            try:
                bgm_clip = AudioFileClip(chosen)
                if bgm_clip.duration < total_duration:
                    n_loops = math.ceil(total_duration / bgm_clip.duration)
                    bgm_clip = concatenate_audioclips([bgm_clip] * n_loops)
                if bgm_clip.duration > total_duration:
                    bgm_clip = bgm_clip.subclipped(0, total_duration)
                bgm_clip = bgm_clip.with_volume_scaled(10 ** (bgm_volume_db / 20))
                audio_layers.append(bgm_clip)
                print(f"  [+] BGM: {os.path.basename(chosen)} ({bgm_volume_db}dB)")
            except Exception as e:
                print(f"  [-] BGM failed: {e}")

    mixed_audio = CompositeAudioClip(audio_layers)
    final = final.with_audio(mixed_audio)

    final.write_videofile(
        output_path,
        fps=20,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="ultrafast",
        bitrate="3000k",
    )

    return output_path
