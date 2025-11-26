# Version: v1.9.0
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
import io
import re
from src.config import Config

# --- 强制字体加载逻辑 ---
# 在 Linux (Github Actions) 上，这是唯一稳妥的方法
FONT_PROP = None
try:
    if Config.FONT_PATH.exists():
        # 直接加载文件，创建一个全局的字体属性对象
        FONT_PROP = fm.FontProperties(fname=str(Config.FONT_PATH))
        print(f"✅ [Renderer] Loaded font from: {Config.FONT_PATH}")
    else:
        # 兜底：尝试系统字体 (本地调试用)
        print(f"⚠️ [Renderer] Font not found at {Config.FONT_PATH}, trying system default.")
        FONT_PROP = fm.FontProperties(family=['SimHei', 'Arial Unicode MS', 'PingFang SC'])
except Exception as e:
    print(f"❌ [Renderer] Font loading failed: {e}")

plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['savefig.facecolor'] = '#191b1f'

class Style:
    BG = '#191b1f'
    HEADER_BG = '#212529'
    ROW_A = '#191b1f'
    ROW_B = '#202226'
    TEXT_MAIN = '#e9ecef'
    TEXT_SUB = '#adb5bd'
    RED = '#ff6b6b'
    GREEN = '#33d9b2'
    GOLD = '#fcc419'
    BLUE = '#4fa3d1'
    PURPLE = '#a55eea'

class ProRenderer:
    def _save(self):
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', pad_inches=0.1)
        buf.seek(0)
        plt.close()
        return buf

    def _clean_title(self, text):
        return re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s\(\)]', '', text).strip()

    def _draw_header(self, ax, title):
        clean = self._clean_title(title)
        # ⚠️ 关键修改：fontproperties=FONT_PROP
        ax.text(0.5, 1.01, clean, ha='center', va='bottom', fontsize=16, 
                color=Style.TEXT_MAIN, fontweight='bold', transform=ax.transAxes,
                fontproperties=FONT_PROP) # <---
        ax.plot([0, 1], [1.005, 1.005], color=Style.GOLD, linewidth=2, transform=ax.transAxes)

    def draw_table(self, df, title, cols_map):
        if df is None or df.empty: return None

        data = df.copy()
        valid_cols = []
        new_names = []
        for k, v in cols_map.items():
            if k in data.columns:
                valid_cols.append(k)
                new_names.append(v)
        
        if not valid_cols: return None
        data = data[valid_cols]
        data.columns = new_names
        data = data.astype(object)

        # ... (数据格式化逻辑保持不变，为了节省篇幅省略，请保留 v1.8.0 的逻辑) ...
        # 复制 v1.8.0 的格式化循环代码到这里
        for c in data.columns:
            if any(k in c for k in ['封单', '资金', '市值', '额', '流值']):
                try:
                    vals = pd.to_numeric(data[c], errors='coerce')
                    mask = vals.notna()
                    data.loc[mask, c] = vals[mask].apply(lambda x: f"{x/100000000:.2f}亿")
                except: pass
            elif any(k in c for k in ['涨跌幅', '换手']):
                try:
                    vals = pd.to_numeric(data[c], errors='coerce')
                    mask = vals.notna()
                    if '涨跌' in c or '幅' in c:
                        data.loc[mask, c] = vals[mask].apply(lambda x: f"+{x:.2f}%" if x>0 else f"{x:.2f}%")
                    else:
                        data.loc[mask, c] = vals[mask].apply(lambda x: f"{x:.2f}%")
                except: pass
            elif '现价' in c or '价' in c:
                try:
                    vals = pd.to_numeric(data[c], errors='coerce')
                    mask = vals.notna()
                    data.loc[mask, c] = vals[mask].apply(lambda x: f"{x:.2f}")
                except: pass

        rows, cols = data.shape
        h = max(rows * 0.4 + 1.2, 3) 
        fig, ax = plt.subplots(figsize=(12, h), facecolor=Style.BG)
        ax.axis('off')
        
        self._draw_header(ax, title)

        table = ax.table(cellText=data.values, colLabels=data.columns, 
                         loc='center', cellLoc='center', bbox=[0, 0, 1, 1])

        table.auto_set_font_size(False)
        table.set_fontsize(10)
        
        # ⚠️ 关键修改：遍历所有单元格设置字体
        for (row, col), cell in table.get_celld().items():
            cell.set_linewidth(0)
            # 强制设置字体属性
            cell.set_text_props(fontproperties=FONT_PROP) # <---
            
            if row == 0:
                cell.set_facecolor(Style.HEADER_BG)
                cell.set_text_props(color=Style.TEXT_SUB, weight='bold', fontproperties=FONT_PROP)
                cell.set_height(0.06)
            else:
                bg = Style.ROW_A if row % 2 != 0 else Style.ROW_B
                cell.set_facecolor(bg)
                cell.set_text_props(color=Style.TEXT_MAIN, fontproperties=FONT_PROP)
                cell.set_height(0.05)
                
                val = str(cell.get_text().get_text())
                col_name = data.columns[col]
                
                # ... (颜色逻辑保持不变) ...
                if '涨跌' in col_name or '幅' in col_name:
                    if '-' in val: cell.set_text_props(color=Style.GREEN)
                    elif '0.00' not in val: cell.set_text_props(color=Style.RED)
                if '连板' in col_name:
                    try:
                        v_num = int(re.sub(r'\D', '', val))
                        if v_num >= 3: cell.set_text_props(color=Style.GOLD, weight='bold')
                    except: pass
                if '理由' in col_name:
                    if '新高' in val: cell.set_text_props(color=Style.BLUE)
                    elif '涨停' in val: cell.set_text_props(color=Style.PURPLE)

        return self._save()

    def draw_bar_chart(self, df, title, val_col_name=None):
        if df is None or df.empty: return None
        
        if not val_col_name or val_col_name not in df.columns:
            found = [c for c in df.columns if '净额' in c]
            if not found: return None
            val_col_name = found[0]
            
        df = df.head(30).copy() 
        df['val_yi'] = df[val_col_name] / 100000000
        
        h = max(len(df) * 0.4 + 1.2, 4)
        fig, ax = plt.subplots(figsize=(9, h), facecolor=Style.BG)
        ax.set_facecolor(Style.BG)
        
        self._draw_header(ax, title)
        
        y_pos = range(len(df))
        colors = [Style.RED if x > 0 else Style.GREEN for x in df['val_yi']]
        
        bars = ax.barh(y_pos, df['val_yi'], color=colors, height=0.6)
        
        name_col = '名称' if '名称' in df.columns else '行业'
        if name_col not in df.columns: name_col = df.columns[0]

        ax.set_yticks(y_pos)
        # ⚠️ 关键修改：设置 Y 轴标签字体
        ax.set_yticklabels(df[name_col], color=Style.TEXT_MAIN, fontsize=10, fontproperties=FONT_PROP) # <---
        ax.invert_yaxis()
        
        for spine in ax.spines.values(): spine.set_visible(False)
        ax.tick_params(left=False, bottom=False, labelbottom=False)
        
        # ⚠️ 关键修改：设置数值标签字体
        ax.bar_label(bars, fmt='%.1f亿', padding=5, color=Style.TEXT_SUB, fontsize=9, fontproperties=FONT_PROP) # <---
        
        return self._save()