# Применение миграций на Railway

## ⚠️ Важно: Используйте Railway Dashboard

Команда `railway run` выполняется локально, но база данных Railway доступна только через внутреннюю сеть. **Рекомендуется использовать Railway Dashboard** для выполнения миграций.

## Решение: Через Shell в Dashboard (Рекомендуется)

1. Откройте https://railway.app
2. Выберите проект **compassionate-optimism**
3. Выберите сервис **web**
4. Перейдите в **Deployments** → **Latest deployment**
5. Нажмите **Shell** (или **View Logs** → **Shell**)
6. В открывшемся терминале выполните:

```bash
cd backend
python -m alembic current
python -m alembic upgrade head
python -m alembic current
python scripts/check_migrations.py
```

## Быстрое решение: Создать таблицу напрямую через SQL

Если миграции не применяются из-за конфликтов, можно создать таблицу `notification_deliveries` напрямую через SQL:

1. Откройте Railway Dashboard
2. Выберите проект → сервис **web**
3. Перейдите в **Data** → **PostgreSQL** → **Query**
4. Выполните SQL из файла `create_notification_deliveries.sql`

Или через Railway CLI:
```powershell
railway connect postgres
# Затем выполните SQL команды из create_notification_deliveries.sql
```

## Если возникает ошибка "Can't locate revision"

Если вы видите ошибку `Can't locate revision identified by '0001_initial_schema'`, это означает, что в базе данных записана старая версия миграции. Выполните:

```bash
cd backend
# Проверить текущую версию в базе
python -c "from sqlalchemy import create_engine, text; import os; engine = create_engine(os.environ['DATABASE_URL'].replace('+asyncpg', '')); with engine.connect() as conn: print(conn.execute(text('SELECT version_num FROM alembic_version')).scalar())"

# Если версия '0001_initial_schema', обновите её на 'initial_schema'
python -c "from sqlalchemy import create_engine, text; import os; engine = create_engine(os.environ['DATABASE_URL'].replace('+asyncpg', '')); with engine.connect() as conn: conn.execute(text(\"UPDATE alembic_version SET version_num = 'initial_schema' WHERE version_num = '0001_initial_schema'\")); conn.commit()"

# Затем примените миграции
python -m alembic upgrade head
```

### Способ 2: Через Railway CLI (если shell работает)

```powershell
railway shell
cd backend
python -m alembic upgrade head
exit
```

### Способ 3: Создать одноразовый deployment

Можно создать временный сервис, который выполнит миграции при старте:

1. В Railway Dashboard создайте новый сервис
2. Укажите команду запуска: `cd backend && python -m alembic upgrade head`
3. После выполнения миграций удалите сервис

## Проверка результата

После применения миграций проверьте:

```bash
# Текущая версия миграций
python -m alembic current

# Проверка наличия таблиц
python scripts/check_migrations.py
```

Должна быть создана таблица `notification_deliveries` и другие таблицы для системы уведомлений.

