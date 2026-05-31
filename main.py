import streamlit as st
import akshare as ak
import os
import datetime

# 强行忽略代理
os.environ['NO_PROXY'] = 'eastmoney.com,sinajs.cn'

# 网页基本配置：设置为宽屏模式，方便团队看盘
st.set_page_config(page_title="海外LOF套利雷达", layout="wide")

# 利用 CSS 样式表将网页背景硬编码为高档的深色系（暗夜蓝），保持原本的极客风审美
st.markdown("""
    <style>
    .stApp {
        background-color: #121826;
        color: #F3F4F6;
    }
    .lof-card {
        background-color: #1F2937;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 15px;
        border-left: 5px solid #EF4444;
    }
    .lof-title {
        color: #F3F4F6;
        font-size: 18px;
        font-weight: bold;
    }
    .premium-text {
        color: #EF4444;
        font-size: 20px;
        font-weight: bold;
    }
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

        # --- 核心逻辑：尝试抓取盘中实时数据 ---
        try:
            fund_df = ak.fund_lof_spot_em()
        except Exception as e:
            is_market_open = False
            try:
                # 闭市备用方案：抓取最近一个交易日的收盘快照
                fund_df = ak.fund_open_fund_daily_em()
            except Exception as e_inner:
                st.error(f"云端服务器网络繁忙，请稍后再试: {e_inner}")

        if fund_df is not None:
            # 顶部状态面板展示
            if is_market_open:
                st.success(f"📊 📊 LOF 溢价及流动性雷达（盘中实时版） | 统计时间: {current_time}")
            else:
                st.info(f"📢 当前非交易时间，已自动切换为最近交易日收盘复盘数据")
            
            st.write(f"**过滤规则**：溢价率 $\\ge$ {premium_threshold}%，且【开放场外申购】的有效套利品种。已自动隐藏暂停申购品种。")
            st.markdown("---")
            
            found_any = False
            count = 0

            for index, row in fund_df.iterrows():
                code = row.get('基金代码', row.get('代码', ''))
                name = row.get('基金简称', row.get('名称', ''))
                
                is_overseas = any(keyword in name for keyword in overseas_keywords) or code.startswith("1611") or code.startswith("1649")
                
                if is_overseas:
                    try:
                        premium_val = row.get('溢价率', row.get('日增长率', 0.0))
                        try:
                            premium = float(premium_val)
                        except:
                            continue
                            
                        if premium >= premium_threshold:
                            # 实时动态过滤暂停申购
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
                            
                            price = float(row.get('现价', row.get('单位净值', 0.0)))
                            iopv = float(row.get('盘中估值', row.get('累计净值', 0.0)))
                            amount_raw = float(row.get('成交额', 0.0))
                            amount_wan = amount_raw / 10000.0
                            
                            # 使用原生 HTML/Markdown 组件渲染极其精美的深色卡片，中文绝不乱码
                            with st.container():
                                st.markdown(f"""
                                <div class="lof-card">
                                    <div class="lof-title">{count}. 【{name}】 ({code})</div>
                                    <div style="margin-top: 8px;">
                                        <span class="premium-text">{'实时' if is_market_open else '昨日收盘'}溢价率：{premium:.2f}%</span>
                                    </div>
                                    <div style="margin-top: 8px; color: #9CA3AF; font-size: 14px;">
                                        • 场内现价/单位净值：<b style="color: #F3F4F6;">{price:.4f} 元</b> &nbsp;&nbsp;|&nbsp;&nbsp; 
                                        盘中估值/累计净值：<b style="color: #F3F4F6;">{iopv:.4f} 元</b>
                                    </div>
                                    <div style="margin-top: 4px; color: #9CA3AF; font-size: 14px;">
                                        • 当日场内成交额：<b style="color: #F3F4F6;">{amount_wan:.2f} 万元</b> &nbsp;&nbsp;|&nbsp;&nbsp; 
                                        场外申购状态：<b style="color: #10B981;">✅ {status_desc}</b>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # 流动性实战提示
                                if is_market_open:
                                    if amount_wan < 200:
                                        st.warning(f"⚠️ 实战提示：该品种当日场内成交额不足 200 万，流动性偏低，注意控制仓位和出货风险。")
                                    else:
                                        st.success(f"🔥 实战提示：流动性十分充裕，属于高价值主力套利目标！")
                    except:
                        continue

            st.markdown("---")
            if not found_any:
                st.subheader("⚖️ 市场平静。当前全市场暂未发现符合条件的疯狂品种。☕")
            else:
                st.metric(label="雷达捕获目标总数", value=f"{count} 只")
                st.info("💡 提示：电脑端可直接拖动鼠标复制卡片文本，手机端长按即可选择复制文字发至微信群。")
