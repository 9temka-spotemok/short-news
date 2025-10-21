# RAILWAY PORT ERROR - URGENT FIX

## Проблема
Railway все еще использует старую команду запуска с `$PORT` вместо правильной обработки переменной окружения.

## Решение
Обновлен `backend/main.py` для правильной обработки переменной PORT.

## Изменения
1. ✅ Обновлен `backend/main.py` - теперь читает PORT из переменных окружения
2. ✅ Обновлен `railway.json` - использует `cd backend && python main.py`
3. ✅ Создан `start_server.py` - альтернативный скрипт запуска

## Команды для деплоя
```bash
git add .
git commit -m "Fix Railway PORT variable - use main.py directly"
git push origin main
```

## Альтернативные варианты запуска
Если проблема сохранится, попробуйте в Railway Dashboard:
1. Settings → Deploy → Start Command: `cd backend && python main.py`
2. Или: `python start_server.py`
3. Или: `cd backend && python start.py`

## Проверка
После деплоя:
- Логи должны показывать: "Starting server on port [номер]"
- Health check: `/health`
- Никаких ошибок с `$PORT`

## Если ничего не помогает
Создайте в Railway переменную окружения:
- Name: `PORT`
- Value: `8000`
- И используйте команду: `cd backend && python main.py`
