# Version: v1.6.1
import akshare as ak
import pandas as pd
from datetime import datetime
import time
import random
import re

class DataFetcher:
    BLACKLIST = [
        '融资融券', '转融券互通', '深股通', '沪股通', 'MSCI', '标普', '富时', 
        '成分', '重仓', '百元股', '参股', '同花顺', '大盘', '预盈', '预增',
        'AB股', 'AH股', 'HS300', '央视', '证金', '昨高', '昨日',
        '深成', '深证', '上证', '100R', '180', '380', '500', '300',
        '标准普尔', '罗素', '基金', '信托', '创业板', '科创'
    ]

    @staticmethod
    def _rest():
        """强制长休眠：25 ~ 35秒"""
        t = random.uniform(30.0, 35.0)
        print(f"💤 [Fetcher] 冷却 {t:.1f}s ...")
        time.sleep(t)

    @staticmethod
    def _retry_fetch(func, retries=3):
        """通用重试装饰器"""
        for i in range(retries):
            try:
                return func()
            except Exception as e:
                print(f"⚠️ 尝试 {i+1}/{retries} 失败: {e}")
                # t = random.uniform(25.0, 35.0)
                time.sleep(5)
        print("❌ 已放弃该接口请求")
        return None

    @staticmethod
    def get_date_str():
        now = datetime.now()
        return now.strftime("%Y%m%d")

    @staticmethod
    def _fmt_time(val):
        s = str(val).strip()
        if len(s) == 6: return f"{s[:2]}:{s[2:4]}:{s[4:]}"
        if len(s) == 5: return f"0{s[:1]}:{s[1:3]}:{s[3:]}"
        return s

    @staticmethod
    def _clean_concept(df):
        if df.empty: return df
        pattern = '|'.join(DataFetcher.BLACKLIST)
        filtered = df[~df['名称'].str.contains(pattern, regex=True)]
        return filtered

    @staticmethod
    def _fuzzy_search_col(df, keywords):
        if df is None or df.empty: return None
        for col in df.columns:
            if all(k in col for k in keywords):
                return col
        return None

    @staticmethod
    def get_market_data():
        print("⏳ [Fetcher] 获取大盘与情绪...")
        
        def _fetch_idx():
            idx = ak.stock_zh_index_spot_em(symbol="沪深重要指数")
            return idx[idx['名称'].isin(['上证指数', '深证成指', '创业板指', '科创50'])].copy()
            
        def _fetch_sent():
            raw_sent = ak.stock_market_activity_legu()
            raw_sent = raw_sent[~raw_sent['item'].str.contains('st', case=False)]
            sd = {}
            for _, row in raw_sent.iterrows():
                k, v = row['item'], row['value']
                try:
                    if isinstance(v, (int, float)): sd[k] = int(v)
                    elif isinstance(v, str) and '%' in v: sd[k] = v
                    else: sd[k] = int(float(v))
                except: sd[k] = v
            return sd

        # --- 修复点：显式判断 None，避免 DataFrame 布尔值歧义错误 ---
        res_idx = DataFetcher._retry_fetch(_fetch_idx)
        idx = res_idx if res_idx is not None else pd.DataFrame()
        
        DataFetcher._rest()
        
        res_sent = DataFetcher._retry_fetch(_fetch_sent)
        sent_dict = res_sent if res_sent is not None else {}
        
        DataFetcher._rest()
        
        return idx, sent_dict

    @staticmethod
    def get_stock_pools():
        print("⏳ [Fetcher] 获取四大股池...")
        date = DataFetcher.get_date_str()
        pools = {}
        
        def clean_time(df, col):
            if col in df.columns: df[col] = df[col].apply(DataFetcher._fmt_time)
            return df

        # 涨停
        def _fetch_zt():
            zt = ak.stock_zt_pool_em(date=date)
            if not zt.empty:
                if '首次封板时间' in zt.columns:
                    zt = clean_time(zt, '首次封板时间')
                    zt = clean_time(zt, '最后封板时间')
                    zt = zt.sort_values('首次封板时间', ascending=True)
                return zt
            return None
        pools['zt'] = DataFetcher._retry_fetch(_fetch_zt)
        DataFetcher._rest()

        # 跌停
        def _fetch_dt():
            dt = ak.stock_zt_pool_dtgc_em(date=date)
            if not dt.empty:
                return clean_time(dt, '最后封板时间')
            return None
        pools['dt'] = DataFetcher._retry_fetch(_fetch_dt)
        DataFetcher._rest()

        # 炸板
        def _fetch_zb():
            zb = ak.stock_zt_pool_zbgc_em(date=date)
            if not zb.empty:
                if '首次封板时间' in zb.columns:
                    zb = clean_time(zb, '首次封板时间')
                    zb = zb.sort_values('首次封板时间', ascending=True)
                return zb
            return None
        pools['zb'] = DataFetcher._retry_fetch(_fetch_zb)
        DataFetcher._rest()

        # 强势
        def _fetch_st():
            st = ak.stock_zt_pool_strong_em(date=date)
            if not st.empty:
                return st.sort_values('涨跌幅', ascending=False)
            return None
        pools['strong'] = DataFetcher._retry_fetch(_fetch_st)
        DataFetcher._rest()
        
        return pools

    @staticmethod
    def get_fund_flows():
        print("⏳ [Fetcher] 获取资金流 (全量)...")
        flows = {}
        
        def fetch_rank(type_name, sector_type=None):
            def _do():
                if sector_type:
                    df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type=sector_type)
                else:
                    df = ak.stock_individual_fund_flow_rank(indicator="今日")
                
                net_col = DataFetcher._fuzzy_search_col(df, ['净额'])
                if not net_col: raise ValueError("无净额列")
                
                df_sorted = df.sort_values(by=net_col, ascending=False)
                return df_sorted, net_col 

            # --- 修复点：显式判断 None ---
            res = DataFetcher._retry_fetch(_do)
            return res if res is not None else (None, None)

        # 行业
        df, col = fetch_rank("行业", "行业资金流")
        if df is not None: 
            flows['industry'] = df
            flows['industry_col'] = col
        DataFetcher._rest()

        # 概念
        df, col = fetch_rank("概念", "概念资金流")
        if df is not None:
            flows['concept'] = DataFetcher._clean_concept(df)
            flows['concept_col'] = col
        DataFetcher._rest()

        # 地域
        df, col = fetch_rank("地域", "地域资金流")
        if df is not None:
            flows['region'] = df
            flows['region_col'] = col
        DataFetcher._rest()

        # 个股
        try:
            stock = ak.stock_individual_fund_flow_rank(indicator="今日")
            net_col = DataFetcher._fuzzy_search_col(stock, ['主力', '净额'])
            if net_col:
                flows['stock'] = stock.sort_values(by=net_col, ascending=False)
                flows['stock_col'] = net_col
        except: pass
        DataFetcher._rest()
            
        return flows