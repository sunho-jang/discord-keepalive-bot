import firebase_admin
from firebase_admin import credentials, db

# JSON 키 파일 경로
cred = credentials.Certificate("serviceAccountKey.json")

# Firebase 초기화 (Realtime Database URL은 자신의 DB URL로 바꿔줘야 해)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://discord-bot-data-xxxxx.firebaseio.com/'  # 너의 주소로 바꿔
})
