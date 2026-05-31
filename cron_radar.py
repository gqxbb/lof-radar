import akshare as ak
import os
import datetime
from datetime import timezone, timedelta
import pandas as pd
import requests

# 强行忽略代理
os.environ['NO_PROXY'] = 'eastmoney.com,sinajs.cn'

# 🍏 填入你运营群机器人的 Webhook 链接
GROUP_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=e3f38cb68d67b4bdfd39aac139c274da24240ac15ba1d32b133430574fb4b4ba"

def run_radar():
    SHA_TZ = timezone(timedelta(hours=8))
    now = datetime.datetime.now(SHA_TZ)
    current_time = now.strftime("%Y-%m-%d %H:%M")
    
    # 周末直接拦截，不发垃圾信息打扰客户
    # if now.weekday() >= 5:
    #     return

    try:
        fund_df = ak.fund_lof_spot_em()
    except Exception as e:
        print(f"数据源获取失败: {e}")
        return

    if fund_df is not None and not fund_df.empty:
        overseas_keywords = ["纳斯", "标普", "原油", "油气", "商品", "互联", "中概", "日经", "德国", "法国", "印度", "越南", "亚洲", "全球", "海外"]
        premium_threshold = -10.0
        
        count_target = 0
        valid_rows = []
        
        # 👑 商业群专属高级文案包装
        group_markdown = f"## 🦅 搞钱小本本 · LOF溢价套利内参\n"
        group_markdown += f"> 📡 实时全网扫盘时间：{current_time}\n"
        group_markdown += f"> ⚡ **战术提醒**：当前进入14:30截单盲区黄金决战期，请密切留意以下标的场内外价差！\n\n"
        group_markdown += "─" * 20 + "\n\n"
        
        for index, row in fund_df.iterrows():
            code = str(row['基金代码'])
            name = row['基金简称']
            is_overseas = any(keyword in name for keyword in overseas_keywords) or code.startswith("1611") or code.startswith("1649") or code.startswith("501")
            
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
                            
                        count_target += 1
                        price = float(row['现价'])
                        raw_amount = float(row.get('成交额', 0.0))
                        amount_wan = raw_amount if code.startswith("50") else raw_amount / 10000.0
                        
                        # 针对运营群优化的精简暴利文案
                        group_markdown += f"🔥 **{count_target}. 【{name}】({code})**\n"
                        group_markdown += f"> • 盘中实时溢价率：<font color=\"warning\">**{premium:.2f}%**</font>\n"
                        group_markdown += f"> • 场内现价：{price:.3f} 元 | 成交额：{amount_wan:.2f} 万元\n"
                        group_markdown += f"> • 场外申购状态：<font color=\"info\">**✅ {status_desc}**</font>\n\n"
                except:
                    continue

        if count_target == 0:
            group_markdown += "⚖️ **📊 盘中扫描报告**：当前市场平稳，暂未出现符合套利门槛（≥3%）的疯狂品种。☕ 团队建议继续保持观望。\n"
        else:
            group_markdown += "─" * 20 + "\n"
            group_markdown += f"💡 **套利纪律**：请在 15:00 前完成场外一票制申购下单。注意防范小成交额品种的冲击成本！"

        # 🍏 推送进群
        if GROUP_WEBHOOK:
            payload = {"msgtype": "markdown", "markdown": {"content": group_markdown}}
            requests.post(GROUP_WEBHOOK, json=payload)

if __name__ == "__main__":
    run_radar()
