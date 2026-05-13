from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    MemberJoinedEvent, Mention, Mentionee
)

import re
import logging
from collections import defaultdict

app = Flask(__name__)

# =========================
# LOG 設定
# =========================
logging.basicConfig(level=logging.INFO)

# =========================
# LINE 設定 (請務必確認您的 Token 與 Secret 正確)
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
# 資料儲存：{ 使用者名稱: { 品項: 數量 } }
# =========================
order_records = defaultdict(lambda: defaultdict(int))

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
# 1. 新成員加入：穩定標註版歡迎詞
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

            welcome_text = (
                f"@{display_name} 歡迎歡迎(你好)🫶🏻\n\n"
                "果醬只做當季水果\n"
                "年節禮盒\n\n"
                "很常老闆娘還沒收錢，你就會收到貨\n"
                "這時候記得來找闆娘\n"
                "大家是老客戶～都有默契！！\n\n"
                "從熬煮、製作到包裝都是一人作業\n"
                "所以要等等闆娘喔😍\n\n"
                "至於外燴、餐盒、需要幫忙客製化的禮盒。都可以直接私訊闆娘處理🫶🏻"
            )
            
            mention_len = len(display_name) + 1
            try:
                mention_obj = Mention(mentionees=[Mentionee(index=0, length=mention_len, user_id=user_id)])
                msg = TextSendMessage(text=welcome_text, mention=mention_obj)
            except:
                msg = TextSendMessage(text=welcome_text)

            line_bot_api.push_message(group_id, msg)
            
    except Exception as e:
        logging.error(f"❌ Join Event Error: {e}")

# =========================
# 2. 訊息處理 (明細彙整統計版)
# =========================
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        text = event.message.text.strip()
        group_id = event.source.group_id
        user_id = event.source.user_id

        # A. 網址偵測
        if re.search(url_pattern, text):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 溫馨提示：群組內請避免亂貼連結，請遵守群規喔！"))
            return

        # B. 管理員指令：清空統計
        if text == "清空統計":
            order_records.clear()
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 訂單明細已全數清空！"))
            return

        # C. 獲取發訊者名字與訂單邏輯
        items_found = re.findall(multi_count_pattern, text)
        updated = False
        
        if items_found:
            # 只有當偵測到目標品項時才去抓名字，節省流量
            try:
                profile = line_bot_api.get_group_member_profile(group_id, user_id)
                user_name = profile.display_name
            except:
                user_name = "神秘客"

            for item_name, operator, num_str in items_found:
                item = item_name.strip()
                if item in ALLOWED_ITEMS:
                    number = int(num_str)
                    if operator == '+':
                        order_records[user_name][item] += number
                    elif operator == '-':
                        order_records[user_name][item] = max(0, order_records[user_name][item] - number)
                    updated = True
            
            if updated:
                # 建立詳細清單文案
                summary = "📋 【訂單明細彙整】\n\n"
                total_all = defaultdict(int)

                # 遍歷每位客人的訂單
                for name, items in order_records.items():
                    person_items = [f"{k}x{v}" for k, v in items.items() if v > 0]
                    if person_items:
                        summary += f"👤 {name}：{', '.join(person_items)}\n"
                        for k, v in items.items():
                            total_all[k] += v

                summary += "\n------------------\n📦 目前品項總計：\n"
                
                # 計算總數
                has_total = False
                for k, v in total_all.items():
                    if v > 0:
                        summary += f"▫️ {k}：共 {v} 份\n"
                        has_total = True
                
                if not has_total:
                    summary = "🎀 目前暫無訂單（統計已歸零）。"
                else:
                    summary += "\n感謝大家的支持！🫶🏻"

                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=summary))

    except Exception as e:
        logging.error(f"❌ Message Error: {e}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)