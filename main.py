import streamlit as st
import akshare as ak
import os
import datetime
from datetime import timezone, timedelta
import pandas as pd
import requests

# 强行忽略代理
os.environ['NO_PROXY'] = 'eastmoney.com,sinajs.cn'

# 限制网页最大宽度为黄金分割比例，两边自动留白居中
st.set_page_config(page_title="搞钱小本本的lof溢价雷达", layout="centered")

# 🍏 梁总，请在这里重新贴入你刚才拿到的真实 PDU 字符串钥匙
PUSHDEER_KEY = "你的PushDeerKey写在这里" 

# 注入高档深色系 CSS 样式表
st.markdown("""
    <style>
    .stApp { background-color: #121826; color: #F3F4F6; }
    .stApp h1 { text-align: center; font-size: 32px; font-weight: bold; margin-bottom: 5px; }
    .stApp p { text-align: center; color: #9CA3AF; }
    .time-banner { 
        background: linear-gradient(135deg, #1E3A8A, #3B82F6); 
        padding: 18px; 
        border-radius: 8px; 
        margin-bottom: 25px; 
        text-align: center; 
        border: 1px solid #60A5FA;
    }
    .time-text { font-size: 22px; font-weight: bold; color: #FFFFFF; font-family: monospace; }
    .remind-text { font-size: 14px; color: #E0F2FE; margin-top: 5px; font-weight: bold; }
    .lof-card { 
        background-color: #1F2937; 
        padding: 20px; 
        border-radius: 10px; 
        margin-bottom: 15px; 
        border-left: 5px solid #EF4444;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); 
    }
    .lof-card:hover {
        border-left: 5px solid #F87171;
        background-color: #253147;
        transition: 0.3s;
    }
    .lof-title { color: #F3F4F6; font-size: 18px; font-weight: bold; }
    .premium-text { color: #EF4444; font-size: 20px; font-weight: bold; }
    div.stButton { text-align: center; }
    </style>
""", unsafe_allow_html=True)

# 校准北京时间 (东八区)
SHA_TZ = timezone(timedelta(hours=8))
now = datetime.datetime.now(SHA_TZ)
now_time = now.strftime("%Y-%m-%d %H:%M:%S")

# 将战术横幅固定在最上方
st.markdown(f"""
    <div class="time-banner">
        <div class="remind-text">⚡ 战术铁律：请于每个交易日【14:30】准时点击下方按钮刷新 ⚡</div>
        <div style="font-size: 13px; color: #BFDBFE; margin-top: 3px;">场外申购截单盲区前最后半小时，是捕捉全天疯狂溢价的终极决战期</div>
    </div>
""", unsafe_allow_html=True)

st.title("🦅 搞钱小本本的lof溢价雷达")
st.caption("全自动大浪淘沙 • 实时过滤已暂停申购的品种")
st.write("")

# 利用三列等分画布，强行把按钮卡在正中间列
col_left, col_btn, col_right = st.columns([1, 3, 1])

with col_btn:
    refresh_trigger = st.button("🔄 立即刷新市场LOF数据并生成报告", type="primary", use_container_width=True)

# 核心刷新动作执行逻辑
if refresh_trigger:
    current_time = now.strftime("%Y-%m-%d %H:%M")
    
    with st.spinner("正在全力检索全市场数据并生成报告..."):
        overseas_keywords = ["纳斯", "标普", "原油", "油气", "商品", "互联", "中概", "日经", "德国", "法国", "印度", "越南", "亚洲", "全球", "海外"]
        premium_threshold = 3.0
        
        # 北京时间硬核开闭市状态判定
        is_weekend = now.weekday() >= 5
        time_now = now.time()
        in_morning_trade = datetime.time(9, 15) <= time_now <= datetime.time(11, 30)
        in_afternoon_trade = datetime.time(13, 0) <= time_now <= datetime.time(15, 0)
        
        if not is_weekend and (in_morning_trade or in_afternoon_trade):
            is_market_open = True
        else:
            is_market_open = False
        
        fund_df = None

        if is_market_open:
            try:
                fund_df = ak.fund_lof_spot_em()
            except:
                is_market_open = False
        
        if not is_market_open:
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
            except:
                pass

        if fund_df is not None and not fund_df.empty:
            total_scanned = len(fund_df)

            # 状态提示
            if is_market_open:
                st.success(f"📊 实时扫盘成功 | 数据抓取时间 (北京时间): {now_time}（盘中实时版）")
            else:
                st.info(f"📢 复盘扫盘成功 | 数据抓取时间 (北京时间): {now_time}（已自动激活盘后备用算法）")
            
            st.markdown(f"<p style='text-align: center; color: #9CA3AF;'><b>当前过滤规则</b>：溢价率 ≥ {premium_threshold}%，且【开放场外申购】。已自动拦截暂停申购品种。</p>", unsafe_allow_html=True)
            st.markdown("---")
            
            # 渲染大看板指标
            col1, col2 = st.columns(2)
            
            count_target = 0
            valid_rows = []
            push_text = ""
            
            for index, row in fund_df.iterrows():
                code = str(row['基金代码'])
                name = row['基金简称']
                is_overseas = any(keyword in name for keyword in overseas_keywords) or code.startswith("1611") or code.startswith("1649") or code.startswith("501")
                
                if is_overseas:
                    try:
                        premium = float(row['溢价率']) if is_market_open else float(row['真实收盘溢价率'])
                        if premium >= premium_threshold:
                            try:
                                limit_info = ak.fund_open_format_xw()
                                matched_fund = limit_info[limit_info['基金代码'] == code]
                                status_desc = matched_fund.iloc[0]['申购状态'] if not matched_fund.empty else "开放申购"
                            except:
                                status_desc = "开放申购"

                            if "暂停申购" in status_desc or "停申" in status_desc or status_desc == "暂停":
                                continue
                                
                            count_target += 1
                            valid_rows.append((row, premium, status_desc))
                            
                            # 组装推送文本摘要
                            push_text += f"{count_target}. {name}({code}) | 溢价率:{premium:.2f}% | 状态:{status_desc}\n"
                    except:
                        continue

            with col1:
                st.metric(label="🗺️ A 股全市场 LOF 扫描总数", value=f"{total_scanned} 只")
            with col2:
                st.metric(label="🎯 溢价率 $\\ge$ 3% 且可申购达标数", value=f"{count_target} 只")
            
            st.markdown("---")

            # 原地渲染卡片
            if count_target == 0:
                st.markdown("<h3 style='text-align: center; color: #9CA3AF;'>⚖️ 市场平静。当前全市场暂未发现符合条件的疯狂品种。☕</h3>", unsafe_allow_html=True)
            else:
                # 🍏 【触发微信推送】
                if PUSHDEER_KEY and PUSHDEER_KEY != "你的PushDeerKey写在这里":
                    try:
                        push_title = f"🦅 搞钱小本本发现 {count_target} 只高溢价套利标的！"
                        requests.get(f"https://api2.pushdeer.com/message/push?text={push_title}&desp={push_text}&pushkey={PUSHDEER_KEY}")
                    except:
                        pass

                current_rank = 0
                for row, premium, status_desc in valid_rows:
                    current_rank += 1
                    code = str(row['基金代码'])
                    name = row['基金简称']
                    price = float(row['现价'])
                    raw_amount = float(row.get('成交额', 0.0))
                    
                    if code.startswith("50"):
                        amount_wan = raw_amount
                    else:
                        amount_wan = raw_amount / 10000.0
                    
                    st.markdown(f"""
                    <div class="lof-card">
                        <div class="lof-title">{current_rank}. 【{name}】 ({code})</div>
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
                    """, unsafe_allow_html=True)
                    
                    if is_market_open:
                        if amount_wan < 200:
                            st.warning(f"⚠️ 实战提示：该品种当日成交额不足 200 万，流动性偏低，注意防范冲击成本。")
                        else:
                            st.success(f"🔥 实战提示：成交活跃，流动性十分充裕，属于优质套利标的！")
                
                st.info("💡 提示：电脑端可直接拖动鼠标复制卡片文本，手机端长按即可选择复制文字发至微信群。")
        else:
            st.warning("☕ 📢 提示：当前正值周末/节假日交易所系统清算期，官方历史数据源临时闭门维护。")
            st.info("💡 本雷达将于【明天（周一）开盘后】全面恢复全自动实时扫盘，届时请点击上方按钮刷新。")
