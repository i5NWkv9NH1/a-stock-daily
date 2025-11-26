# Version: v1.8.0
import telebot
from telebot.types import InputMediaPhoto
from src.config import Config
from src.fetcher import DataFetcher
from src.renderer import ProRenderer
import pandas as pd
from datetime import datetime
import time
import sys

# --- 配置 ---
COLS_CONFIG = {
    'zt': {
        '代码': '代码', '名称': '名称', '涨跌幅': '涨跌幅', '最新价': '现价', 
        '首次封板时间': '首封', '最后封板时间': '回封', '炸板次数': '炸',
        '封板资金': '封单', '连板数': '连板', '所属行业': '行业'
    },
    'dt': {
        '代码': '代码', '名称': '名称', '涨跌幅': '涨跌幅', '最新价': '现价', 
        '连续跌停': '连跌', '所属行业': '行业', '最后封板时间': '封单时间'
    },
    'zb': {
        '代码': '代码', '名称': '名称', '涨跌幅': '涨跌幅', '最新价': '现价', 
        '首次封板时间': '首封', '炸板次数': '炸', '所属行业': '行业'
    },
    'strong': {
        '代码': '代码', '名称': '名称', '涨跌幅': '涨跌幅', '最新价': '现价',
        '换手率': '换手', '流通市值': '流值', '入选理由': '理由', '所属行业': '行业'
    }
}

bot = telebot.TeleBot(Config.TG_BOT_TOKEN) if Config.TG_BOT_TOKEN else None

def escape_markdown_v2(text):
    special_chars = r'_*[]()~`>#+-=|{}.!'
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def get_market_session():
    h = datetime.now().hour
    if 0 <= h < 9: return "收盘复盘"
    if 9 <= h < 11: return "早盘观测"
    if 11 <= h < 15: return "午盘速递"
    return "收盘复盘"

def job():
    print(f"\n🚀 [Job] 开始执行任务: {datetime.now()}")
    session = get_market_session()
    
    # 1. Fetch
    idx_df, sent_dict = DataFetcher.get_market_data()
    pools = DataFetcher.get_stock_pools()
    flows = DataFetcher.get_fund_flows()
    
    # 2. Text
    date_str = pd.Timestamp.now().strftime('%Y-%m-%d')
    idx_text = ""
    if not idx_df.empty:
        idx_text += "```text\n"
        for _, row in idx_df.iterrows():
            pct = row['涨跌幅']
            icon = "🔴" if pct > 0 else "🟢"
            amt = row.get('成交额', 0) / 100000000
            idx_text += f"{icon} {row['名称'][:4]:<4} {row['最新价']:>7.2f} {pct:>+6.2f}% {amt:>5.0f}亿\n"
        idx_text += "```"

    up = sent_dict.get('上涨', 0)
    down = sent_dict.get('下跌', 0)
    zt = sent_dict.get('涨停', 0)
    dt = sent_dict.get('跌停', 0)
    
    header = escape_markdown_v2(f"📅 {date_str} A股{session}")
    sep = escape_markdown_v2("────────────────")
    sent_line1 = escape_markdown_v2(f"📈 上涨: {up}    📉 下跌: {down}")
    sent_line2 = escape_markdown_v2(f"🔥 涨停: {zt}      ❄️ 跌停: {dt}")
    tags = escape_markdown_v2(f"#A股 #{session}")

    caption = (
        f"*{header}*\n{sep}\n\n{idx_text}\n"
        f"*{escape_markdown_v2('🌡️ 市场温控')}*\n"
        f"{sent_line1}\n{sent_line2}\n\n{tags}"
    )

    # 3. Render
    print("🎨 渲染图表...")
    renderer = ProRenderer()
    media_group = []

    for pool_key, title in [('zt','涨停梯队'), ('zb','炸板统计'), ('dt','跌停名单'), ('strong','强势股池')]:
        if pool_key in pools:
            img = renderer.draw_table(pools[pool_key], title, COLS_CONFIG[pool_key])
            if img: 
                cap = caption if not media_group else "" 
                media_group.append(InputMediaPhoto(img.getvalue(), caption=cap, parse_mode="MarkdownV2"))

    for flow_key, title in [('industry','行业资金流'), ('concept','概念资金流'), ('region','地域资金流'), ('stock','个股主力资金')]:
        if flow_key in flows:
            img = renderer.draw_bar_chart(flows[flow_key], title, flows.get(f'{flow_key}_col'))
            if img:
                cap = caption if not media_group else ""
                media_group.append(InputMediaPhoto(img.getvalue(), caption=cap, parse_mode="MarkdownV2"))

    # 4. Send
    if media_group and bot:
        print(f"📤 发送 {len(media_group)} 张图片...")
        try:
            bot.send_media_group(Config.TG_CHAT_ID, media_group)
            print("✅ 完成")
        except Exception as e:
            print(f"❌ 发送失败: {e}")
    else:
        print("⚠️ 跳过发送")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
        print("🕒 已启动定时调度模式 (按 Ctrl+C 退出)")
        # 简单调度逻辑：每分钟检查一次时间
        # 目标时间点：10:00, 11:30, 15:05
        # 避免重复发送：记录上次发送日期+时段
        last_sent = ""
        
        while True:
            now = datetime.now()
            current_tag = ""
            
            # 简单时间窗口匹配
            if now.hour == 10 and 0 <= now.minute <= 5: current_tag = f"{now.date()}_1000"
            elif now.hour == 11 and 30 <= now.minute <= 35: current_tag = f"{now.date()}_1130"
            elif now.hour == 15 and 5 <= now.minute <= 10: current_tag = f"{now.date()}_1505"
            
            if current_tag and current_tag != last_sent:
                job()
                last_sent = current_tag
                print("💤 任务完成，继续待机...")
            
            time.sleep(60) # 每分钟检查一次
    else:
        job()

if __name__ == "__main__":
    main()