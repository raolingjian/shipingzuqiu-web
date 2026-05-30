#!/usr/bin/env python3
import os, sys, json, tomllib
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from scripts.fetch_news import fetch_news, format_news_summary
from scripts.generate_script import generate_script
from scripts.download_videos import download_videos
from scripts.text_to_speech import run_tts
from scripts.compose_video import compose_video
from upload import publish_all

def load_config():
    path = os.path.join(PROJECT_DIR, "config.toml")
    if not os.path.exists(path):
        raise FileNotFoundError(f"config.toml not found at {path}")
    print(f"  配置: {os.path.basename(path)}")
    with open(path, "rb") as f:
        return tomllib.load(f)

def ensure_dirs(cfg):
    today = datetime.now().strftime("%Y-%m-%d")
    out_dir = os.path.join(PROJECT_DIR, cfg["project"]["output_dir"], today)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(PROJECT_DIR, "materials", "clips"), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_DIR, "cookies"), exist_ok=True)
    return out_dir, today

def make_video(script, title, out_dir, today, cfg, font_path):
    print(f"\n  --- 制作视频: {title} ---\n")
    print("  [TTS] 生成配音...")
    texts = []
    if script.get("hook"):
        texts.append(script["hook"])
    for s in script.get("scenes", []):
        texts.append(s["text"])
    if script.get("outro"):
        texts.append(script["outro"])
    audio_files, full_audio = run_tts(
        texts,
        voice=cfg["tts"]["voice"],
        rate=cfg["tts"].get("rate", "+0%"),
        volume=cfg["tts"]["volume"],
        enable_ssml=cfg["tts"].get("enable_ssml", True),
        pitch_variation=cfg["tts"].get("pitch_variation", True),
    )
    print(f"  生成 {len(audio_files)} 段音频")
    print("  [合成] 合成视频...")
    safe_title = title.replace(" ", "_").replace("/", "_").replace("?", "").replace("！", "").replace("🔥", "")[:50]
    video_path = os.path.join(out_dir, f"{today}_{safe_title}.mp4")
    bgm_config = {
        "enabled": cfg["tts"].get("bgm_enabled", True),
        "paths": [os.path.join(PROJECT_DIR, p) for p in cfg["tts"].get("bgm_paths", [])],
        "volume": cfg["tts"].get("bgm_volume", -25),
        "random": cfg["tts"].get("bgm_random", True),
    } if cfg["tts"].get("bgm_enabled", True) else None
    compose_video(
        script_dict=script,
        audio_files=audio_files,
        full_audio_path=full_audio,
        font_path=font_path,
        output_path=video_path,
        bgm_config=bgm_config,
        title=title,
    )
    print("  [封面] 生成封面...")
    cover_path = os.path.join(out_dir, f"{today}_{safe_title}_cover.png")
    from scripts.make_cover import make_cover
    make_cover(title=title, output_path=cover_path, font_path=font_path, video_path=video_path)
    return video_path, cover_path

def main():
    cfg = load_config()
    out_dir, today = ensure_dirs(cfg)
    print(f"\n{'='*50}")
    print(f"  消防考证科普视频 - {today}")
    print(f"{'='*50}\n")
    print("[1/5] 获取消防相关热点...")
    keywords = cfg["news"].get("keywords", ["消防证", "消防安全"])
    news = fetch_news(max_results=cfg["news"]["max_results"], keywords=keywords)
    print(f"  找到 {len(news)} 条相关内容")
    summary = format_news_summary(news)
    print(f"  {summary}\n")
    print("[2/5] AI 写脚本...")
    from openai import OpenAI
    client = OpenAI(
        api_key=cfg["llm"]["api_key"],
        base_url=cfg["llm"].get("base_url", "https://api.openai.com/v1"),
    )
    script = generate_script(summary, client, model=cfg["llm"]["model"])
    title = script.get("title", "消防考证知识")
    print(f"  标题: {title}")
    print(f"  场景数: {len(script.get('scenes', []))}\n")
    script_path = os.path.join(out_dir, "script.json")
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    print("[3/5] 下载视频素材...")
    scenes = script.get("scenes", [])
    clip_results = download_videos(scenes, num_clips=len(scenes))
    for i, paths in enumerate(clip_results):
        if paths:
            scenes[i]["_clips"] = paths
        else:
            scenes[i]["_clips"] = []
    print()
    font_path = os.path.join(PROJECT_DIR, cfg["project"]["font_path"])
    video_path, cover_path = make_video(script, title, out_dir, today, cfg, font_path)
    print(f"\n[4/5] 自动发布到各平台...")
    skip = []
    if "--no-douyin" in sys.argv:
        skip.append("抖音")
    if "--no-xhs" in sys.argv:
        skip.append("小红书")
    if "--no-kuaishou" in sys.argv:
        skip.append("快手")
    if "--no-weixin" in sys.argv:
        skip.append("微信视频号")
    publish_all(
        video_path=video_path,
        title=title,
        cover_path=cover_path,
        description=script.get("hook", title),
        headless=cfg["publish"].get("headless", False),
        skip=skip,
    )
    print(f"\n{'='*50}")
    print(f"  🎉 消防考证视频流程完成！")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
