#!/usr/bin/env python3
"""
B站教程视频 - AI/智能体/工作流 系列教程
支持长视频（3-10分钟），不受时间限制
"""

import os
import sys
import json
import time
import tomllib
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)
# 共享足球项目的脚本
sys.path.insert(0, os.path.join(os.path.dirname(PROJECT_DIR), "足球"))

from scripts.fetch_news import fetch_news, format_news_summary
from scripts.generate_script import generate_script
from scripts.download_videos import download_videos
from scripts.text_to_speech import run_tts
from scripts.compose_video import compose_video
from scripts.make_cover import make_cover


BILIBILI_UPLOAD_URL = "https://member.bilibili.com/platform/upload/video/frame"
BILIBILI_CHECK_URL = "https://member.bilibili.com/platform/video-management/video"
BILIBILI_STATE_FILE = os.path.join(PROJECT_DIR, "playwright_state.json")


def _load_state(context):
    """加载B站登录状态"""
    if os.path.exists(BILIBILI_STATE_FILE):
        with open(BILIBILI_STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        context.add_cookies(state.get("cookies", []))


def _save_state(context):
    """保存B站登录状态"""
    state = context.storage_state()
    with open(BILIBILI_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def login_bilibili():
    """登录B站（扫码登录）"""
    from playwright.sync_api import sync_playwright

    print("\n  === B站登录 ===\n")
    with sync_playwright() as pw:
        b = pw.chromium.launch_persistent_context(
            os.path.join(PROJECT_DIR, "playwright_profile"),
            channel="chrome", headless=False, no_viewport=True,
        )
        _load_state(b)
        page = b.new_page()

        page.goto(BILIBILI_UPLOAD_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)

        cur = page.url.lower()
        if "login" in cur or "passport" in cur:
            print("  请在浏览器中扫码登录B站，然后按 Enter 继续")
            input("  >>> ")
            time.sleep(2)
            _save_state(b)
            print("  [+] B站登录状态已保存")
        else:
            _save_state(b)
            print("  [+] B站已登录")

        page.goto("about:blank")
        time.sleep(1)
        b.close()


def upload_to_bilibili(video_path, title, description="", cover_path=None):
    """上传视频到B站"""
    from playwright.sync_api import sync_playwright

    video_path = os.path.abspath(video_path)
    if not os.path.exists(video_path):
        print(f"  [X] 视频不存在: {video_path}")
        return False

    print(f"\n  === 上传到B站 ===")
    print(f"  视频: {video_path}")
    print(f"  标题: {title}\n")

    pw = sync_playwright().start()
    b = pw.chromium.launch_persistent_context(
        os.path.join(PROJECT_DIR, "playwright_profile"),
        channel="chrome", headless=False, no_viewport=True,
    )
    _load_state(b)
    page = b.new_page()

    try:
        # 1. 导航到上传页
        print("  [1/5] 打开上传页...")
        page.goto(BILIBILI_UPLOAD_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)

        if "login" in page.url.lower() or "passport" in page.url.lower():
            print("  [X] 未登录，请先运行 python main.py login")
            b.close()
            pw.stop()
            return False

        # 2. 上传视频文件
        print("  [2/5] 上传视频文件...")
        uploaded = False
        try:
            with page.expect_file_chooser(timeout=30000) as fc_info:
                for sel in ["text=上传视频", "text=点击上传", "text=拖拽", "[class*='upload']"]:
                    try:
                        el = page.locator(sel).first
                        if el.is_visible(timeout=2000):
                            el.click()
                            break
                    except Exception:
                        continue
                else:
                    page.locator("input[type='file']").first.click(force=True, timeout=5000)
            fc = fc_info.value
            fc.set_files(video_path)
            uploaded = True
        except Exception:
            pass

        if not uploaded:
            page.evaluate("""
                const inp = document.querySelector('input[type=file]');
                if (inp) { inp.style.display='block'; inp.style.visibility='visible'; inp.style.opacity='1'; }
            """)
            time.sleep(1)
            page.locator("input[type='file']").first.set_input_files(video_path)
            uploaded = True

        print("  [+] 视频已上传，等待处理...")
        time.sleep(15)

        # 3. 填写标题
        print("  [3/5] 填写标题...")
        for sel in ['input[placeholder*="标题"]', 'textarea[placeholder*="标题"]',
                    'input[placeholder*="填写"]', 'textarea[placeholder*="填写"]']:
            try:
                inp = page.locator(sel).first
                if inp.is_visible(timeout=3000):
                    inp.fill("")
                    time.sleep(0.3)
                    inp.fill(title)
                    print(f"  [+] 标题已填写")
                    break
            except Exception:
                continue

        # 4. 填写简介
        if description:
            print("  [4/5] 填写简介...")
            for sel in ['textarea[placeholder*="简介"]', 'textarea[placeholder*="描述"]',
                        'textarea[placeholder*="说点什么"]', 'textarea']:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        el.fill("")
                        time.sleep(0.3)
                        el.fill(description)
                        print(f"  [+] 简介已填写")
                        break
                except Exception:
                    continue
        else:
            print("  [4/5] 跳过简介")

        # 5. 点击投稿
        print("  [5/5] 点击投稿...")
        for sel in ["text=投稿", "text=立即投稿", "button:has-text('投稿')"]:
            try:
                btn = page.locator(sel).last
                if btn.is_visible(timeout=5000):
                    btn.click(force=True)
                    print("  [+] 已点击投稿")
                    time.sleep(3)
                    break
            except Exception:
                continue

        # 检查是否成功
        time.sleep(5)
        body_text = page.evaluate("document.body.innerText")
        if "投稿成功" in body_text or "稿件" in body_text or "审核" in body_text:
            print("  [✓] B站投稿成功！")
            _save_state(b)
        else:
            print("  [-] 投稿状态未知，请检查浏览器")

        # 验证
        try:
            page.goto(BILIBILI_CHECK_URL, wait_until="domcontentloaded", timeout=20000)
            time.sleep(5)
            page_text = page.evaluate("document.body.innerText")
            if title[:6] in page_text:
                print(f"  [✓] 标题匹配！发布成功确认")
            else:
                print(f"  [-] 未检测到标题，可能仍在处理")
        except Exception:
            pass

        print("\n  浏览器保持打开，请检查发布状态。")
        print("  按 Enter 关闭...")
        input("  >>> ")

    except Exception as e:
        print(f"  [X] 上传异常: {str(e)[:100]}")
    finally:
        b.close()
        pw.stop()

    return True


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
    os.makedirs(os.path.join(PROJECT_DIR, "materials", "audio"), exist_ok=True)
    return out_dir, today


def make_video(script, title, out_dir, today, cfg, font_path):
    """将脚本合成为视频（TTS → compose_video → make_cover）"""
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
    make_cover(
        title=title,
        output_path=cover_path,
        font_path=font_path,
        video_path=video_path,
    )

    return video_path, cover_path


def main():
    cfg = load_config()
    out_dir, today = ensure_dirs(cfg)

    channel_name = cfg.get("account", {}).get("channel_name", "游戏策划转型AI实战")
    print(f"\n{'='*50}")
    print(f"  B站教程视频 - {channel_name}")
    print(f"  {today}")
    print(f"{'='*50}\n")

    # --- 预设的教程选题 ---
    tutorial_topics = [
        {
            "title": "我如何用AI自动做短视频",
            "hook": "今天带大家看看，我是怎么用AI一键生成短视频的",
            "points": [
                "系统总览：新闻抓取→AI写脚本→自动合成→发布",
                "DeepSeek写脚本有多快？10秒出一条",
                "Edge TTS免费配音，效果堪比真人",
                "MoviePy自动合成，字幕标签全自动",
                "一次运行，4个平台同时发布",
            ]
        },
        {
            "title": "Cursor+AI编程有多爽",
            "hook": "38岁游戏策划，用Cursor一周写了3000行代码",
            "points": [
                "Cursor是什么？AI编程助手",
                "写代码像聊天一样简单",
                "自动化脚本、爬虫、数据处理全搞定",
                "不会Python也能写出好用的工具",
                "我的实际案例：短视频自动化系统",
            ]
        },
        {
            "title": "DeepSeek写脚本实战",
            "hook": "让AI帮你写短视频脚本，10秒出一条爆款",
            "points": [
                "DeepSeek是什么？国产大模型之光",
                "写脚本的Prompt模板分享",
                "如何让AI写出接地气的文案",
                "JSON格式输出+自动重试机制",
                "批量生成：一次出3条视频脚本",
            ]
        },
        {
            "title": "Edge TTS免费配音教程",
            "hook": "免费的AI配音工具，效果堪比专业录音棚",
            "points": [
                "Edge TTS是什么？微软的免费语音合成",
                "支持多种中文声音：男声/女声",
                "随机音调变化，听起来更自然",
                "每段文案独立合成，失败自动重试",
                "完全免费，不需要API Key",
            ]
        },
        {
            "title": "MoviePy视频合成入门",
            "hook": "用Python自动合成短视频，字幕标签全自动",
            "points": [
                "MoviePy是什么？Python视频编辑库",
                "1080x1920竖屏视频合成",
                "动态字幕+标签芯片+信息卡片",
                "BGM混音+音量控制",
                "一键生成封面图",
            ]
        },
        {
            "title": "B站视频自动下载",
            "hook": "自动下载B站视频做素材，省去找视频的时间",
            "points": [
                "yt-dlp下载B站视频",
                "按关键词搜索相关视频",
                "自动切片：随机位置截取片段",
                "缓存机制：已下载的不重复下载",
                "720p画质，大小适中",
            ]
        },
        {
            "title": "一键发布4个平台",
            "hook": "抖音、小红书、快手、微信视频号，一次全发",
            "points": [
                "Playwright自动化浏览器操作",
                "登录状态持久化，扫码一次长期有效",
                "每个平台的特殊处理：AI声明、原创声明",
                "小红书Shadow DOM发布技巧",
                "微信视频号Wujie框架适配",
            ]
        },
        {
            "title": "Supabase管理你的内容",
            "hook": "用免费数据库管理你的短视频内容",
            "points": [
                "Supabase是什么？免费的Firebase替代",
                "创建配置表、任务表、视频表",
                "实时订阅：任务状态变化自动通知",
                "前端管理面板：配置+监控",
                "手机APP远程管理",
            ]
        },
    ]

    # 选择选题
    topic_idx = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 0
    topic = tutorial_topics[topic_idx % len(tutorial_topics)]

    print(f"[1/4] 选题: {topic['title']}")
    print(f"  Hook: {topic['hook']}")
    print(f"  要点: {len(topic['points'])}个\n")

    # 生成完整脚本
    print("[2/4] AI 生成教程脚本...")
    from openai import OpenAI
    client = OpenAI(
        api_key=cfg["llm"]["api_key"],
        base_url=cfg["llm"].get("base_url", "https://api.openai.com/v1"),
    )

    # 构建教程脚本（不受时间限制）
    scenes = []
    for i, point in enumerate(topic["points"], 1):
        # 每个要点拆分成2-3个子场景
        parts = point.split("：") if "：" in point else [point]
        if len(parts) == 1:
            scenes.append({"text": parts[0], "image_desc": f"教程画面{i}"})
        else:
            # 标题 + 解释
            scenes.append({"text": parts[0] + "！", "image_desc": f"教程标题{i}"})
            if len(parts) > 1:
                # 拆分解释为多句话
                detail = parts[1]
                sentences = [s.strip() for s in detail.replace("。", "，").split("，") if s.strip()]
                for sent in sentences[:3]:
                    scenes.append({"text": sent, "image_desc": f"教程细节{i}"})

    # 确保场景数在合理范围
    if len(scenes) < 10:
        # 补充过渡场景
        transitions = [
            "接下来我们看实际操作",
            "大家跟着我做",
            "这一步很关键",
            "很多人在这里出错",
            "学会了这个就简单了",
        ]
        while len(scenes) < 10:
            scenes.append({
                "text": transitions[len(scenes) % len(transitions)],
                "image_desc": "过渡画面"
            })

    script = {
        "title": topic["title"],
        "hook": topic["hook"],
        "scenes": scenes[:20],  # 最多20个场景
        "outro": "如果觉得有用，一键三连支持一下！",
        "target_duration": cfg.get("video", {}).get("target_duration", 300),
        "style": "tutorial",
    }

    title = script["title"]
    print(f"  标题: {title}")
    print(f"  场景数: {len(script.get('scenes', []))}\n")

    script_path = os.path.join(out_dir, "script.json")
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    print("[3/4] 下载视频素材（按场景文字搜索新视频）...")
    scenes_data = script.get("scenes", [])
    clip_results = download_videos(scenes_data, num_clips=len(scenes_data), fresh=True)
    for i, paths in enumerate(clip_results):
        if paths:
            scenes_data[i]["_clips"] = paths
        else:
            scenes_data[i]["_clips"] = []
    print()

    font_path = os.path.join(PROJECT_DIR, cfg["project"]["font_path"])
    video_path, cover_path = make_video(script, title, out_dir, today, cfg, font_path)

    print(f"\n[4/4] 视频制作完成！")
    print(f"  视频: {video_path}")
    print(f"  封面: {cover_path}")
    print(f"  脚本: {script_path}")

    print(f"\n{'='*50}")
    print(f"  🎉 B站教程视频制作完成！")
    print(f"{'='*50}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "login":
            login_bilibili()
        elif arg.isdigit():
            main()
        elif os.path.exists(arg):
            # 上传模式：python main.py <视频路径> <标题> <简介>
            video = arg
            title = sys.argv[2] if len(sys.argv) > 2 else "教程视频"
            desc = sys.argv[3] if len(sys.argv) > 3 else ""
            upload_to_bilibili(video, title, desc)
        else:
            print(f"  未知参数: {arg}")
            print("  用法:")
            print("    python main.py login        — 登录B站")
            print("    python main.py 0            — 制作第1集")
            print("    python main.py video.mp4 标题 简介  — 上传到B站")
    else:
        main()
