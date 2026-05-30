import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

W, H = 1080, 1920


def make_cover(title, output_path, font_path, video_path=None):
    """B站教程视频封面：视频截图+艺术字"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 1. 背景
    if video_path and os.path.exists(video_path):
        bg_img = _extract_frame(video_path)
    else:
        bg_img = None

    if bg_img is None:
        bg_img = _make_tech_bg()

    bg_img = bg_img.resize((W, H), Image.Resampling.LANCZOS)

    # 2. 遮罩
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for y in range(H // 3, H):
        alpha = int(180 * (y - H // 3) / (H * 2 // 3))
        odraw.rectangle([(0, y), (W, y + 1)], fill=(0, 0, 0, min(alpha, 180)))
    for y in range(0, H // 5):
        alpha = int(120 * (1 - y / (H // 5)))
        odraw.rectangle([(0, y), (W, y + 1)], fill=(0, 0, 0, alpha))
    bg_img = Image.alpha_composite(bg_img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(bg_img)

    # 3. 字体
    font_big = ImageFont.truetype(font_path, 100) if os.path.exists(font_path) else ImageFont.load_default()
    font_mid = ImageFont.truetype(font_path, 50) if os.path.exists(font_path) else ImageFont.load_default()
    font_small = ImageFont.truetype(font_path, 36) if os.path.exists(font_path) else ImageFont.load_default()

    # 4. 顶部标签
    tag_text = "🤖 AI实战教程"
    tag_bbox = draw.textbbox((0, 0), tag_text, font=font_small)
    tag_w = tag_bbox[2] - tag_bbox[0] + 40
    tag_h = tag_bbox[3] - tag_bbox[1] + 20
    draw.rounded_rectangle([(60, 80), (60 + tag_w, 80 + tag_h)],
                           radius=tag_h // 2, fill=(0, 255, 136))
    draw.text((80, 80 + tag_h // 2), tag_text, fill="#000000", font=font_small, anchor="lm")

    # 5. 艺术字标题
    title_lines = _wrap_text(title, font_big, W - 160)
    title_y = H // 2 - len(title_lines) * 65
    for line in title_lines:
        draw.text((W // 2 + 4, title_y + 4), line, fill=(0, 0, 0), font=font_big, anchor="mm")
        for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
            draw.text((W // 2 + dx, title_y + dy), line, fill=(0, 0, 0), font=font_big, anchor="mm")
        draw.text((W // 2, title_y), line, fill="#00FF88", font=font_big, anchor="mm")
        title_y += 130

    # 6. 底部CTA
    draw.text((W // 2, H - 120), "👆 关注不迷路，干货持续更新", fill=(255, 255, 255, 200), font=font_mid, anchor="mm")

    bg_img.save(output_path, quality=95)
    return output_path


def _extract_frame(video_path):
    try:
        from moviepy import VideoFileClip
        clip = VideoFileClip(video_path)
        t = random.uniform(clip.duration * 0.3, clip.duration * 0.7)
        frame = clip.get_frame(t)
        clip.close()
        img = Image.fromarray(frame)
        img = img.filter(ImageFilter.GaussianBlur(radius=3))
        return img
    except Exception as e:
        print(f"  [封面] 截取视频帧失败: {e}")
        return None


def _make_tech_bg():
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        r = int(26 - 10 * (y / H))
        g = int(26 + 10 * (y / H))
        b = int(46 + 20 * (y / H))
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    # 网格装饰
    for x in range(0, W, 80):
        draw.line([(x, 0), (x, H)], fill=(255, 255, 255, 10), width=1)
    for y in range(0, H, 80):
        draw.line([(0, y), (W, y)], fill=(255, 255, 255, 10), width=1)
    return img


def _wrap_text(text, font, max_width):
    if font.getlength(text) <= max_width:
        return [text]
    lines = []
    current = ""
    for char in text:
        test = current + char
        if font.getlength(test) > max_width and current:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(__file__))
    make_cover(
        "我如何用AI自动做短视频",
        os.path.join(base, "output", "test_cover.png"),
        os.path.join(base, "..", "fonts", "msyh.ttc"),
    )
