#!/usr/bin/env python3
"""
中国足球吃瓜短视频 - 自动化流水线
支持 --ollama 使用本地模型（免费，需先安装 Ollama）
支持 --config <路径> 指定配置文件
"""

import os
import sys
import json
import tomllib
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from scripts.fetch_news import fetch_news, format_news_summary
from scripts.generate_script import generate_script
from scripts.download_videos import download_videos
from scripts.text_to_speech import run_tts
from scripts.compose_video import compose_video
from scripts.make_cover import make_cover
from upload import publish_all


def load_config():
    config_name = "config.toml"
    if "--ollama" in sys.argv:
        config_name = "config_ollama.toml"
    for i, arg in enumerate(sys.argv):
        if arg == "--config" and i + 1 < len(sys.argv):
            config_name = sys.argv[i + 1]
            break
    path = os.path.join(PROJECT_DIR, config_name)
    if not os.path.exists(path):
        path = os.path.join(PROJECT_DIR, "config.toml")
    print(f"  配置: {os.path.basename(path)}")
    with open(path, "rb") as f:
        return tomllib.load(f)


def ensure_dirs(cfg):
    today = datetime.now().strftime("%Y-%m-%d")
    out_dir = os.path.join(PROJECT_DIR, cfg["project"]["output_dir"], today)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(PROJECT_DIR, "materials", "images"), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_DIR, "cookies"), exist_ok=True)
    return out_dir, today


def make_video(script, title, out_dir, today, cfg, font_path):
    """将单个脚本合成为视频（TTS → compose_video → make_cover）"""
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
    safe_title = title.replace(" ", "_").replace("/", "_").replace("?", "")[:50]
    video_path = os.path.join(out_dir, f"{today}_{safe_title}.mp4")
    bgm_config = {
        "enabled": cfg["tts"].get("bgm_enabled", True),
        "paths": [os.path.join(PROJECT_DIR, p) for p in cfg["tts"].get("bgm_paths", [])],
        "volume": cfg["tts"].get("bgm_volume", -20),
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
    make_cover(
        title=title,
        output_path=cover_path,
        font_path=font_path,
        video_path=video_path,
    )

    return video_path, cover_path


def make_runs(news_list, cfg, out_dir, today, max_runs=3):
    """批量处理多条新闻，生成多个视频"""
    from openai import OpenAI
    client = OpenAI(
        api_key=cfg["llm"]["api_key"],
        base_url=cfg["llm"].get("base_url", "https://api.openai.com/v1"),
    )
    font_path = os.path.join(PROJECT_DIR, cfg["project"]["font_path"])

    results = []
    for idx in range(min(len(news_list), max_runs)):
        print(f"\n{'='*50}")
        print(f"  [{idx+1}/{min(len(news_list), max_runs)}] 处理新闻: {news_list[idx].get('title','')[:60]}")
        print(f"{'='*50}")

        summary = format_news_summary([news_list[idx]])
        script = generate_script(summary, client, model=cfg["llm"]["model"])
        title = script.get("title", "中国足球又闹心了")

        script_path = os.path.join(out_dir, f"script_{idx+1}.json")
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)

        print("  [视频] 下载视频素材...")
        scenes = script.get("scenes", [])
        clip_results = download_videos(scenes, num_clips=len(scenes))
        for i, paths in enumerate(clip_results):
            if paths:
                scenes[i]["_clips"] = paths
            else:
                scenes[i]["_clips"] = []

        video_path, cover_path = make_video(script, title, out_dir, today, cfg, font_path)
        desc = script.get("hook", title)
        results.append({"title": title, "video": video_path, "cover": cover_path, "script": script_path, "description": desc})

    return results


def main():
    cfg = load_config()
    out_dir, today = ensure_dirs(cfg)

    print(f"\n{'='*50}")
    print(f"  中国足球吃瓜视频 - {today}")
    print(f"{'='*50}\n")

    print("[1/5] 抓取今日足球热点...")
    news = fetch_news(max_results=cfg["news"]["max_results"], sources=cfg["news"].get("sources"))
    print(f"  找到 {len(news)} 条新闻")

    # 如果有多条新闻且有 make_runs 模式则批量处理
    if "--batch" in sys.argv:
        print("[2/5] 批量模式: 生成多个视频...")
        results = make_runs(news, cfg, out_dir, today, max_runs=3)
        print(f"\n  共生成 {len(results)} 个视频:")
        for r in results:
            print(f"    - {r['title']}: {r['video']}")

        print("\n[发布] 批量发布...")
        for r in results:
            publish_all(
                video_path=r["video"],
                title=r["title"],
                cover_path=r["cover"],
                description=r.get("description", r["title"]),
                headless=cfg["publish"].get("headless", False),
            )
        return

    # 单条模式
    summary = format_news_summary(news)
    print(f"  {summary}\n")

    print("[2/5] AI 写吃瓜脚本...")
    from openai import OpenAI
    client = OpenAI(
        api_key=cfg["llm"]["api_key"],
        base_url=cfg["llm"].get("base_url", "https://api.openai.com/v1"),
    )
    script = generate_script(summary, client, model=cfg["llm"]["model"])
    title = script.get("title", "中国足球又闹心了")
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

    print(f"\n[5/5] 自动发布到各平台...")
    desc = script.get("hook", title)
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
        description=desc,
        headless=cfg["publish"].get("headless", False),
        skip=skip,
    )

    print(f"\n{'='*50}")
    print(f"  🎉 今日视频流程完成！")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
