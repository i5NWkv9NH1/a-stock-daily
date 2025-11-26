import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import telebot

# 1. 加载环境变量
# 这里必须指明 .env 的路径，防止找不到
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("TG_BOT_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

if not TOKEN:
    print("❌ 错误: .env 文件里没填 TG_BOT_TOKEN")
    sys.exit(1)

# 2. 初始化机器人
bot = telebot.TeleBot(TOKEN)

# (可选) 如果你开了 VPN 但 Python 连不上，可能需要手动设置代理
# from telebot import apihelper
# apihelper.proxy = {'https': 'http://127.0.0.1:7890'} # 这里的端口看你 VPN 软件的设置

def run_test():
    print(f"尝试连接 Telegram... Token: {TOKEN[:5]}***")
    
    try:
        # 获取机器人信息，测试连接
        me = bot.get_me()
        print(f"✅ 连接成功! 机器人名: {me.username}")
        
        if not CHAT_ID:
            print("⚠️ 没填 Chat ID，跳过发送测试。")
            return

        # 发送测试消息
        print(f"正在向 ID {CHAT_ID} 发送消息...")
        bot.send_message(CHAT_ID, "🚀 A股机器人链路测试成功！\n\n来自 Python 本地的问候。")
        print("✅ 消息已发送，请检查手机。")

    except Exception as e:
        print(f"❌ 失败: {e}")
        print("💡 提示: 如果是 ConnectionError，请检查你的 VPN 是否开启了 TUN 模式，或者在代码里配置代理。")

if __name__ == "__main__":
    run_test()