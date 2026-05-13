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
logging.basicConfig(level=logging.INFO)

# =========================
# LINE 設定
# =========================
CHANNEL_ACCESS_TOKEN = "oFUPzoB75X9XQD5Ac1onzxxg9Anv3IsmKY67YWGhPIlwONFDHCisv8Puh2Lop2EsnU0Ygvc7OJYniPgnChVUKXe0bW8nJ5ETIoKcgx2Fe5ILVGRlNcj4LujcNwjzfVGfc5M6vyYyWMG780xnicpMuQdB04t89/1O/w1cDnyilFU="
CHANNEL_SECRET = "18658576141b5169e2ea8ab7c840ddea"

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 品項與儲存
ALLOWED_ITEMS = ["草莓果醬", "甜燒餅", "年節禮盒", "鳳梨酥", "餐盒"]
order_records = defaultdict(lambda: defaultdict(int))
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

@handler.add(MemberJoinedEvent)
def handle_member_join(event):
    try:
        group_id = event.source.group_id
        for member in event.joined.members:
            user_id = member.user_id
            try:
                profile = line_bot_api.get_group_member_profile(group_id, user_id)
                name = profile.display_name
            except:
                name = "新朋友"
            
            text = f"@{name} 歡迎歡迎🫶🏻\n\n果醬當季製作、年節禮盒。\n一人作業請稍等闆娘😍"
            try:
                m = Mention(mentionees=[Mentionee(index=0, length=len(name)+1, user_id=user_id)])
                line_bot_api.push_message(group_id, TextSendMessage(text=text, mention=m))
            except:
                line_bot_api.push_message(group_id, TextSendMessage(text=text))
    except Exception as e:
        logging.error(f"Join Error: {e}")

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        text = event.message.text.strip()
        group_id = event.source.group_id
        user_id = event.source.user_id

        if text == "清空統計":
            order_records.clear()
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 已清空資料"))
            return

        items = re.findall(multi_count_pattern, text)
        if items:
            try:
                p = line_bot_api.get_group_member_profile(group_id, user_id)
                user_name = p.display_name
            except:
                user_name = "神秘客"

            updated = False
            for item_name, op, num in items:
                item = item_name.strip()
                if item in ALLOWED_ITEMS:
                    n = int(num)
                    if op == '+': order_records[user_name][item] += n
                    else: order_records[user_name][item] = max(0, order_records[user_name][item] - n)
                    updated = True
            
            if updated:
                res = "📋 【訂單明細】\n\n"
                totals = defaultdict(int)
                for n, its in order_records.items():
                    p_its = [f"{k}x{v}" for k, v in its.items() if v > 0]
                    if p_its:
                        res += f"👤 {n}: {', '.join(p_its)}\n"
                        for k, v in its.items(): totals[k] += v
                res += "\n📦 總計：\n" + "\n".join([f"▫️ {k}: {v}" for k, v in totals.items() if v > 0])
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res))
    except Exception as e:
        logging.error(f"Msg Error: {e}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)