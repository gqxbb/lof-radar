import akshare as ak
import os
import datetime
from datetime import timezone, timedelta
import requests

# 强行忽略可能导致连线失败的代理
os.environ['NO_PROXY'] = 'eastmoney.com,sinajs.cn,feishu.cn'

# 从 GitHub 保险箱里读取飞书专属长链接
GROUP_WEBHOOK = os.getenv("FEISHU_WEBHOOK")

def run_radar():
    SHA_TZ = timezone(timedelta(hours=8))
    now = datetime.datetime.now(SHA_TZ)
    current_time = now.strftime("%Y-%m-%d %H:%M")

    try:
        # 实时抓取全市场LOF行情
        fund_df = ak.fund_lof_spot_em()
    except Exception as e:
        print(f"东方财富数据源获取失败: {e}")
        return

    if fund_df is not None and not fund_df.empty:
        # 核心跨境/油气品种过滤网
        overseas_keywords = ["纳斯", "标普", "原油", "油气", "商品", "互联", "中概", "日经", "德国", "法国", "印度", "越南", "亚洲", "全球", "海外"]
        premium_threshold = 2.0  # 商业实战门槛：盘中溢价率大于等于 2.0% 视为有肉吃
        
        count_target = 0
        
        # 👑 飞书顶级彭博卡片排版协议（大标题开头死死咬住“测试”暗号）
        card_content = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "测试：搞钱小本本 · LOF溢价内参"},
                "template": "orange"  # 亮橙色警报包边，极其高档
            },
            "elements": [
                {"tag": "markdown", "text": f"📡 **云端全网扫盘时间**：{current_time}\n⚡ **战术提醒**：当前进入14:30盲区决战期，请密切留意实时价差！"}
            ]
        }
        
        for index, row in fund_df.iterrows():
            code = str(row['基金代码'])
            name = row['基金简称']
            is_overseas = any(keyword in name for keyword in overseas_keywords) or code.startswith("1611") or code.startswith("1649") or code.startswith("501")
            
            if is_overseas:
                try:
                    premium = float(row['溢价率'])
                    if premium >= premium_threshold:
                        try:
                            # 穿透巨潮资讯，核验场外申购状态，排除暂停申购的假肉票
                            limit_info = ak.fund_open_format_xw()
                            matched_fund = limit_info[limit_info['基金代码'] == code]
                            status_desc = matched_fund.iloc[0]['申购状态'] if not matched_fund.empty else "开放申购"
                        except:
                            status_desc = "开放申购"

                        # 严格过滤暂停申购的废标
                        if "暂停申购" in status_desc or "停申" in status_desc or status_desc == "暂停":
                            continue
                            
                        count_target += 1
                        price = float(row['现价'])
                        raw_amount = float(row.get('成交额', 0.0))
                        amount_wan = raw_amount if code.startswith("50") else raw_amount / 10000.0
                        
                        # 优雅的分栏卡片插入
                        card_content["elements"].append({"tag": "hr"})
                        card_content["elements"].append({
                            "tag": "markdown",
                            "text": f"🔥 **{count_target}. 【{name}】({code})**\n• 盘中实时溢价率：**{premium:.2f}%**\n• 场内现价：{price:.3f} 元 | 成交额：{amount_wan:.2f} 万元\n• 场外状态：🟢 **{status_desc}**"
                        })
                except:
                    continue

        if count_target == 0:
            card_content["elements"].append({"tag": "hr"})
            card_content["elements"].append({"tag": "markdown", "text": "📊 **盘中扫描完成**：当前全市场套利品种情绪平稳，暂未出现符合门槛的疯狂品种，建议按兵不动。"})
        else:
            card_content["elements"].append({"tag": "hr"})
            card_content["elements"].append({"tag": "markdown", "text": "💡 **套利纪律**：请在 15:00 前完成场外一票制下单。注意防范小成交额品种的冲击成本！"})

        # 发射！
        if GROUP_WEBHOOK:
            payload = {
                "msg_type": "interactive",
                "card": card_content
            }
            res = requests.post(GROUP_WEBHOOK, json=payload)
            print(f"飞书云端网关实时返回: {res.text}")

if __name__ == "__main__":
    run_radar()
