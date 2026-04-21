import os
import sys
import json
import time
import random
import logging
import requests
from datetime import datetime
from calendar import monthrange
from chinese_calendar import is_workday as cc_is_workday

# 配置日志
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"reminder_{datetime.now().strftime('%Y%m')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Webhook Key 从环境变量读取
WEBHOOK_KEY = os.getenv("QYWX_WEBHOOK_KEY", "")
WEBHOOK_URL = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={WEBHOOK_KEY}"

# 全局状态
_sent_reminders = set()
_current_date = None


def reset_sent_reminders():
    """每天凌晨重置已发送提醒记录"""
    global _sent_reminders, _current_date
    today = datetime.now().date()
    if _current_date != today:
        _sent_reminders.clear()
        _current_date = today
        logger.info("已重置当日提醒记录")


def is_workday():
    """判断是否为工作日（自动处理法定节假日和调休）"""
    return cc_is_workday(datetime.now().date())


def is_last_day_of_month():
    """判断是否为当月最后一天"""
    today = datetime.now()
    return today.day == monthrange(today.year, today.month)[1]


def is_payday():
    """判断是否为每月5号（发薪日）"""
    return datetime.now().day == 5


def is_thursday():
    """判断是否为周四"""
    return datetime.now().weekday() == 3  # 3=周四


def is_friday():
    """判断是否为周五"""
    return datetime.now().weekday() == 4  # 4=周五


def send_message(content, max_retries=3):
    """发送企业微信消息，支持失败重试"""
    if not WEBHOOK_KEY:
        logger.error("未设置 QYWX_WEBHOOK_KEY 环境变量，无法发送消息")
        return False

    data = {
        "msgtype": "text",
        "text": {"content": content}
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                WEBHOOK_URL,
                headers={"Content-Type": "application/json"},
                data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
                timeout=10
            )
            if response.status_code == 200:
                logger.info("消息发送成功")
                return True
            else:
                logger.warning(f"消息发送失败，状态码: {response.status_code}, 响应: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"第 {attempt} 次发送失败: {str(e)}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                logger.error(f"消息发送失败，已重试 {max_retries} 次")
                break
    return False


def _build_lunch_content():
    """构建午饭推荐内容"""
    suggestion = random.choice(["🍗 鸭腿饭", "🥗 自选菜"])
    return f"今天吃什么？\n\n推荐：{suggestion} 🍴\n\n大家有什么好推荐吗？"


def _build_work_report_content():
    """构建报工提醒内容"""
    reminder_type = "月度最后一天" if is_last_day_of_month() else "工作日"
    return f"提醒类型：{reminder_type}\n请大家及时完成报工！📊"


def _build_crazy_thursday_content():
    """构建疯狂星期四文案"""
    options = [
        "今天疯狂星期四，V我50看看实力！🍗",
        "生活不易，猪猪叹气。叹气泄气，还得打气。疯狂星期四，V我50打气！",
        "有没有一种可能，你其实是想请我疯狂星期四的？🍟",
        "科学研究表明：每周四吃肯德基的人，快乐指数提升100%！",
        "世界上有5种K：黑桃K、红桃K、梅花K、方块K，还有疯狂星期四V我50！",
        "你今天是东方树叶，我是肯德基疯狂星期四，我们天生一对！",
    ]
    return random.choice(options)


def _build_friday_celebration_content():
    """构建周五放纵文案"""
    options = [
        "周五了！今天不加班，谁加班谁是🐶",
        "周五一到，快乐冒泡！今晚不醉不归🍻",
        "熬过今天，又是两天自由身！冲！🎉",
        "周五了，老板喊加班请装死，谢谢配合🙏",
        "今天是周五，摸鱼有理，摆烂无罪！",
        "周五下午的工作态度：活着就好，其他的下周一再说。",
    ]
    return random.choice(options)


# 提醒任务配置表
REMINDER_TASKS = [
    {
        "time": "08:40",
        "label": "⏰ 【上班打卡提醒】",
        "content": "早上好！☀️\n请记得上班打卡！✋",
        "condition": is_workday,
    },
    {
        "time": "09:00",
        "label": "😢 【上班了】",
        "content": "怎么又要上班了😭😭😭",
        "condition": is_workday,
    },
    {
        "time": "11:45",
        "label": "🍽️ 【午饭时间】",
        "content": _build_lunch_content,
        "condition": is_workday,
    },
    {
        "time": "11:50",
        "label": "🎉 【下班了】",
        "content": "别tm干了！🏃‍♂️💨",
        "condition": is_workday,
    },
    {
        "time": "13:30",
        "label": "😢 【上班了】",
        "content": "怎么又要上班了😭😭😭",
        "condition": is_workday,
    },
    {
        "time": "17:30",
        "label": "⏰ 【日报提醒】",
        "content": "请大家及时完成今日日报！📝",
        "condition": is_workday,
    },
    {
        "time": "17:45",
        "label": "⏰ 【报工提醒】",
        "content": _build_work_report_content,
        "condition": lambda: is_workday() or is_last_day_of_month(),
    },
    {
        "time": "18:00",
        "label": "🎉 【下班了】",
        "content": "别tm干了！🏃‍♂️💨",
        "condition": is_workday,
    },
    {
        "time": "18:05",
        "label": "⏰ 【下班打卡提醒】",
        "content": "下班时间到！🌙\n请记得下班打卡！✋",
        "condition": is_workday,
    },
    {
        "time": "09:30",
        "label": "💰 【发薪日】",
        "content": "工资到账！今晚加餐，奶茶自由！🧋🍗",
        "condition": is_payday,
    },
    {
        "time": "11:30",
        "label": "🍗 【疯狂星期四】",
        "content": _build_crazy_thursday_content,
        "condition": is_thursday,
    },
    {
        "time": "17:00",
        "label": "🍻 【周五放纵时刻】",
        "content": _build_friday_celebration_content,
        "condition": is_friday,
    },
]


def check_and_send_reminders():
    """检查时间并发送相应提醒"""
    now = datetime.now()
    reset_sent_reminders()

    time_key = f"{now.hour:02d}:{now.minute:02d}"
    if time_key in _sent_reminders:
        return

    for task in REMINDER_TASKS:
        if task["time"] != time_key:
            continue

        # 检查触发条件
        condition_func = task.get("condition")
        if condition_func and not condition_func():
            label = task["label"].replace("\n", "").strip()
            logger.info(f"[{label}] 不满足触发条件，跳过提醒")
            continue

        # 构建消息内容
        content_raw = task["content"]
        if callable(content_raw):
            content_body = content_raw()
        else:
            content_body = content_raw

        full_content = (
            f"{task['label']}\n\n"
            f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"{content_body}"
        )

        send_message(full_content)
        _sent_reminders.add(time_key)
        break  # 同一时间点只执行一个任务


def main():
    logger.info("=" * 40)
    logger.info("企业微信提醒服务已启动")
    logger.info("=" * 40)
    for task in REMINDER_TASKS:
        logger.info(f"  • {task['time']} - {task['label']}")
    logger.info("按 Ctrl+C 停止服务\n")

    # 发送启动测试消息
    test_msg = (
        "🤖 提醒服务已启动！\n\n"
        f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"今日是：{'工作日' if is_workday() else '非工作日'}"
        f"{'，且是本月最后一天' if is_last_day_of_month() else ''}"
    )
    send_message(test_msg)

    try:
        while True:
            check_and_send_reminders()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("=" * 40)
        logger.info("提醒服务已停止")
        logger.info("=" * 40)


if __name__ == "__main__":
    main()
