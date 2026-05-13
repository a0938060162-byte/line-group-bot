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
CHANNEL_ACCESS_TOKEN = "oFUPzoB75X9XQD5Ac1onzxxg9Anv3IsmKY67YWGhPIlwONFDHCisv8Puh2Lop2EsnU0Ygvc7OJYniPgnChVUKXe0bW8nJ5ETIoKcgx2Fe5ILVGRlNcj4LujcNwjzfVGfc5M6vyYyWMG780xnicpMuQdB04t89/1O/w1cDnyilFU="
CHANNEL_SECRET = "18658576141b5169e2ea8ab7c840ddea"

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# =========================
# 資料儲存（統計用）
# =========================
counter_data = defaultdict(int)

# =========================
# 正則表達式設定
# =========================
url_pattern = r'(https?://[^\s]+|www\.[^\s]+)'
count_pattern = r'(.+?)\s*\+\s*(\d+)'

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

        line_bot_api.push_message(
            group_id,
            TextSendMessage(text=welcome_text)
        )
    except Exception as e:
        logging.error(f"❌ Join Event Error: {e}")

# =========================
# 2. 訊息處理 (網址偵測 & 統計)
# =========================
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        text = event.message.text.strip()

        # --- A. 網址偵測 (僅提醒，不計次) ---
        if re.search(url_pattern, text):
            reply_msg = "⚠️ 溫馨提示：群組內請避免亂貼連結，請遵守群規喔！"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_msg)
            )
            return

        # --- B. 訂單統計功能 (例如：果醬+2) ---
        match = re.match(count_pattern, text)
        if match:
            item = match.group(1).strip()
            number = int(match.group(2))

            # 累加數量
            counter_data[item] += number

            # 彙整目前所有統計結果
            summary = "📊 目前訂購清單：\n"
            for k, v in counter_data.items():
                summary += f"▫️ {k}：{v}\n"
            summary += "\n感謝大家的支持！"

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=summary)
            )
            return

        # 其他訊息保持沉默
        pass

    except Exception as e:
        logging.error(f"❌ Message Error: {e}")

# =========================
# 啟動伺服器
# =========================
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)