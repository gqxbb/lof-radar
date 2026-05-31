import streamlit as st
import akshare as ak
import os
import datetime
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# 强行忽略代理
os.environ['NO_PROXY'] = 'eastmoney.com,sinajs.cn'

st.set_page_config(page_title="海外LOF套利雷达", layout="wide")

# 1. 🌟 新增核心逻辑：让网页右上角的时间每 10 秒钟自动刷新一次（既能看到最新时间，又不会频繁轰炸东财接口）
st_autorefresh(interval=10000, key="dataclock")

# 2. 注入高档深色系 CSS 样式表
st.markdown("""
    <style>
    .stApp { background-color: #121826; color: #F3F4F6; }
    .time-banner { 
        background: linear-gradient(135deg, #1E3A8A, #3B82F6); 
        padding: 15px; 
        border-radius: 8px; 
        margin-bottom: 20px; 
        text-align: center;
        border: 1px solid #60A5FA;
    }
    .time-text { font-size: 22px; font-weight: bold; color: #FFFFFF; font-family: monospace; }
    .remind-text { font-size: 14px; color: #E0F2FE; margin-top: 5px; font-weight: bold; }
    .lof-card { background-color: #1F2937; padding: 20px; border-radius: 10px; margin-bottom: 15px; border-left: 5px solid #EF4444; }
    .lof-title { color: #F3F4F6; font-size: 18px; font-weight: bold; }
    .premium-text { color: #EF4444; font-size: 20px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# 3. 🌟 核心视觉升级：在网页最顶端渲染“时间与战术提醒横幅”
now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"""
    <div class="time-banner">
        <div class="time-text">🕒 当前系统时间：{now_time}</div>
        <div class="remind-text">⚡ 提醒：每个交易日【14:30】点击下方按钮可观看实时数据，抓取盘中最后半小时的黄金决战期溢价！</div>
    </div>
""", unsafe_allow_html=True)

st.title("🦅 搞钱小本本的 LOF 溢价雷达")
st.caption("全自动大浪淘沙 • 实时过滤已暂停申购的品种")

if st.button("🔄 立即刷新全市场数据", type="primary"):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    with st.spinner("正在全力检索全市场数据并生成报告..."):
        overseas_keywords = ["纳斯", "标普", "原油", "油气", "商品", "互联", "中概", "日经", "德国", "法国", "印度", "越南", "亚洲", "全球", "海外"]
        premium_threshold = 3.0
        
        is_market_open = True
        fund_df = None

        try:
            fund_df = ak.fund_lof_spot_em()
            if '盘中估值' not in fund_df.columns or fund_df['溢价率'].isnull().all():
                raise ValueError("当前非实时交易时间")
        except Exception as e:
            is_market_open = False
            try:
                raw_df = ak.fund_lof_spot_em()
                em_nav_df = ak.fund_open_fund_daily_em()
                
                if not raw_df.empty and not em_nav_df.empty:
                    em_nav_df.rename(columns={'基金代码': '基金代码', '单位净值': '最新净值', '累计净值': '最新累计净值'}, inplace=True)
                    merged_df = pd.merge(raw_df, em_nav_df[['基金代码', '最新净值', '最新累计净值']], on='基金代码', how='inner')
                    
                    merged_df['现价'] = pd.to_numeric(merged_df['现价'], errors='coerce')
                    merged_df['最新净值'] = pd.to_numeric(merged_df['最新净值'], errors='coerce')
                    merged_df['真实收盘溢价率'] = (merged_df['现价'] - merged_df['最新净值']) / merged_df['最新净值'] * 100
                    
                    fund_df = merged_df
            except Exception as e_inner:
                pass

        if fund_df is not None and not fund_df.empty:
            total_scanned = len(fund_df)

            if is_market_open:
                st.success(f"📊 LOF 溢价及流动性雷达（盘中实时版） | 统计时间: {current_time}")
            else:
                st.info(f"📢 当前非交易时间，已自动激活【盘后精确复盘算法】")
            
            st.write(f"**当前过滤规则**：溢价率 $\\ge$ {premium_threshold}%，且【开放场外申购】。已自动拦截暂停申购品种。")
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            cards_html_list = []
            count_target = 0

            for index, row in fund_df.iterrows():
                code = str(row['基金代码'])
                name = row['基金简称']
                
                is_overseas = any(keyword in name for keyword in overseas_keywords) or code.startswith("1611") or code.startswith("1649") or code.startswith("501")
                
                if is_overseas:
                    try:
                        if is_market_open:
                            premium = float(row['溢价率'])
                        else:
                            premium = float(row['真实收盘溢价率'])
                        
                        if premium >= premium_threshold:
                            try:
                                limit_info = ak.fund_open_format_xw()
                                matched_fund = limit_info[limit_info['基金代码'] == code]
                                status_desc = matched_fund.iloc[0]['申购状态'] if not matched_fund.empty else "开放申购"
                            except:
                                status_desc = "开放申购"

                            if "暂停申购" in status_desc or "停申" in status_desc or status_desc == "暂停":
                                continue
                            
                            price = float(row['现价'])
                            raw_amount = float(row.get('成交额', 0.0))
                            
                            if code.startswith("50"):
                                amount_wan = raw_amount
                            else:
                                amount_wan = raw_amount / 10000.0
                            
                            count_target += 1
                            
                            card_html = f"""
                            <div class="lof-card">
                                <div class="lof-title">{count_target}. 【{name}】 ({code})</div>
                                <div style="margin-top: 8px;">
                                    <span class="premium-text">{'盘中实时' if is_market_open else '静态收盘'}溢价率：{premium:.2f}%</span>
                                </div>
                                <div style="margin-top: 8px; color: #9CA3AF; font-size: 14px;">
                                    • 场内现价/收盘价：<b style="color: #F3F4F6;">{price:.3f} 元</b> &nbsp;&nbsp;|&nbsp;&nbsp; 
                                    {'场外盘中估值' if is_market_open else '场外最新官方净值'}：<b style="color: #F3F4F6;">{row.get('盘中估值', row.get('最新净值', 0.0)):.4f} 元</b>
                                </div>
                                <div style="margin-top: 4px; color: #9CA3AF; font-size: 14px;">
                                    • 当日场内成交额：<b style="color: #F3F4F6;">{amount_wan:.2f} 万元</b> &nbsp;&nbsp;|&nbsp;&nbsp; 
                                    场外申购状态：<b style="color: #10B981;">✅ {status_desc}</b>
                                </div>
                            </div>
                            """
                            
                            if is_market_open:
                                if amount_wan < 200:
                                    card_html += f'<div style="color: #F59E0B; font-size: 14px; margin-bottom: 15px; font-weight: bold;">⚠️ 实战提示：该品种当日成交额不足 200 万，流动性偏低，注意防范冲击成本。</div>'
                                else:
                                    card_html += f'<div style="color: #10B981; font-size: 14px; margin-bottom: 15px; font-weight: bold;">🔥 实战提示：成交活跃，流动性十分充裕，属于优质套利标的！</div>'
                            
                            cards_html_list.append(card_html)
                    except:
                        continue

            with col1:
                st.metric(label="🗺️ A 股全市场 LOF 扫描总数", value=f"{total_scanned} 只")
            with col2:
                st.metric(label="🎯 溢价率 $\\ge$ 3% 且可申购达标数", value=f"{count_target} 只")
            
            st.markdown("---")

            if count_target == 0:
                st.subheader("⚖️ 市场平静。当前全市场暂未发现符合条件的疯狂品种。☕")
            else:
                for html_content in cards_html_list:
                    st.markdown(html_content, unsafe_allow_html=True)
                st.info("💡 提示：电脑端可直接拖动鼠标复制卡片文本，手机端长按即可选择复制文字发至微信群。")
        else:
            st.warning("☕ 📢 提示：当前正值周末/节假日交易所系统清算期，官方历史数据源临时闭门维护。")
            st.info("💡 本雷达将于【明天（周一）开盘后】全面恢复全自动实时扫盘，届时请点击上方按钮刷新。")
