import os
import requests

# 🍏 自动读取你在 GitHub 保销箱存的 DING_WEBHOOK
GROUP_WEBHOOK = os.getenv("DING_WEBHOOK")

def run_radar():
    # 模拟一份成功的文案，直接绕过所有行情接口和时间限制
    group_markdown = f"## 🦅 搞钱小本本 · 钉钉机器人联通测试\n"
    group_markdown += f"> 📡 状态：GitHub Actions 云端全自动链路测试\n\n"
    group_markdown += "─" * 20 + "\n\n"
    group_markdown += f"🔥 **1. 【模拟测试标的】(000000)**\n"
    group_markdown += f"> • 盘中实时溢价率：**+8.88%**\n"
    group_markdown += f"> • 物理链路状态：**✅ 恭喜梁总，全线完美打通！**\n\n"
    group_markdown += "─" * 20 + "\n"
    group_markdown += f"💡 明天（周一）下午 14:30，系统将自动恢复真实行情扫盘！"

    # 强行向钉钉发射
    if GROUP_WEBHOOK:
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": "🦅 搞钱小本本关联成功",
                "text": group_markdown
            }
        }
        res = requests.post(GROUP_WEBHOOK, json=payload)
        print(f"钉钉接口返回状态码: {res.status_code}, 返回内容: {res.text}")

if __name__ == "__main__":
    run_radar()
