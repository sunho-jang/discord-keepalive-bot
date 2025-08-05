import firebase_admin
from firebase_admin import credentials, db
import json
import os

# 환경 변수에서 JSON 문자열을 가져옴
firebase_key_str = os.environ.get("FIREBASE_KEY_JSON")
firebase_key_dict = json.loads(firebase_key_str)

cred = credentials.Certificate(firebase_key_dict)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://discord-bot-data-58877-default-rtdb.asia-southeast1.firebasedatabase.app'
})
