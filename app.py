from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

import re
import logging
from collections import defaultdict

app = Flask(__name__)

# =========================
# LOG 設定
# =========================
logging.basicConfig(level=logging.INFO)

# =========================
# LINE 設定 (請填入你的設定)
# =========================
CHANNEL_ACCESS_TOKEN = "你的TOKEN"
CHANNEL_SECRET = "你的SECRET"

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# =========================
# 🛍️ 特定品項設定 (只有這些字會被統計)
# =========================
# 在這裡填入你想統計的關鍵字，例如：["果醬", "禮盒", "餐盒"]
# 如果要新增品項，直接在括號內加引號跟逗號即可
ALLOWED_ITEMS = ["果醬", "年節禮盒", "外燴", "餐盒"]

# =========================
# 資料儲存
# =========================
counter_data = defaultdict(int)

# =========================
# 正則表達式設定
# =========================
url_pattern = r'(https?://[^\s]+|www\.[^\s]+)'
multi_count_pattern = r'([^\s\+\-]+?)\s*([+\-])\s*(\d+)'

# =========================
# Webhook 主入口
# =========================
@app.route("/callback", methods=['POST'])
def callback():
    body = request.get_data(as_text=True)
    signature = request.headers.get('X-Line-Signature', '')
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    except Exception as e:
        logging.error(f"Webhook Error: {e}")
        abort(500)
    return 'OK'

# =========================
# 1. 新成員加入：客製化歡迎詞
# =========================
@handler.add(MemberJoinedEvent)
def handle_member_join(event):
    try:
        group_id = event.source.group_id
        welcome_text = (
            "歡迎歡迎(你好)\n\n"
            "果醬只做當季水果\n"
            "年節禮盒\n\n"
            "很常老闆娘還沒收錢，你就會收到貨\n"
            "這時候記得來找闆娘\n"
            "大家是老客戶～都有默契！！\n\n"
            "從熬煮、製作到包裝都是一人作業\n"
            "所以要等等闆娘喔😍\n\n"
            "至於外燴、餐盒、需要幫忙客製化的禮盒。都可以直接私訊闆娘處理🫶🏻"
        )
        line_bot_api.push_message(group_id, TextSendMessage(text=welcome_text))
    except Exception as e:
        logging.error(f"❌ Join Error: {e}")

# =========================
# 2. 訊息處理 (含特定字偵測)
# =========================
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        text = event.message.text.strip()

        # --- A. 網址偵測 (僅提醒) ---
        if re.search(url_pattern, text):
            reply_msg = "⚠️ 溫馨提示：群組內請避免亂貼連結，請遵守群規喔！"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_msg))
            return

        # --- B. 管理員指令：清空統計 ---
        if text == "闆娘指令清空統計":
            counter_data.clear()
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 已清空所有統計資料！"))
            return

        # --- C. 特定品項統計邏輯 ---
        items_found = re.findall(multi_count_pattern, text)
        
        updated = False
        if items_found:
            for item_name, operator, num_str in items_found:
                item = item_name.strip()
                
                # ⭐ 核心邏輯：檢查品項是否在允許清單內
                if item in ALLOWED_ITEMS:
                    number = int(num_str)
                    if operator == '+':
                        counter_data[item] += number
                    elif operator == '-':
                        counter_data[item] = max(0, counter_data[item] - number)
                    updated = True
            
            # 只有當真的有統計到「清單內品項」時才回覆，避免干擾一般聊天
            if updated:
                active_items = {k: v for k, v in counter_data.items() if v > 0}
                if not active_items:
                    summary = "📊 目前暫無訂單（統計已歸零）。"
                else:
                    summary = "📊 目前最新訂購彙整：\n\n"
                    for k, v in active_items.items():
                        summary += f"▫️ {k}：{v}\n"
                    summary += "\n感謝大家的支持！"

                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=summary))
            return

    except Exception as e:
        logging.error(f"❌ Message Error: {e}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)