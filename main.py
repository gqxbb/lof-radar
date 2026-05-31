import streamlit as st
import akshare as ak
import os
import datetime
from PIL import Image, ImageDraw, ImageFont

# 强行忽略代理
os.environ['NO_PROXY'] = 'eastmoney.com,sinajs.cn'

st.set_page_config(page_title="海外LOF套利雷达", layout="centered")

def text_to_image(text):
    """画图并返回图片对象"""
    bg_color = (18, 24, 38)       
    text_color = (243, 244, 246)  
    accent_color = (239, 68, 68)  
    font = ImageFont.load_default()

    lines = text.split("\n")
    line_height = 30
    padding = 40
    img_width = 700
    img_height = (len(lines) * line_height) + (padding * 2)

    image = Image.new("RGB", (img_width, img_height), color=bg_color)
    draw = ImageDraw.Draw(image)

    current_y = padding
    for line in lines:
        if "实时溢价率" in line or "昨日收盘溢价" in line:
            draw.text((padding, current_y), line, font=font, fill=accent_color)
            current_y += line_height
        else:
            draw.text((padding, current_y), line, font=font, fill=text_color)
            current_y += line_height

    return image

# Streamlit 网页前端展示
st.title("🦅 梁总的海外 LOF 溢价雷达")
st.caption("全自动大浪淘沙，实时过滤已暂停申购的品种")

# 放一个手动刷新按钮
if st.button("🔄 立即刷新全市场数据"):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    with st.spinner("正在全力检索全市场数据并绘制卡片..."):
        overseas_keywords = ["纳斯", "标普", "原油", "油气", "商品", "互联", "中概", "日经", "德国", "法国", "印度", "越南", "亚洲", "全球", "海外"]
        premium_threshold = 3.0
        
        report = ""
        is_market_open = True
        fund_df = None

        # --- 核心逻辑：尝试抓取盘中实时数据 ---
        try:
            fund_df = ak.fund_lof_spot_em()
        except Exception as e:
            # 🔴 如果报错（如周末休市），自动启动备用方案，抓取历史收盘数据
            is_market_open = False
            try:
                # 抓取最近一个交易日的全市场基金收盘净值及表现快照
                fund_df = ak.fund_open_fund_daily_em()
            except Exception as e_inner:
                st.error(f"云端服务器网络繁忙，请稍后再试: {e_inner}")

        if fund_df is not None:
            if is_market_open:
                report += f"LOF 溢价及流动性雷达（盘中实时版）\n"
                report += f"数据统计时间: {current_time}\n"
            else:
                report += f"LOF 溢价雷达（📢当前非交易时间，显示最近收盘数据）\n"
                report += f"数据统计时间: 周末/节假日闭市复盘\n"
            
            report += f"--------------------------------------------------\n"
            report += f"提示：以下海外 LOF 溢价已突破 {premium_threshold}%，且开放场外申购！\n\n"
            
            found_any = False
            count = 0

            # 统一提取状态的工具（由于实时接口和收盘接口字段不同，做一下智能兼容）
            for index, row in fund_df.iterrows():
                # 兼容两个接口的代码和名称字段
                code = row.get('基金代码', row.get('代码', ''))
                name = row.get('基金简称', row.get('名称', ''))
                
                is_overseas = any(keyword in name for keyword in overseas_keywords) or code.startswith("1611") or code.startswith("1649")
                
                if is_overseas:
                    try:
                        # 兼容实时溢价率和历史溢价率字段
                        premium_val = row.get('溢价率', row.get('日增长率', 0.0)) # 兜底逻辑
                        try:
                            premium = float(premium_val)
                        except:
                            continue
                            
                        if premium >= premium_threshold:
                            # 过滤暂停申购的品种
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
                            
                            # 获取价格和成交额（盘中和收盘字段兼容）
                            price = float(row.get('现价', row.get('单位净值', 0.0)))
                            iopv = float(row.get('盘中估值', row.get('累计净值', 0.0)))
                            amount_raw = float(row.get('成交额', 0.0))
                            amount_wan = amount_raw / 10000.0
                            
                            report += f" {count}. 【{name}】({code})\n"
                            if is_market_open:
                                report += f"    • 实时溢价率：{premium:.2f}%\n"
                                report += f"    • 实时现价：{price:.3f} 元  /  盘中估值(IOPV)：{iopv:.4f} 元\n"
                                report += f"    • 当日场内成交额：{amount_wan:.2f} 万元\n"
                            else:
                                report += f"    • 最近收盘溢价率：{premium:.2f}%\n"
                                report += f"    • 最新净值：{price:.4f} 元\n"
                                
                            report += f"    • 场外申购状态：{status_desc}\n\n"
                    except:
                        continue

            if not found_any:
                report += f" 市场平静。当前暂未发现满足条件的疯狂品种。 ☕"
            else:
                report += f"--------------------------------------------------\n"
                report += f"本次雷达共捕获 {count} 只具备实战价值的高溢价目标。"

            # 生成图片并在网页上画出来
            img_result = text_to_image(report)
            st.image(img_result, caption="手机端长按图片或电脑端右键即可保存分享", use_column_width=True)
