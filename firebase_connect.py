import firebase_admin
from firebase_admin import credentials, db

# Secret File 방식으로 Firebase 인증 파일 로드
cred = credentials.Certificate("/etc/secrets/serviceAccountKey.json")

# Firebase 앱 초기화
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://discord-bot-data-58877-default-rtdb.asia-southeast1.firebasedatabase.app'
})
