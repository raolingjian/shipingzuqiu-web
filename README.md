# 🎬 视频创作系统 (shipingzuqiu-web)

> AI驱动的短视频制作流水线：新闻抓取 → AI脚本 → 视频合成 → 多平台发布

## 📁 项目结构

```
shipingzuqiu-web/
├── admin/                  # Web管理面板（Supabase + 前端）
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── app.js          # 应用主逻辑
│       └── supabase.js     # Supabase API
│
├── automation/             # 短视频自动化系统
│   ├── football/           # 足球吃瓜短视频（主项目）
│   ├── education/          # 消防考证培训
│   └── bilibili/           # B站教程频道
│
├── docs/                   # 工作流文档
│   ├── workflow.md         # 完整工作流说明
│   └── reference.md        # 技术参考文档
│
└── README.md               # 本文件
```

## 🔄 工作流

1. **新闻抓取** → `fetch_news.py`
2. **AI脚本生成** → `generate_script.py`（DeepSeek/OpenAI）
3. **视频素材下载** → `download_videos.py`（B站视频+切片）
4. **TTS语音合成** → `text_to_speech.py`（Edge TTS）
5. **视频合成** → `compose_video.py`（MoviePy）
6. **封面生成** → `make_cover.py`
7. **多平台发布** → `upload.py`（抖音/小红书/快手/微信视频号）

## 🚀 快速开始

```bash
# 安装依赖
pip install openai edge-tts moviepy pillow requests beautifulsoup4 yt-dlp imageio-ffmpeg icrawler playwright

# 足球主题视频
cd automation/football
python main.py

# 批量模式（一次生成3个视频）
python main.py --batch

# 本地Ollama模型
python main.py --ollama

# B站教程视频
cd automation/bilibili
python main.py 0    # 制作第1集
python main.py login # 登录B站
```

## ⚙️ 配置

复制 `config.example.toml` 为 `config.toml`，填入你的 API Key：

```toml
[llm]
api_key = "sk-your-api-key-here"
base_url = "https://api.deepseek.com"
model = "deepseek-chat"
```

## 🎯 子项目

| 项目 | 说明 | 主题 |
|------|------|------|
| football | 主项目 | 足球吃瓜（多主题：校园/职场/情感/星座） |
| education | 子项目 | 消防考证培训科普 |
| bilibili | 频道 | 游戏策划转型AI实战教程 |

## 📋 更新日志

### 2026-05-29
- ✅ 修复字幕显示问题（自动字体检测）
- ✅ 修复快手标题/简介填写问题
- ✅ 修复微信视频号登录状态保存
- ✅ 新增B站视频产出系统
- ✅ 代码整理并上传GitHub
