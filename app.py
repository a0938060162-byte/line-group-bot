from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, MemberJoinedEvent
import re
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# =========================
# LINE 設定
# =========================
CHANNEL_ACCESS_TOKEN = "oFUPzoB75X9XQD5Ac1onzxxg9Anv3IsmKY67YWGhPIlwONFDHCisv8Puh2Lop2EsnU0Ygvc7OJYniPgnChVUKXe0bW8nJ5ETIoKcgx2Fe5ILVGRlNcj4LujcNwjzfVGfc5M6vyYyWMG780xnicpMuQdB04t89/1O/w1cDnyilFU="
CHANNEL_SECRET = "18658576141b5169e2ea8ab7c840ddea"

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# =========================
# 🛍️ 統計設定
# =========================
ALLOWED_ITEMS = ["草莓果醬", "甜燒餅", "年節禮盒", "鳳梨酥", "餐盒"]
order_records = {}

# 網址偵測用的正規表達式
url_pattern = r'(https?://[^\s]+|www\.[^\s]+)'

@app.route("/callback", methods=['POST'])
def callback():
    body = request.get_data(as_text=True)
    signature = request.headers.get('X-Line-Signature', '')
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    except Exception as e:
        logging.error(f"Error: {e}")
        abort(500)
    return 'OK'

# 1. 新成員加入：歡迎詞
@handler.add(MemberJoinedEvent)
def handle_member_join(event):
    try:
        welcome_msg = (
            "歡迎歡迎🫶🏻\n\n"
            "果醬只做當季水果\n"
            "禮盒目前只做中秋節&過年\n\n"
            "很常老闆娘還沒收錢，你就會收到貨\n"
            "這時候記得來找闆娘\n"
            "大家是老客戶～都有默契！！\n\n"
            "從熬煮、製作到包裝都是一人作業\n"
            "所以要等等闆娘喔😍\n\n"
            "至於外燴、餐盒、需要幫忙客製化的禮盒。都可以直接私訊闆娘處理🫶🏻"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=welcome_msg))
    except Exception as e:
        logging.error(f"Join Error: {e}")

# 2. 訊息處理：網址偵測 + 明細統計
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global order_records
    try:
        text = event.message.text.strip()
        group_id = event.source.group_id
        user_id = event.source.user_id

        # --- A. 網址偵測與警告 ---
        if re.search(url_pattern, text):
            warning_msg = "⚠️ 溫馨提示：群組內請不要上傳布相關資訊及亂貼連結！謝謝"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=warning_msg))
            return  # 偵測到網址後直接中斷，不執行下面的統計

        # --- B. 管理員功能：清空統計 ---
        if text == "清空統計":
            order_records = {}
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 訂單明細已清空"))
            return

        # --- C. 訂單統計邏輯 ---
        match = re.findall(r'([^\s\+\-]+?)\s*([+\-])\s*(\d+)', text)
        if match:
            try:
                profile = line_bot_api.get_group_member_profile(group_id, user_id)
                user_name = profile.display_name
            except:
                user_name = "朋友"

            updated = False
            for item_name, op, num_str in match:
                item = item_name.strip()
                if item in ALLOWED_ITEMS:
                    num = int(num_str)
                    if user_name not in order_records:
                        order_records[user_name] = {}
                    if item not in order_records[user_name]:
                        order_records[user_name][item] = 0
                    
                    if op == '+':
                        order_records[user_name][item] += num
                    else:
                        order_records[user_name][item] = max(0, order_records[user_name][item] - num)
                    updated = True
            
            if updated:
                report = "📋 【最新訂單明細】\n"
                all_totals = {}
                
                for name, items in order_records.items():
                    person_list = [f"{k}x{v}" for k, v in items.items() if v > 0]
                    if person_list:
                        report += f"\n👤 {name}: {', '.join(person_list)}"
                        for k, v in items.items():
                            all_totals[k] = all_totals.get(k, 0) + v
                
                report += "\n\n📦 目前總計：\n"
                has_data = False
                for k, v in all_totals.items():
                    if v > 0:
                        report += f"▫️ {k}: {v}\n"
                        has_data = True
                
                if not has_data:
                    report = "🎀 目前暫無訂單。"

                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=report))

    except Exception as e:
        logging.error(f"Message Error: {e}")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)