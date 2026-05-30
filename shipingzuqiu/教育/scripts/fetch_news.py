import os, re, json, requests
from datetime import datetime

CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "materials", "news_cache.json")

def _fetch_baidu_news(keywords=None):
    articles = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    kw = keywords or ["消防证", "消防工程师", "消防设施操作员", "消防安全", "消防知识"]
    try:
        for keyword in kw:
            url = f"https://news.baidu.com/ns?word={requests.utils.quote(keyword)}&tn=news"
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = "utf-8"
            html = resp.text
            pattern = r'<a[^>]*href="(https?://[^"]*)"[^>]*>(.*?)</a>'
            matches = re.findall(pattern, html, re.DOTALL)
            seen = set()
            for link, title_html in matches:
                title = re.sub(r'<[^>]+>', '', title_html).strip()
                if not title or len(title) < 6 or title in seen:
                    continue
                seen.add(title)
                articles.append({"title": title, "source": "百度新闻", "url": link})
    except Exception as e:
        print(f"  [百度] 抓取失败: {e}")
    return articles

def _fetch_sogou(keywords=None):
    articles = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    kw = keywords or ["消防证 考试", "消防工程师 报名", "消防安全 知识"]
    try:
        for keyword in kw:
            url = f"https://www.sogou.com/sogou?query={requests.utils.quote(keyword)}"
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = "utf-8"
            html = resp.text
            pattern = r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>'
            matches = re.findall(pattern, html, re.DOTALL)
            seen = set()
            for link, title_html in matches:
                title = re.sub(r'<[^>]+>', '', title_html).strip()
                if not title or len(title) < 6 or title in seen:
                    continue
                seen.add(title)
                articles.append({"title": title, "source": "搜狗", "url": link})
    except Exception as e:
        print(f"  [搜狗] 抓取失败: {e}")
    return articles

def _fallback_news():
    return [
        {"title": "消防工程师证书含金量有多高？2025年考证必看", "source": "话题库", "url": ""},
        {"title": "消防设施操作员证怎么考？报考条件全解析", "source": "话题库", "url": ""},
        {"title": "高层建筑火灾如何逃生？这些保命知识要牢记", "source": "话题库", "url": ""},
        {"title": "消防证报考流程及费用，新手小白必看指南", "source": "话题库", "url": ""},
        {"title": "消防工程师考试通过率揭秘，备考方法分享", "source": "话题库", "url": ""},
    ]

def format_news_summary(articles):
    if not articles:
        return "今天暂时没有找到消防相关热点，可以用常青话题来聊聊消防考证知识"
    lines = [f"{i+1}. [{a['source']}] {a['title']}" for i, a in enumerate(articles)]
    return "\n".join(lines)

def fetch_news(max_results=10, keywords=None):
    all_articles = []
    all_articles.extend(_fetch_baidu_news(keywords))
    all_articles.extend(_fetch_sogou(keywords))
    seen = set()
    unique = []
    for a in all_articles:
        if a["title"] not in seen:
            seen.add(a["title"])
            unique.append(a)
    if not unique:
        unique = _fallback_news()
    return unique[:max_results]

if __name__ == "__main__":
    news = fetch_news()
    print(format_news_summary(news))
