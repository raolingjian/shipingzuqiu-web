# 🎬 短视频自动化系统 — 完整工作流

> AI驱动的短视频制作流水线：新闻抓取 → AI脚本 → 视频合成 → 多平台发布

---

## 📁 项目结构

```
shipingzuqiu/
├── 足球/                          ← 主项目（支持多主题）
│   ├── main.py                    ← 主入口（支持 --batch --ollama --config）
│   ├── config.toml                ← 多主题配置（5个主题）
│   ├── upload.py                  ← 多平台发布（抖音/小红书/快手/微信）
│   ├── scripts/
│   │   ├── fetch_news.py          ← 新闻抓取（新浪/百度/懂球帝/虎扑/搜狗）
│   │   ├── generate_script.py     ← AI脚本生成（DeepSeek/OpenAI）
│   │   ├── download_videos.py     ← B站视频下载+切片
│   │   ├── text_to_speech.py      ← Edge TTS语音合成
│   │   ├── compose_video.py       ← MoviePy视频合成
│   │   ├── make_cover.py          ← 封面生成
│   │   ├── search_images.py       ← 图片搜索（百度/必应）
│   │   ├── download_memes.py      ← 表情包下载
│   │   ├── gen_emoji.py           ← 表情包生成
│   │   └── publish.py             ← Selenium旧版发布
│   ├── fonts/                     ← 字体目录
│   ├── materials/                 ← 素材目录
│   │   ├── audio/                 ← BGM音频
│   │   ├── clips/                 ← 视频片段缓存
│   │   └── images/                ← 表情包/图片
│   └── output/                    ← 输出目录
│
├── 教育/                          ← 子项目（消防考证）
│   ├── main.py                    ← 主入口
│   ├── config.toml                ← 配置
│   ├── upload.py                  ← 导入足球/upload.py
│   └── scripts/                   ← 同足球结构
│
└── B站/                           ← B站教程频道（新建）
    ├── main.py                    ← 主入口
    ├── config.toml                ← 配置
    └── scripts/
        ├── fetch_news.py          ← AI行业热点抓取
        ├── generate_script.py     ← 教程脚本生成
        ├── compose_video.py       ← 长视频合成
        └── text_to_speech.py      ← TTS
```

---

## 🔄 完整工作流

### 阶段1：新闻抓取

```python
# 足球主题
from scripts.fetch_news import fetch_news, format_news_summary
news = fetch_news(max_results=10, sources=["sina", "baidu", "dongqiudi", "hupu", "sogou"])

# 教育主题（消防）
from scripts.fetch_news import fetch_news
news = fetch_news(max_results=10, keywords=["消防证", "消防工程师"])

# 多主题模式（config.toml中配置）
# football/campus/workplace/emotional/horoscope
```

**数据源：**
- 足球：新浪体育、百度新闻、懂球帝API、虎扑、搜狗搜索
- 教育：百度新闻、搜狗搜索
- 常青话题库（网络失败时的备选）

### 阶段2：AI脚本生成

```python
from openai import OpenAI
from scripts.generate_script import generate_script

client = OpenAI(api_key="sk-xxx", base_url="https://api.deepseek.com")
script = generate_script(news_summary, client, model="deepseek-chat")
```

**输出格式：**
```json
{
  "title": "封面标题（10-12字）",
  "hook": "开场5秒钩子",
  "scenes": [
    {"text": "配音文案（6-12字）", "image_desc": "画面描述"}
  ],
  "outro": "结尾引导语",
  "target_duration": 18,
  "style": "short_burst"
}
```

**关键参数：**
- 足球：15-20秒，6-8个场景，每句6-12字
- 教育：25-35秒，6-8个场景，每句6-18字
- B站：不受时间限制，3-10分钟深度内容

### 阶段3：视频素材获取

```python
from scripts.download_videos import download_videos

# 从B站搜索并下载相关视频
clip_results = download_videos(scenes, num_clips=len(scenes))
```

**机制：**
1. 根据关键词搜索B站视频
2. 下载720p视频
3. ffmpeg切片（随机位置，20-32秒）
4. 缓存到materials/clips/
5. 智能复用已下载的片段

### 阶段4：TTS语音合成

```python
from scripts.text_to_speech import run_tts

texts = ["hook文案", "场景1文案", "场景2文案", ...]
audio_files, full_audio = run_tts(
    texts,
    voice="zh-CN-YunxiNeural",  # 男声
    rate="+0%",                  # 语速
    volume="+0%",                # 音量
    pitch_variation=True,        # 音调变化
)
```

**特性：**
- Edge TTS免费，音质好
- 自动静音替代（网络失败时）
- 随机音调变化（更自然）

### 阶段5：视频合成

```python
from scripts.compose_video import compose_video

compose_video(
    script_dict=script,
    audio_files=audio_files,
    full_audio_path=full_audio,
    font_path="fonts/msyh.ttc",
    output_path="output/2026-05-29/视频.mp4",
    bgm_config=bgm_config,
    title=title,
)
```

**合成元素：**
- 🎨 背景：主题风格背景 + meme/表情包
- 🎬 视频片段：随机切片的B站视频
- 📝 字幕：动态上浮字幕 + 底部字幕条
- 🏷️ 标签：左上角主题标签（随机颜色）
- 💬 信息卡片：中上部关键信息卡片
- 📊 进度条：右上角场景进度
- 🎵 BGM：随机选择 + 音量控制

**字幕修复（2026-05-29）：**
- 新增 `_find_font()` 自动检测字体
- 优先级：项目fonts/ → Windows系统字体
- 字体路径：msyh.ttc → NotoSansSC.ttf → simhei.ttf → msyhbd.ttc

### 阶段6：封面生成

```python
from scripts.make_cover import make_cover

cover_path = make_cover(title=title, output_path="cover.png", font_path="font_path")
```

**封面元素：**
- 主题色背景
- 大标题（自动换行）
- 顶部装饰条 + 标签
- 底部CTA文案
- 角落装饰

### 阶段7：多平台发布

```python
from upload import publish_all

publish_all(
    video_path="output/视频.mp4",
    title="视频标题",
    cover_path="output/封面.png",
    description="视频描述",
    headless=False,
    skip=["微信视频号"],  # 可选跳过
)
```

**平台差异：**

| 平台 | 标题 | 简介 | 特殊操作 |
|------|------|------|---------|
| 抖音 | ✅ | ✅ | AI声明→AI生成→确定 |
| 小红书 | ✅ | ✅正文 | Shadow DOM发布 |
| 快手 | ✅ | ✅ | 作者声明→AI生成 |
| 微信视频号 | ✅ | ✅ | Wujie Shadow DOM |

**登录管理：**
```python
# 首次登录（扫码）
python upload.py --only douyin,xiaohongshu

# 全部登录
python upload.py

# 仅发布（跳过登录）
python upload.py video.mp4 "标题"
```

---

## 🎯 多主题系统

config.toml 中配置5个主题：

| 主题 | 新闻源 | 脚本风格 | 适用人群 |
|------|--------|---------|---------|
| football | 新浪/百度/懂球帝/虎扑 | 吃瓜吐槽 | 足球粉丝 |
| campus | B站校园视频 | 干货分享 | 大学生 |
| workplace | B站职场视频 | 生存指南 | 职场人 |
| emotional | B站情感视频 | 感悟分享 | 年轻人 |
| horoscope | B站星座视频 | 运势解读 | 星座爱好者 |

---

## ⚙️ 高级功能

### 批量模式
```bash
# 一次生成3个视频
python main.py --batch
```

### Ollama本地模型
```bash
# 使用本地Ollama模型（免费）
python main.py --ollama
```

### 自定义配置
```bash
# 指定配置文件
python main.py --config my_config.toml
```

### 心流状态
```toml
[flow_state]
states = [
    { name = "creative", bgm_boost = true, duration_modifier = 1.2 },
    { name = "productive", process_optimization = true, parallel_tasks = true },
    { name = "balanced", standard_mode = true },
]
```

---

## 🐛 常见问题

### Q: 字幕不显示
**修复：** compose_video.py 已添加自动字体检测
```bash
# 手动指定字体路径
python main.py --config config.toml
# 确保 fonts/msyh.ttc 或 fonts/NotoSansSC.ttf 存在
```

### Q: 快手标题/简介不填写
**修复：** upload.py 已增加快手专用选择器和宽度匹配逻辑

### Q: 微信视频号登录失败
**修复：** upload.py 已增加微信专用登录URL和检测逻辑

### Q: B站视频下载失败
**原因：** yt-dlp版本过旧或B站反爬
**解决：** `pip install -U yt-dlp`

### Q: 视频合成太慢
**优化：** 
- 减少场景数量（6个以内）
- 降低分辨率（修改config.toml中的resolution）
- 使用ultrafast预设（已默认）

---

## 📝 更新日志

### 2026-05-29
- ✅ 修复字幕显示问题（自动字体检测）
- ✅ 修复快手标题/简介填写问题
- ✅ 修复微信视频号登录状态保存
- ✅ 修复教育项目upload.py导入路径
- ✅ 新增B站视频产出系统规划

### 之前的更新
- 多主题系统（5个主题）
- 批量模式（--batch）
- Ollama本地模型支持（--ollama）
- 心流状态系统
- 封面自动生成
- 微信Wujie Shadow DOM支持