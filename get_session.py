"""
Запусти этот файл ОДИН РАЗ чтобы получить SESSION_STRING.
Потом вставь результат в .env и этот файл можно удалить.

Команда: python get_session.py
"""
from pyrogram import Client

api_id   = input("Введи API_ID: ").strip()
api_hash = input("Введи API_HASH: ").strip()

print("\nСейчас Telegram попросит номер телефона и код подтверждения.")
print("Используй аккаунт который будет читать каналы (не бот, а обычный аккаунт).\n")

with Client("temp_session", api_id=int(api_id), api_hash=api_hash) as app:
    session = app.export_session_string()
    print("\n" + "="*60)
    print("Твой SESSION_STRING:")
    print("="*60)
    print(session)
    print("="*60)
    print("\nСкопируй эту строку и вставь в .env файл в строку SESSION_STRING=")
    
