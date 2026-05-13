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
# 格式：{ "人名": { "品項": 數量 } }
order_records = {}

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

# 1. 新成員加入 (純文字歡迎，最保險)
@handler.add(MemberJoinedEvent)
def handle_member_join(event):
    try:
        reply_text = "歡迎新朋友加入！🫶🏻\n果醬當季製作、年節禮盒都有喔。\n一人作業請稍等闆娘😍"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
    except Exception as e:
        logging.error(f"Join Error: {e}")

# 2. 訊息處理 (明細統計)
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global order_records
    try:
        text = event.message.text.strip()
        group_id = event.source.group_id
        user_id = event.source.user_id

        if text == "清空統計":
            order_records = {}
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 訂單已清空"))
            return

        # 匹配格式如：草莓果醬+1 或 甜燒餅-2
        match = re.findall(r'([^\s\+\-]+?)\s*([+\-])\s*(\d+)', text)
        if match:
            # 取得發言者名字
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
                
                # 逐人列出
                for name, items in order_records.items():
                    person_list = [f"{k}x{v}" for k, v in items.items() if v > 0]
                    if person_list:
                        report += f"\n👤 {name}: {', '.join(person_list)}"
                        for k, v in items.items():
                            all_totals[k] = all_totals.get(k, 0) + v
                
                # 總量統計
                report += "\n\n📦 總計累積：\n"
                for k, v in all_totals.items():
                    if v > 0:
                        report += f"▫️ {k}: {v}\n"
                
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=report))

    except Exception as e:
        logging.error(f"Message Error: {e}")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)