import streamlit as st
import akshare as ak
import os
import datetime
import pandas as pd

# 强行忽略代理
os.environ['NO_PROXY'] = 'eastmoney.com,sinajs.cn'

st.set_page_config(page_title="海外LOF套利雷达", layout="wide")

# 注入高档深色系 CSS
st.markdown("""
    <style>
    .stApp { background-color: #121826; color: #F3F4F6; }
    .lof-card { background-color: #1F2937; padding: 20px; border-radius: 10px; margin-bottom: 15px; border-left: 5px solid #EF4444; }
    .lof-title { color: #F3F4F6; font-size: 18px; font-weight: bold; }
    .premium-text { color: #EF4444; font-size: 20px; font-weight: bold; }
    </style>
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

        # 1. 【核心逻辑】首先尝试抓取盘中实时数据
        try:
            fund_df = ak.fund_lof_spot_em()
            # 实时接口里必须包含“盘中估值”和“溢价率”字段，否则说明接口虽然吐了数据，但属于无效闭市数据
            if '盘中估值' not in fund_df.columns or fund_df['溢价率'].isnull().all():
                raise ValueError("当前非实时交易时间")
        except Exception as e:
            # 2. 🔴 【进入盘后/周末备用方案】
            is_market_open = False
            try:
                # 抓取全市场 LOF 基金历史收盘基础行情（东财静态接口）
                raw_df = ak.fund_lof_spot_em()
                # 抓取全市场 QDII/开放式基金的最新官方净值
                em_nav_df = ak.fund_open_fund_daily_em()
                
                # 盘后核心算法：将行情（包含场内收盘价）与官方净值进行多键联合匹配，精准算出盘后收盘溢价
                if not raw_df.empty and not em_nav_df.empty:
                    # 重命名净值表的列以便合并
                    em_nav_df.rename(columns={'基金代码': '基金代码', '单位净值': '最新净值', '累计净值': '最新累计净值'}, inplace=True)
                    # 融合两张表
                    merged_df = pd.merge(raw_df, em_nav_df[['基金代码', '最新净值', '最新累计净值']], on='基金代码', how='inner')
                    
                    # 盘后重新计算溢价率: (场内现价 - 场外最新净值) / 场外最新净值 * 100
                    merged_df['现价'] = pd.to_numeric(merged_df['现价'], errors='coerce')
                    merged_df['最新净值'] = pd.to_numeric(merged_df['最新净值'], errors='coerce')
                    merged_df['真实收盘溢价率'] = (merged_df['现价'] - merged_df['最新净值']) / merged_df['最新净值'] * 100
                    
                    fund_df = merged_df
            except Exception as e_inner:
                st.error(f"云端服务器网络繁忙，请稍后再试: {e_inner}")

        if fund_df is not None and not fund_df.empty:
            # 顶部状态面板
            if is_market_open:
                st.success(f"📊 LOF 溢价及流动性雷达（盘中实时版） | 统计时间: {current_time}")
            else:
                st.info(f"📢 当前非交易时间，已自动激活【盘后精确复盘算法】（基于最近交易日场内收盘价与场外最新净值计算）")
            
            st.write(f"**当前过滤规则**：溢价率 $\\ge$ {premium_threshold}%，且【开放场外申购】。已自动拦截暂停申购品种。")
            st.markdown("---")
            
            found_any = False
            count = 0

            # 3. 循环大浪淘沙
            for index, row in fund_df.iterrows():
                code = row['基金代码']
                name = row['基金简称']
                
                # 关键词匹配筛选海外 QDII
                is_overseas = any(keyword in name for keyword in overseas_keywords) or code.startswith("1611") or code.startswith("1649")
                
                if is_overseas:
                    try:
                        # 根据开闭市状态，动态提取计算好的溢价率
                        if is_market_open:
                            premium = float(row['溢价率'])
                        else:
                            premium = float(row['真实收盘溢价率'])
                        
                        # 严格卡死大于等于 3% 门槛
                        if premium >= premium_threshold:
                            # 4. 实时动态过滤场外暂停申购品种
                            try:
                                limit_info = ak.fund_open_format_xw()
                                matched_fund = limit_info[limit_info['基金代码'] == code]
                                status_desc = matched_fund.iloc[0]['申购状态'] if not matched_fund.empty else "开放申购"
                            except:
                                status_desc = "开放申购"

                            if "暂停申购" in status_desc or "停申" in status_desc or status_desc == "暂停":
                                continue
                            
                            found_any = True
                            count += 1
                            
                            price = float(row['现价'])
                            
                            # 渲染高级原生 HTML 卡片
                            with st.container():
                                st.markdown(f"""
                                <div class="lof-card">
                                    <div class="lof-title">{count}. 【{name}】 ({code})</div>
                                    <div style="margin-top: 8px;">
                                        <span class="premium-text">{'盘中实时' if is_market_open else '静态收盘'}溢价率：{premium:.2f}%</span>
                                    </div>
                                    <div style="margin-top: 8px; color: #9CA3AF; font-size: 14px;">
                                        • 场内收盘价：<b style="color: #F3F4F6;">{price:.3f} 元</b> &nbsp;&nbsp;|&nbsp;&nbsp; 
                                        {'场外盘中估值' if is_market_open else '场外最新官方净值'}：<b style="color: #F3F4F6;">{row.get('盘中估值', row.get('最新净值', 0.0)):.4f} 元</b>
                                    </div>
                                    <div style="margin-top: 4px; color: #9CA3AF; font-size: 14px;">
                                        • 场外申购限制：<b style="color: #10B981;">✅ {status_desc}</b>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                    except:
                        continue

            st.markdown("---")
            if not found_any:
                st.subheader("⚖️ 市场平静。当前全市场暂未发现符合条件的疯狂品种。☕")
            else:
                st.metric(label="雷达捕获目标总数", value=f"{count} 只")
                st.info("💡 💡 提示：电脑端可直接拖动鼠标复制卡片文本，手机端长按即可选择复制文字发至微信群。")
