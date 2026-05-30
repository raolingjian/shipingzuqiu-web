import os, sys, json, random, time, subprocess, math
import requests

try:
    import imageio_ffmpeg
    _FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    _FFMPEG_PATH = "ffmpeg"

def _ffmpeg(*args, **kw):
    cmd = [_FFMPEG_PATH] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=kw.get("timeout", 60))

def _ffprobe(*args, **kw):
    probe_path = _FFMPEG_PATH.replace("ffmpeg", "ffprobe")
    if not os.path.exists(probe_path):
        try:
            import imageio_ffmpeg
            base = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
            for f in os.listdir(base):
                if "ffprobe" in f.lower() and f.endswith(".exe"):
                    probe_path = os.path.join(base, f)
                    break
                if "ffmpeg" in f.lower() and "v7" in f and f.endswith(".exe"):
                    probe_path = os.path.join(base, f)
                    break
        except Exception:
            pass
        if not os.path.exists(probe_path):
            probe_path = _FFMPEG_PATH
    cmd = [probe_path] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=kw.get("timeout", 30))

def _get_video_duration(video_path):
    try:
        probe = _ffprobe("-v", "quiet", "-print_format", "json", "-show_format", video_path)
        if probe.returncode == 0:
            info = json.loads(probe.stdout)
            return float(info["format"]["duration"])
    except Exception:
        pass
    try:
        result = _ffmpeg("-i", video_path, "-f", "null", "-", timeout=30)
        stderr = result.stderr.decode("utf-8", errors="replace")
        for line in stderr.split("\n"):
            if "Duration" in line:
                parts = line.strip().split(",")[0].split("Duration:")[1].strip()
                h, m, s = parts.split(":")
                return float(h) * 3600 + float(m) * 60 + float(s)
    except Exception:
        pass
    try:
        with open(video_path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if size > 0:
                return size / (1024 * 1024) * 0.5
    except Exception:
        pass
    return 60

CLIPS_DIR = None
CACHE_FILE = None

KEYWORDS = [
    "消防 演练", "消防员 训练", "消防 培训", "消防安全 教育",
    "火灾 逃生", "消防 检查", "消防 知识", "消防 宣传",
    "消防员 出警", "消防 技能",
]

CLIP_DURATION = 32

def _safe_print(*args, **kw):
    text = " ".join(str(a) for a in args)
    try:
        print(text, **kw)
    except UnicodeEncodeError:
        print(text.encode("gbk", errors="replace").decode("gbk"), **kw)

def _ensure_dirs():
    global CLIPS_DIR, CACHE_FILE
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CLIPS_DIR = os.path.join(base, "materials", "clips")
    CACHE_FILE = os.path.join(CLIPS_DIR, ".clip_cache.json")
    os.makedirs(CLIPS_DIR, exist_ok=True)

def _load_cache():
    if CACHE_FILE and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"used_clips": [], "available_clips": []}

def _save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def _search_bilibili(keyword, page=1, max_results=10):
    try:
        url = "https://api.bilibili.com/x/web-interface/search/all/v2"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://search.bilibili.com/",
        }
        resp = requests.get(url, params={"keyword": keyword, "page": page}, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if data.get("code") != 0:
            return []
        results = data.get("data", {}).get("result", [])
        videos = []
        for item in results:
            if not isinstance(item, dict):
                continue
            items = item.get("data", [])
            if not isinstance(items, list):
                continue
            for v in items:
                if not isinstance(v, dict):
                    continue
                bvid = v.get("bvid", "")
                if not bvid:
                    continue
                duration_sec = 0
                dur_str = str(v.get("duration", "0:00"))
                parts = dur_str.split(":")
                if len(parts) == 2:
                    duration_sec = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    duration_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                videos.append({
                    "bvid": bvid,
                    "title": v.get("title", "").replace("<em class=\"keyword\">", "").replace("</em>", ""),
                    "duration": duration_sec,
                    "author": v.get("author", ""),
                })
        return videos[:max_results]
    except Exception as e:
        _safe_print(f"  [B站搜索异常] {keyword}: {e}")
        return []

def _download_video(bvid, output_dir):
    url = f"https://www.bilibili.com/video/{bvid}"
    output_template = os.path.join(output_dir, f"{bvid}.%(ext)s")
    try:
        import yt_dlp
        ydl_opts = {
            "format": "bv[height<=720]+ba/b[height<=720]",
            "outtmpl": output_template,
            "restrictfilenames": True,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "merge_output_format": "mp4",
            "ffmpeg_location": _FFMPEG_PATH if _FFMPEG_PATH != "ffmpeg" else None,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            for f in os.listdir(output_dir):
                if f.startswith(bvid) and f.endswith((".mp4", ".mkv", ".webm")):
                    return os.path.join(output_dir, f)
            return None
    except Exception as e:
        _safe_print(f"  [下载失败] {bvid}: {str(e)[:200]}")
        return None

def _extract_segments(video_path, num_segments=2, clip_duration=CLIP_DURATION):
    total_dur = _get_video_duration(video_path)
    if total_dur < clip_duration:
        return [video_path]
    safe_start = max(5, total_dur * 0.05)
    safe_end = total_dur * 0.9 - clip_duration
    if safe_end <= safe_start:
        safe_end = safe_start + 1
    segments = []
    base_name = os.path.splitext(video_path)[0]
    for i in range(num_segments):
        start = random.uniform(safe_start, safe_end)
        seg_path = f"{base_name}_seg{i}_{int(start)}.mp4"
        if not os.path.exists(seg_path):
            try:
                _ffmpeg("-y", "-ss", str(start), "-i", video_path,
                        "-t", str(clip_duration), "-c", "copy",
                        "-avoid_negative_ts", "make_zero", seg_path, timeout=60)
            except Exception:
                continue
        segments.append(seg_path)
    return segments

def _is_usable_clip(path):
    if not path or not os.path.exists(path):
        return False
    return os.path.getsize(path) > 50000

def _refresh_clip_pool(min_new=3):
    cache = _load_cache()
    available = [c for c in cache.get("available_clips", []) if os.path.exists(c)]
    if len(available) >= min_new + 2:
        cache["available_clips"] = available
        _save_cache(cache)
        _safe_print(f"  [缓存] 已有 {len(available)} 个可用片段")
        return
    random.shuffle(KEYWORDS)
    downloaded = 0
    for kw in KEYWORDS:
        if downloaded >= min_new:
            break
        _safe_print(f"  [B站搜索] {kw}")
        videos = _search_bilibili(kw, page=1, max_results=5)
        time.sleep(1.5)
        for v in videos:
            if downloaded >= min_new:
                break
            if v["duration"] < 40 or v["duration"] > 900:
                continue
            if any(v["bvid"] in c for c in available):
                continue
            _safe_print(f"  [下载] {v['title'][:40]}...")
            path = _download_video(v["bvid"], CLIPS_DIR)
            if path and os.path.exists(path):
                segments = _extract_segments(path, num_segments=random.randint(2, 3))
                for seg in segments:
                    if _is_usable_clip(seg):
                        available.append(seg)
                downloaded += 1
            time.sleep(2)
    cache["available_clips"] = available
    _save_cache(cache)

def download_videos(scenes, num_clips=8):
    _ensure_dirs()
    _refresh_clip_pool(min_new=3)
    cache = _load_cache()
    available = [c for c in cache.get("available_clips", []) if os.path.exists(c)]
    used = set(cache.get("used_clips", []))
    fresh = [c for c in available if c not in used]
    if len(fresh) < num_clips:
        fresh = available
    random.shuffle(fresh)
    chosen = fresh[:num_clips]
    for c in chosen:
        used.add(c)
    cache["used_clips"] = list(used)
    _save_cache(cache)
    result = []
    for i in range(len(scenes)):
        idx = i % max(len(chosen), 1)
        result.append([chosen[idx]] if chosen else [])
    _safe_print(f"  [视频素材] 选用 {len(chosen)}/{len(available)} 个片段")
    return result

def download_videos_for_scenes(scenes, clips_per_scene=1):
    return download_videos(scenes, num_clips=len(scenes) * clips_per_scene)

if __name__ == "__main__":
    test_scenes = [{"text": "消防知识1"}, {"text": "消防知识2"}, {"text": "消防知识3"}]
    results = download_videos(test_scenes, num_clips=3)
    print(json.dumps(results, ensure_ascii=False, indent=2))
