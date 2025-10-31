-- Диагностический SQL скрипт для проверки Telegram пользователя на Railway
-- Использование: railway connect postgres, затем выполните этот скрипт

-- Замените '1018308084' на ваш Chat ID
\set chat_id '1018308084'

-- ============================================================
-- 1. ПРОВЕРКА ПОЛЬЗОВАТЕЛЯ ПО CHAT_ID (EXACT MATCH)
-- ============================================================
SELECT 
    '1. EXACT MATCH' as check_type,
    up.user_id,
    up.telegram_chat_id,
    up.telegram_enabled,
    up.digest_enabled,
    up.telegram_digest_mode,
    LENGTH(up.telegram_chat_id) as chat_id_length,
    up.telegram_chat_id::text as chat_id_text,
    u.email as user_email,
    CASE 
        WHEN up.telegram_enabled = true THEN '✅ Telegram enabled'
        WHEN up.telegram_enabled = false THEN '❌ Telegram DISABLED - нужно включить!'
        ELSE '⚠️ telegram_enabled is NULL'
    END as status
FROM user_preferences up
LEFT JOIN users u ON u.id = up.user_id
WHERE up.telegram_chat_id = :chat_id;

-- ============================================================
-- 2. ПРОВЕРКА С TRIM (на случай пробелов)
-- ============================================================
SELECT 
    '2. TRIM MATCH' as check_type,
    up.user_id,
    up.telegram_chat_id,
    up.telegram_enabled,
    LENGTH(up.telegram_chat_id) as chat_id_length,
    TRIM(up.telegram_chat_id) as trimmed_chat_id,
    u.email as user_email,
    CASE 
        WHEN up.telegram_enabled = true THEN '✅ Telegram enabled'
        ELSE '❌ Telegram DISABLED или не найден'
    END as status
FROM user_preferences up
LEFT JOIN users u ON u.id = up.user_id
WHERE TRIM(up.telegram_chat_id) = :chat_id;

-- ============================================================
-- 3. ПРОВЕРКА С telegram_enabled = TRUE (exact)
-- ============================================================
SELECT 
    '3. EXACT + ENABLED' as check_type,
    up.user_id,
    up.telegram_chat_id,
    up.telegram_enabled,
    u.email as user_email,
    CASE 
        WHEN up.user_id IS NOT NULL THEN '✅ Найден с telegram_enabled = true'
        ELSE '❌ Не найден или telegram_enabled = false'
    END as status
FROM user_preferences up
LEFT JOIN users u ON u.id = up.user_id
WHERE up.telegram_chat_id = :chat_id
  AND up.telegram_enabled = true;

-- ============================================================
-- 4. ПРОВЕРКА С TRIM + telegram_enabled = TRUE
-- ============================================================
SELECT 
    '4. TRIM + ENABLED' as check_type,
    up.user_id,
    up.telegram_chat_id,
    up.telegram_enabled,
    u.email as user_email,
    CASE 
        WHEN up.user_id IS NOT NULL THEN '✅ Найден с trim и telegram_enabled = true'
        ELSE '❌ Не найден или telegram_enabled = false'
    END as status
FROM user_preferences up
LEFT JOIN users u ON u.id = up.user_id
WHERE TRIM(up.telegram_chat_id) = :chat_id
  AND up.telegram_enabled = true;

-- ============================================================
-- 5. ПОИСК ВСЕХ ПОХОЖИХ CHAT_ID (для отладки)
-- ============================================================
SELECT 
    '5. SIMILAR CHAT_IDS' as check_type,
    up.user_id,
    up.telegram_chat_id,
    up.telegram_enabled,
    LENGTH(up.telegram_chat_id) as chat_id_length,
    REPLACE(up.telegram_chat_id, ' ', '_') as chat_id_with_spaces_marked,
    u.email as user_email
FROM user_preferences up
LEFT JOIN users u ON u.id = up.user_id
WHERE up.telegram_chat_id LIKE '%' || :chat_id || '%'
   OR TRIM(up.telegram_chat_id) = :chat_id;

-- ============================================================
-- 6. ИТОГОВАЯ ДИАГНОСТИКА
-- ============================================================
SELECT 
    '6. SUMMARY' as check_type,
    COUNT(*) FILTER (WHERE up.telegram_chat_id = :chat_id) as exact_match_count,
    COUNT(*) FILTER (WHERE TRIM(up.telegram_chat_id) = :chat_id) as trim_match_count,
    COUNT(*) FILTER (WHERE up.telegram_chat_id = :chat_id AND up.telegram_enabled = true) as exact_enabled_count,
    COUNT(*) FILTER (WHERE TRIM(up.telegram_chat_id) = :chat_id AND up.telegram_enabled = true) as trim_enabled_count,
    CASE 
        WHEN COUNT(*) FILTER (WHERE up.telegram_chat_id = :chat_id AND up.telegram_enabled = true) > 0 
             OR COUNT(*) FILTER (WHERE TRIM(up.telegram_chat_id) = :chat_id AND up.telegram_enabled = true) > 0
        THEN '✅ /digest ДОЛЖЕН РАБОТАТЬ'
        WHEN COUNT(*) FILTER (WHERE up.telegram_chat_id = :chat_id) > 0
        THEN '⚠️ Пользователь найден, но telegram_enabled = false. Нужно включить!'
        ELSE '❌ Пользователь НЕ НАЙДЕН. Нужно добавить Chat ID в профиль.'
    END as diagnosis
FROM user_preferences up
WHERE up.telegram_chat_id = :chat_id
   OR TRIM(up.telegram_chat_id) = :chat_id;

-- ============================================================
-- 7. ПРОВЕРКА НАСТРОЕК ДАЙДЖЕСТА
-- ============================================================
SELECT 
    '7. DIGEST SETTINGS' as check_type,
    up.user_id,
    up.digest_enabled,
    up.digest_frequency,
    up.telegram_digest_mode,
    u.email as user_email,
    CASE 
        WHEN up.digest_enabled = true AND up.telegram_enabled = true THEN '✅ Всё настроено'
        WHEN up.digest_enabled = false THEN '⚠️ Digest disabled'
        WHEN up.telegram_enabled = false THEN '⚠️ Telegram disabled'
        ELSE '❌ Не настроено'
    END as status
FROM user_preferences up
LEFT JOIN users u ON u.id = up.user_id
WHERE up.telegram_chat_id = :chat_id
   OR TRIM(up.telegram_chat_id) = :chat_id;

