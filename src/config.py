# Version: v1.0.0
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
    TG_CHAT_ID = os.getenv("TG_CHAT_ID")
    
    # 字体路径：请确保 src 目录下有 SimHei.ttf
    # 如果没有，去下载一个！否则中文必乱码
    FONT_PATH = Path(__file__).parent / "SimHei.ttf" 
    
    # 调试模式：如果为 True，不发送 TG，只生成图片到本地 data 目录
    DEBUG = False