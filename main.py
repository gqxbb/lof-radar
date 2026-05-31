import streamlit as st
import akshare as ak
import os
import datetime
from PIL import Image, ImageDraw, ImageFont

# 强行忽略代理
os.environ['NO_PROXY'] = 'eastmoney.com,sinajs.cn'

st.set_page_config(page_title="海外LOF套利雷达", layout="centered")

def text_to_image(text):
    """画图并返回图片对象，不保存在本地"""
    bg_color = (18, 24, 38)       
    text_color = (243, 244, 246)  
    accent_color = (239, 68, 68)  
    
    # 云端服务器通常是 Linux 系统，我们使用系统自带或默认字体
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
        if "实时溢价率" in line:
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
    
    with st.spinner("正在疯狂扫描全市场数据并绘制卡片..."):
        try:
            fund_df = ak.fund_lof_spot_em()
            overseas_keywords = ["纳斯", "标普", "原油", "油气", "商品", "互联", "中概", "日经", "德国", "法国", "印度", "越南", "亚洲", "全球", "海外"]
            premium_threshold = 3.0

            report = f"LOF 溢价及流动性雷达\n"
            report += f"数据统计时间: {current_time}\n"
            report += f"--------------------------------------------------\n"
            
            found_any = False
            count = 0

            for index, row in fund_df.iterrows():
                code = row['基金代码']
                name = row['基金简称']
                is_overseas = any(keyword in name for keyword in overseas_keywords) or code.startswith("1611") or code.startswith("1649")
                
                if is_overseas:
                    try:
                        premium = float(row['溢价率'])
                        if premium >= premium_threshold:
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
                            iopv = float(row['盘中估值'])
                            amount_wan = float(row['成交额']) / 10000.0
                            
                            report += f" {count}. 【{name}】({code})\n"
                            report += f"    • 实时溢价率：{premium:.2f}%\n"
                            report += f"    • 场内现价：{price:.3f} 元  /  盘中估值(IOPV)：{iopv:.4f} 元\n"
                            report += f"    • 当日场内成交额：{amount_wan:.2f} 万元\n"
                            report += f"    • 场外申购状态：{status_desc}\n\n"
                    except:
                        continue

            if not found_any:
                report += f" 市场平静。当前暂未发现满足条件的疯狂品种。 ☕"
            else:
                report += f"--------------------------------------------------\n"
                report += f"本次雷达共捕获 {count} 只具备实战价值的高溢价目标。"

            # 生成图片并在网页上直接画出来
            img_result = text_to_image(report)
            st.image(img_result, caption="点击右键可以保存这张复盘图发群", use_column_width=True)

        except Exception as e:
            st.error(f"云端连接交易所超时，请稍后重试。原因: {e}")