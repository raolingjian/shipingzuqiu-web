import os, sys, importlib.util

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
# 足球子项目里有完整的 upload.py
FOOTBALL_DIR = os.path.join(os.path.dirname(PROJECT_DIR), "足球")

spec = importlib.util.spec_from_file_location("football_upload", os.path.join(FOOTBALL_DIR, "upload.py"))
mod = importlib.util.module_from_spec(spec)
sys.modules["football_upload"] = mod
spec.loader.exec_module(mod)

upload = mod.upload
login_all = mod.login_all
publish_all = mod.publish_all
publish_xiaohongshu = mod.publish_xiaohongshu
