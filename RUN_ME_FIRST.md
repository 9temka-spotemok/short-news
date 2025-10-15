# ⚡ ЗАПУСТИТЕ ЭТО ПЕРВЫМ

## 🔴 Критически важно!

Перед тестированием функций выполните эти 3 команды:

---

## Шаг 1: Примените миграции

```bash
cd backend
python -m alembic upgrade head
```

**Ожидается:** `Running upgrade b5037d3c878c -> c1d2e3f4g5h6`

---

## Шаг 2: Инициализируйте настройки пользователей

```bash
python scripts/init_all_settings.py
```

**Ожидается:** `Created X user preferences` и `Created X notification settings`

**Это создаст:**
- UserPreferences для всех пользователей
- NotificationSettings для всех пользователей

**Без этого шага дайджесты НЕ БУДУТ РАБОТАТЬ!**

---

## Шаг 3: Запустите сервисы

### Terminal 1 - Backend:
```bash
cd backend
python -m uvicorn main:app --reload
```

### Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

---

## ✅ Готово!

Теперь откройте:
```
http://localhost:5173
```

Войдите в систему и протестируйте:
- http://localhost:5173/digest-settings
- http://localhost:5173/notifications  
- http://localhost:5173/competitor-analysis

---

## 🐛 Если не работает

Смотрите:
- `TROUBLESHOOTING_DIGESTS.md` - диагностика
- `SETUP_NEW_FEATURES.md` - подробная настройка

---

## 🎯 Автоматический запуск (альтернатива)

**Windows:**
```powershell
.\setup_features.ps1
```

**Linux/Mac:**
```bash
chmod +x setup_features.sh
./setup_features.sh
```

Эти скрипты выполнят Шаги 1-2 автоматически!



