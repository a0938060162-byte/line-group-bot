from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
# 修正匯入方式，使用最基礎的 models 確保相容性
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
# LINE 設定
# =========================
CHANNEL_ACCESS_TOKEN = "oFUPzoB75X9XQD5Ac1onzxxg9Anv3IsmKY67YWGhPIlwONFDHCisv8Puh2Lop2EsnU0Ygvc7OJYniPgnChVUKXe0bW8nJ5ETIoKcgx2Fe5ILVGRlNcj4LujcNwjzfVGfc5M6vyYyWMG780xnicpMuQdB04t89/1O/w1cDnyilFU="
CHANNEL_SECRET = "18658576141b5169e2ea8ab7c840ddea"

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# =========================
# 🛍️ 特定品項設定
# =========================
ALLOWED_ITEMS = ["草莓果醬", "甜燒餅", "年節禮盒", "鳳梨酥", "餐盒"]

# =========================
# 資料儲存
# =========================
counter_data = defaultdict(int)

# =========================
# 正則表達式設定
# =========================
url_pattern = r'(https?://[^\s]+|www\.[^\s]+)'
multi_count_pattern = r'([^\s\+\-]+?)\s*([+\-])\s*(\d+)'

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
# 1. 新成員加入：穩定標註版
# =========================
@handler.add(MemberJoinedEvent)
def handle_member_join(event):
    try:
        group_id = event.source.group_id
        new_members = event.joined.members
        
        for member in new_members:
            user_id = member.user_id
            
            try:
                profile = line_bot_api.get_group_member_profile(group_id, user_id)
                display_name = profile.display_name
            except:
                display_name = "新朋友"

            # 歡迎詞內容
            welcome_text = (
                f"@{display_name} 歡迎歡迎(你好)🫶🏻\n\n"
                "果醬只做當季水果\n"
                "禮盒目前做中秋節&過年\n\n"
                "很常老闆娘還沒收錢，你就會收到貨\n"
                "這時候記得來找闆娘\n"
                "大家是老客戶～都有默契！！\n\n"
                "從熬煮、製作到包裝都是一人作業\n"
                "所以要等等闆娘喔😍\n\n"
                "至於外燴、餐盒、需要幫忙客製化的禮盒。都可以直接私訊闆娘處理🫶🏻"
            )
            
            # 使用最通用的 Mentionee 寫法
            # 如果這行報錯，代表 SDK 真的無法載入 Mention 類別
            try:
                from linebot.models import Mention, Mentionee
                mention_obj = Mention(mentionees=[Mentionee(index=0, length=len(display_name)+1, user_id=user_id)])
                msg = TextSendMessage(text=welcome_text, mention=mention_obj)
            except:
                # 備援方案：如果標註功能在伺服器上還是壞的，發送純文字歡迎詞
                msg = TextSendMessage(text=welcome_text)

            line_bot_api.push_message(group_id, msg)
            
    except Exception as e:
        logging.error(f"❌ Join Event Error: {e}")

# =========================
# 2. 訊息處理 (統計與連結偵測)
# =========================
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        text = event.message.text.strip()

        if re.search(url_pattern, text):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 溫馨提示：群組內請避免亂貼連結，請遵守群規喔！"))
            return

        if text == "清空統計":
            counter_data.clear()
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 已清空所有統計資料！"))
            return

        items_found = re.findall(multi_count_pattern, text)
        updated = False
        if items_found:
            for item_name, operator, num_str in items_found:
                item = item_name.strip()
                if item in ALLOWED_ITEMS:
                    number = int(num_str)
                    if operator == '+': counter_data[item] += number
                    elif operator == '-': counter_data[item] = max(0, counter_data[item] - number)
                    updated = True
            
            if updated:
                active_items = {k: v for k, v in counter_data.items() if v > 0}
                summary = "🎀目前暫無訂單🎀" if not active_items else "目前最新訂購彙整：\n\n" + "\n".join([f"▫️ {k}：{v}" for k, v in active_items.items()]) + "\n\n感謝支持！"
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=summary))

    except Exception as e:
        logging.error(f"❌ Message Error: {e}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)