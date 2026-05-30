from openai import OpenAI
import json, re

SYSTEM_PROMPT = """你是一个消防考证科普短视频的脚本写手。
你的风格：接地气、专业但不枯燥，用大白话讲消防知识和考证干货。

每次输出一个短视频脚本，格式为 JSON：

{
  "title": "封面标题，12个字以内，够吸引人",
  "hook": "开场5秒，吸引注意，抛出痛点或问题",
  "scenes": [
    {
      "text": "每句配音文案，6-15个字最佳",
      "image_desc": "对应的画面描述"
    }
  ],
  "outro": "结尾引流话术"
}

要求：
- 总时长25-35秒
- scenes 数组 6-8 条
- 每条 scene 文案 6-12 个字优先，最长不超过18个字
- 不要写新闻导语，开头先抛问题或痛点
- 文案像朋友聊天，不要书面腔
- 每句只表达一个知识点，适合短视频快切
- 画面描述要具体，每句配一个画面
- 主题围绕消防证、消防工程师、消防设施操作员、消防安全知识、火灾逃生等
- 结尾话术必须是："想考消防证的朋友，加我咨询详情！"

请直接返回纯 JSON，不要 markdown 代码块。"""

RETRY_PROMPT = """你返回的不是有效 JSON。请只返回纯 JSON 对象，不要任何其他文字，不要 markdown 代码块。

格式要求：
{
  "title": "字符串",
  "hook": "字符串",
  "scenes": [{"text": "字符串", "image_desc": "字符串"}],
  "outro": "字符串"
}

再次强调：
总时长25-35秒，scenes 6-8条，结尾话术: "想考消防证的朋友，加我咨询详情！"
"""

def _clean_text(text):
    text = (text or "").strip()
    text = re.sub(r"\s+", "", text)
    text = text.strip('"“”')
    return text

def _split_to_bursts(text, max_len=14):
    text = _clean_text(text)
    if not text:
        return []
    parts = re.split(r"[，,。！？!？：:；;、\n]+", text)
    bursts = []
    for part in parts:
        part = _clean_text(part)
        if not part:
            continue
        if len(part) <= max_len:
            bursts.append(part)
            continue
        start = 0
        while start < len(part):
            end = min(start + max_len, len(part))
            chunk = part[start:end]
            if chunk:
                bursts.append(chunk)
            start = end
    return bursts

def _normalize_script(data):
    title = _clean_text(data.get("title") or "消防考证知识")[:12]
    hook_candidates = _split_to_bursts(data.get("hook") or title, max_len=16)
    hook = hook_candidates[0] if hook_candidates else title

    raw_scenes = data.get("scenes") or []
    scene_pool = []
    for scene in raw_scenes:
        text = _clean_text(scene.get("text"))
        if not text:
            continue
        image_desc = _clean_text(scene.get("image_desc")) or text
        for burst in _split_to_bursts(text, max_len=14):
            scene_pool.append({"text": burst, "image_desc": image_desc})

    if len(scene_pool) < 6:
        hook_tail = hook_candidates[1:] if len(hook_candidates) > 1 else []
        for burst in hook_tail:
            scene_pool.append({"text": burst, "image_desc": burst})
            if len(scene_pool) >= 6:
                break

    scenes = scene_pool[:8]
    if len(scenes) < 6:
        fallback = [
            {"text": "消防证含金量有多高", "image_desc": "消防证证书特写"},
            {"text": "考过就是铁饭碗", "image_desc": "消防工程师工作场景"},
            {"text": "报考条件有哪些", "image_desc": "报考条件列表"},
            {"text": "考试内容难不难", "image_desc": "考生学习备考画面"},
            {"text": "通过率其实不低", "image_desc": "考试通过率数据图"},
            {"text": "想考消防证的朋友，加我咨询详情！", "image_desc": "联系方式二维码"},
        ]
        scenes.extend(fallback[: max(0, 6 - len(scenes))])

    outro = "想考消防证的朋友，加我咨询详情！"

    return {
        "title": title,
        "hook": hook,
        "scenes": scenes,
        "outro": outro,
        "target_duration": 30,
        "style": "short_burst",
    }

def generate_script(news_summary, client, model="deepseek-chat", timeout=120):
    user_msg = f"今天的消防相关话题如下，请以此素材写一条消防考证科普短视频脚本：\n\n{news_summary}"

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg if attempt == 0 else f"{user_msg}\n\n{RETRY_PROMPT}"},
                ],
                temperature=0.7 if attempt == 0 else 0.3,
                timeout=timeout,
            )
        except Exception as e:
            if attempt < 2:
                continue
            raise

        content = resp.choices[0].message.content.strip()
        content = re.sub(r'^```(?:json)?\s*\n?', '', content)
        content = re.sub(r'\n?\s*```$', '', content)

        try:
            return _normalize_script(json.loads(content))
        except json.JSONDecodeError as e:
            if attempt < 2:
                continue
            raise

    raise RuntimeError("脚本生成失败：JSON 解析错误")

if __name__ == "__main__":
    import os, sys, tomllib
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from scripts.fetch_news import fetch_news, format_news_summary
    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.toml"), "rb") as f:
        cfg = tomllib.load(f)["llm"]
    client = OpenAI(api_key=cfg["api_key"], base_url=cfg.get("base_url", "https://api.openai.com/v1"))
    news = fetch_news()
    summary = format_news_summary(news)
    script = generate_script(summary, client, model=cfg["model"])
    print(json.dumps(script, ensure_ascii=False, indent=2))
