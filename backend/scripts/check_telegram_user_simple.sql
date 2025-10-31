-- Простая версия диагностического скрипта для Railway CLI
-- Замените '1018308084' на ваш Chat ID перед выполнением

-- ============================================================
-- БЫСТРАЯ ПРОВЕРКА (замените 1018308084 на ваш Chat ID)
-- ============================================================

-- 1. Основная проверка
SELECT 
    up.user_id,
    up.telegram_chat_id,
    up.telegram_enabled,
    up.digest_enabled,
    up.telegram_digest_mode,
    LENGTH(up.telegram_chat_id) as chat_id_length,
    u.email as user_email,
    CASE 
        WHEN up.telegram_enabled = true THEN '✅ Telegram enabled - /digest ДОЛЖЕН работать'
        WHEN up.telegram_enabled = false THEN '❌ Telegram DISABLED - нужно включить!'
        ELSE '⚠️ telegram_enabled is NULL'
    END as status
FROM user_preferences up
LEFT JOIN users u ON u.id = up.user_id
WHERE up.telegram_chat_id = '1018308084';

-- 2. Проверка с TRIM (если есть пробелы)
SELECT 
    up.user_id,
    TRIM(up.telegram_chat_id) as trimmed_chat_id,
    up.telegram_enabled,
    u.email as user_email,
    'Проверка с TRIM' as note
FROM user_preferences up
LEFT JOIN users u ON u.id = up.user_id
WHERE TRIM(up.telegram_chat_id) = '1018308084';

-- 3. Проверка с telegram_enabled = TRUE
SELECT 
    up.user_id,
    up.telegram_chat_id,
    up.telegram_enabled,
    u.email as user_email,
    '✅ Найден с telegram_enabled = true' as status
FROM user_preferences up
LEFT JOIN users u ON u.id = up.user_id
WHERE up.telegram_chat_id = '1018308084'
  AND up.telegram_enabled = true;

-- 4. ИТОГОВАЯ ДИАГНОСТИКА
SELECT 
    COUNT(*) FILTER (WHERE up.telegram_chat_id = '1018308084') as exact_match_count,
    COUNT(*) FILTER (WHERE up.telegram_chat_id = '1018308084' AND up.telegram_enabled = true) as enabled_count,
    CASE 
        WHEN COUNT(*) FILTER (WHERE up.telegram_chat_id = '1018308084' AND up.telegram_enabled = true) > 0
        THEN '✅ /digest ДОЛЖЕН РАБОТАТЬ'
        WHEN COUNT(*) FILTER (WHERE up.telegram_chat_id = '1018308084') > 0
        THEN '⚠️ Пользователь найден, но telegram_enabled = false. Выполните: UPDATE user_preferences SET telegram_enabled = true WHERE telegram_chat_id = ''1018308084'';'
        ELSE '❌ Пользователь НЕ НАЙДЕН. Нужно добавить Chat ID в профиль.'
    END as diagnosis
FROM user_preferences up
WHERE up.telegram_chat_id = '1018308084';

