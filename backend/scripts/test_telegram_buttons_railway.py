"""
Скрипт для тестирования кнопок Telegram бота на проде через Railway CLI

Использование:
    # Тестирование кнопки digest_settings_all
    python -m scripts.test_telegram_buttons_railway --chat-id 1018308084 --button digest_settings_all --webhook-url https://web-production-6bf5.up.railway.app/api/v1/telegram/webhook

    # Тестирование кнопки digest_settings_tracked
    python -m scripts.test_telegram_buttons_railway --chat-id 1018308084 --button digest_settings_tracked --webhook-url https://web-production-6bf5.up.railway.app/api/v1/telegram/webhook

    # Тестирование обеих кнопок подряд
    python -m scripts.test_telegram_buttons_railway --chat-id 1018308084 --button all --webhook-url https://web-production-6bf5.up.railway.app/api/v1/telegram/webhook

    # Проверка логов через Railway CLI (после тестирования)
    railway logs --service "web" --since 2m | grep -i "callback\|digest_settings"
"""

import sys
import argparse
import asyncio
import json
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))


async def send_test_callback(
    webhook_url: str,
    chat_id: str,
    callback_data: str,
    callback_id: int = None
) -> Dict[str, Any]:
    """
    Отправить тестовый callback запрос к webhook
    
    Args:
        webhook_url: URL webhook endpoint
        chat_id: Telegram chat ID
        callback_data: Данные callback кнопки
        callback_id: ID callback запроса (для уникальности)
    
    Returns:
        Response от webhook
    """
    if callback_id is None:
        callback_id = int(datetime.now().timestamp() * 1000)
    
    # Создаем структуру callback_query как в реальном Telegram update
    update = {
        "update_id": callback_id,
        "callback_query": {
            "id": f"{callback_id}",
            "from": {
                "id": int(chat_id),
                "is_bot": False,
                "first_name": "Test",
                "username": "test_user",
                "language_code": "ru"
            },
            "message": {
                "message_id": 9999,
                "from": {
                    "id": 8358550051,
                    "is_bot": True,
                    "first_name": "short-news",
                    "username": "short_news_sender_bot"
                },
                "chat": {
                    "id": int(chat_id),
                    "first_name": "Test",
                    "username": "test_user",
                    "type": "private"
                },
                "date": int(datetime.now().timestamp()),
                "text": "🛠️ **Digest Settings**\n\nCurrent mode: **All News**\n\nChoose digest mode:\n• **All News** — all available news\n• **Tracked Only** — only news from your tracked companies",
                "reply_markup": {
                    "inline_keyboard": [
                        [
                            {
                                "text": "✅ All News",
                                "callback_data": "digest_settings_all"
                            },
                            {
                                "text": "❌ Tracked Only",
                                "callback_data": "digest_settings_tracked"
                            }
                        ],
                        [
                            {
                                "text": "🔙 Back to Main Menu",
                                "callback_data": "main_menu"
                            }
                        ]
                    ]
                }
            },
            "chat_instance": f"{callback_id}",
            "data": callback_data
        }
    }
    
    print(f"\n📤 Отправка callback запроса:")
    print(f"   Chat ID: {chat_id}")
    print(f"   Callback data: {callback_data}")
    print(f"   Webhook URL: {webhook_url}")
    print(f"\n📋 Payload:")
    print(json.dumps(update, indent=2, ensure_ascii=False))
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=update,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_text = await response.text()
                
                print(f"\n📥 Ответ от webhook:")
                print(f"   Status: {response.status}")
                print(f"   Response: {response_text[:500]}")
                
                if response.status == 200:
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        return {"status": "ok", "raw_response": response_text}
                else:
                    return {
                        "status": "error",
                        "status_code": response.status,
                        "response": response_text
                    }
                    
    except aiohttp.ClientError as e:
        print(f"\n❌ Ошибка при отправке запроса: {e}")
        return {"status": "error", "error": str(e)}
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        return {"status": "error", "error": str(e)}


async def test_button(webhook_url: str, chat_id: str, button: str):
    """Тестировать конкретную кнопку"""
    print("\n" + "=" * 70)
    print(f"🧪 Тестирование кнопки: {button}")
    print("=" * 70)
    
    result = await send_test_callback(webhook_url, chat_id, button)
    
    if result.get("status") == "ok":
        print(f"\n✅ Кнопка {button} отправлена успешно!")
        print(f"   Проверьте логи Railway для подтверждения обработки:")
        print(f"   railway logs --service 'web' --since 1m | grep -i '{button}'")
    else:
        print(f"\n❌ Ошибка при отправке кнопки {button}")
        print(f"   Результат: {result}")
    
    return result


async def main():
    parser = argparse.ArgumentParser(
        description="Тестирование кнопок Telegram бота через Railway webhook"
    )
    parser.add_argument(
        "--chat-id",
        type=str,
        required=True,
        help="Telegram chat ID пользователя"
    )
    parser.add_argument(
        "--button",
        type=str,
        required=True,
        choices=["digest_settings_all", "digest_settings_tracked", "all"],
        help="Кнопка для тестирования (digest_settings_all, digest_settings_tracked, или all для обеих)"
    )
    parser.add_argument(
        "--webhook-url",
        type=str,
        default="https://web-production-6bf5.up.railway.app/api/v1/telegram/webhook",
        help="URL webhook endpoint (по умолчанию: Railway production)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("🤖 Тестирование кнопок Telegram бота через Railway")
    print("=" * 70)
    print(f"Chat ID: {args.chat_id}")
    print(f"Webhook URL: {args.webhook_url}")
    print("=" * 70)
    
    if args.button == "all":
        # Тестируем обе кнопки
        print("\n📝 Тестирование обеих кнопок...")
        
        results = []
        
        # Тест 1: digest_settings_all
        result1 = await test_button(
            args.webhook_url,
            args.chat_id,
            "digest_settings_all"
        )
        results.append(("digest_settings_all", result1))
        
        # Небольшая задержка между запросами
        await asyncio.sleep(2)
        
        # Тест 2: digest_settings_tracked
        result2 = await test_button(
            args.webhook_url,
            args.chat_id,
            "digest_settings_tracked"
        )
        results.append(("digest_settings_tracked", result2))
        
        # Итоги
        print("\n" + "=" * 70)
        print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
        print("=" * 70)
        
        for button, result in results:
            status = "✅" if result.get("status") == "ok" else "❌"
            print(f"{status} {button}: {result.get('status', 'unknown')}")
        
        print("\n💡 Следующие шаги:")
        print("   1. Проверьте логи Railway:")
        print("      railway logs --service 'web' --since 2m | grep -i 'callback\\|digest_settings'")
        print("   2. Убедитесь, что видны записи:")
        print("      - 'Processing callback from <chat_id>: digest_settings_*'")
        print("      - 'Digest mode changed to * for user *'")
        print("   3. Проверьте в Telegram боте, что настройки изменились")
    else:
        # Тестируем одну кнопку
        result = await test_button(
            args.webhook_url,
            args.chat_id,
            args.button
        )
        
        print("\n💡 Следующие шаги:")
        print("   1. Проверьте логи Railway:")
        print(f"      railway logs --service 'web' --since 1m | grep -i '{args.button}'")
        print("   2. Убедитесь, что видны записи:")
        print(f"      - 'Processing callback from {args.chat_id}: {args.button}'")
        print("   3. Проверьте в Telegram боте, что настройки изменились")


if __name__ == "__main__":
    asyncio.run(main())
















