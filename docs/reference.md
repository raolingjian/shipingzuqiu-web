# 🔧 短视频自动化系统 — 技能参考文档

> 短视频自动化系统的详细技术参考，包含每个模块的API、参数、调试方法

---

## 📦 依赖安装

```bash
pip install openai edge-tts moviepy pillow requests beautifulsoup4 yt-dlp imageio-ffmpeg icrawler
```

---

## 📰 模块1：新闻抓取 (fetch_news.py)

### 足球版

```python
from scripts.fetch_news import fetch_news, format_news_summary

# 基础用法
news = fetch_news(max_results=10)
summary = format_news_summary(news)
print(summary)

# 指定数据源
news = fetch_news(max_results=5, sources=["sina", "baidu"])
```

**参数：**
- `max_results`: 最大返回数量（默认5）
- `sources`: 数据源列表，可选值：`["sina", "baidu", "dongqiudi", "hupu", "sogou"]`

**返回格式：**
```python
[
    {"title": "新闻标题", "source": "新浪体育", "url": "https://..."},
    ...
]
```

### 教育版

```python
from scripts.fetch_news import fetch_news

news = fetch_news(max_results=10, keywords=["消防证", "消防工程师"])
```

### 调试

```bash
# 直接运行测试
cd 足球
python -m scripts.fetch_news
```

---

## 🤖 模块2：AI脚本生成 (generate_script.py)

### 足球版

```python
from openai import OpenAI
from scripts.generate_script import generate_script

client = OpenAI(api_key="sk-xxx", base_url="https://api.deepseek.com")
script = generate_script(news_summary, client, model="deepseek-chat")
```

**输出格式：**
```python
{
    "title": "封面标题",
    "hook": "开场5秒钩子",
    "scenes": [
        {"text": "配音文案", "image_desc": "画面描述"},
        ...
    ],
    "outro": "结尾引导语",
    "target_duration": 18,
    "style": "short_burst"
}
```

**内部处理：**
1. 调用AI生成JSON
2. 自动重试3次（JSON解析失败时）
3. `_normalize_script()` 标准化：
   - 标题截断到12字
   - 文案按12字切分（短爆点）
   - 场景数限制6-8个
   - 不足6个时用fallback填充

### 教育版

```python
# 教育版的outro固定为"想考消防证的朋友，加我咨询详情！"
# 其余逻辑相同
```

### 自定义Prompt

修改 `generate_script.py` 中的 `SYSTEM_PROMPT` 可自定义风格。

---

## 🎬 模块3：视频合成 (compose_video.py)

### 核心函数

```python
from scripts.compose_video import compose_video

compose_video(
    script_dict=script,      # AI生成的脚本
    audio_files=audio_files, # TTS音频文件列表
    full_audio_path=full_audio,  # 完整音频路径
    font_path="fonts/msyh.ttc", # 字体路径
    output_path="output/视频.mp4",
    bgm_config={              # 可选
        "enabled": True,
        "paths": ["materials/audio/bgm1.mp3"],
        "volume": -20,
        "random": True,
    },
    title="视频标题",         # 可选，默认从script取
)
```

### 字体自动检测

```python
# compose_video.py 内置 _find_font()
# 如果 font_path 无效，自动搜索：
# 1. 项目 fonts/msyh.ttc
# 2. 项目 fonts/NotoSansSC.ttf
# 3. C:\Windows\Fonts\msyh.ttc
# 4. C:\Windows\Fonts\simhei.ttf
# 5. C:\Windows\Fonts\simsun.ttc
# 6. C:\Windows\Fonts\msyhbd.ttc
```

### 视频结构

```
[开场] Title大字 + Hook副标题 + 字幕条 + 标签
  ↓
[场景1] 背景视频 + 信息卡片 + 标签 + 字幕条 + 动态字幕 + 进度
  ↓
[场景2] ...
  ↓
[结尾] 评论区见 + 字幕
```

### 合成参数

| 参数 | 值 | 说明 |
|------|------|------|
| fps | 20 | 帧率 |
| codec | libx264 | 编码器 |
| audio_codec | aac | 音频编码 |
| preset | ultrafast | 编码速度 |
| bitrate | 3000k | 码率 |

### 调试

```bash
# 直接运行测试
cd 足球
python -m scripts.compose_video
```

---

## 🎤 模块4：TTS (text_to_speech.py)

### 核心函数

```python
from scripts.text_to_speech import run_tts

audio_files, full_audio = run_tts(
    texts=["文案1", "文案2", ...],
    voice="zh-CN-YunxiNeural",  # 男声
    rate="+0%",                  # 语速（+10%~-10%）
    volume="+0%",                # 音量
    enable_ssml=True,
    pitch_variation=True,        # 随机音调变化
)
```

**可用声音：**
- `zh-CN-YunxiNeural` — 男声（推荐）
- `zh-CN-XiaoxiaoNeural` — 女声
- `zh-CN-YunjianNeural` — 男声（更成熟）

**返回：**
- `audio_files`: 每段文案对应的音频文件路径列表
- `full_audio`: 所有文案合并的完整音频路径

---

## 🎭 模块5：表情包/图片

### 生成表情包

```python
# 生成8个搞笑表情包
cd 足球
python -m scripts.gen_emoji
# 输出到 materials/images/emoji/
```

### 下载表情包

```python
cd 足球
python -m scripts.download_memes
# 从百度/必应下载搞笑图片
# 自动过滤：尺寸太小、横幅图、纯色图
```

### 搜图

```python
from scripts.search_images import search_images

image_paths = search_images(scenes, max_per_scene=2)
```

---

## 📤 模块6：多平台发布 (upload.py)

### 登录

```python
from upload import login_all

# 登录所有平台
login_all()

# 仅登录特定平台
login_all(platforms=["douyin", "xiaohongshu"])
```

**CLI：**
```bash
python upload.py                    # 登录全部
python upload.py --only weixin      # 仅登录微信
python upload.py --only douyin,xiaohongshu  # 登录抖音+小红书
```

### 发布

```python
from upload import publish_all

publish_all(
    video_path="output/视频.mp4",
    title="视频标题",
    cover_path="output/封面.png",  # 可选
    description="视频描述",         # 可选
    headless=False,                # 建议False（可视化）
    skip=["微信视频号"],            # 可选跳过
)
```

**CLI：**
```bash
python upload.py video.mp4 "标题"                    # 发布到全部
python upload.py video.mp4 "标题" --no-weixin        # 跳过微信
python upload.py video.mp4 "标题" --no-xhs --no-kuaishou  # 跳过小红书+快手
```

### 平台特殊处理

**抖音：**
- 先去上传页 → 上传视频 → 跳转到发布页 → 填写 → 发布
- AI声明弹窗：自主声明 → 内容为AI生成 → 确定

**小红书：**
- Shadow DOM发布（xhs-publish-btn）
- 自动选择内容类型声明
- 发布后检查笔记管理页

**快手：**
- 多策略标题填写（class匹配 + placeholder + 宽度检测）
- 作者声明 → AI生成
- 发布后弹窗处理（确定/确认/知道了）

**微信视频号：**
- Wujie Shadow DOM处理
- 侧边栏导航（内容管理 → 视频 → 发表视频）
- 声明原创弹窗处理

---

## 🔍 调试技巧

### 查看截图

```python
# upload.py 自动保存截图到 playwright_profile/debug/
# 截图命名规则：
# - nav_*.png — 导航后
# - uploaded_*.png — 上传后
# - ks_ready.png — 快手处理完成
# - ks_timeout.png — 快手等待超时
# - click_fail_*.png — 发布按钮点击失败
```

### 查看页面元素

```python
# 在upload.py中临时添加调试：
print(page.evaluate("document.body.innerHTML[:2000]"))
```

### 常用命令

```bash
# 测试单个模块
python -m scripts.fetch_news
python -m scripts.generate_script
python -m scripts.compose_video

# 测试发布
python upload.py video.mp4 "测试标题" --no-xhs --no-kuaishou --no-weixin