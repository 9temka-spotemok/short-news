"""
Utilities for sharing a single asyncio event loop inside Celery workers.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Awaitable, TypeVar

import nest_asyncio
from loguru import logger

T = TypeVar("T")

_loop_lock = threading.Lock()
_worker_loop: asyncio.AbstractEventLoop | None = None
_PENDING_TIMEOUT = 1.0
_CANCEL_TIMEOUT = 0.5

# Периодический cleanup каждые N выполнений
_CLEANUP_INTERVAL = 100
_execution_count = 0
_execution_count_lock = threading.Lock()


def get_or_create_loop() -> asyncio.AbstractEventLoop:
    """
    Return a reusable asyncio loop for the current Celery worker process.
    """
    global _worker_loop
    loop = _worker_loop

    if loop is None or loop.is_closed():
        with _loop_lock:
            # Double-check pattern
            loop = _worker_loop
            if loop is None or loop.is_closed():
                loop = asyncio.new_event_loop()
                nest_asyncio.apply(loop)
                _worker_loop = loop
                logger.debug("Created new event loop for Celery worker")

    assert loop is not None, "Failed to initialise asyncio event loop"
    
    # Проверяем, что loop не закрыт и не запущен в другом потоке
    if loop.is_closed():
        with _loop_lock:
            if _worker_loop is loop:
                _worker_loop = None
            loop = asyncio.new_event_loop()
            nest_asyncio.apply(loop)
            _worker_loop = loop
            logger.debug("Recreated event loop (was closed)")
    
    asyncio.set_event_loop(loop)
    return loop


def _cleanup_loop(loop: asyncio.AbstractEventLoop) -> None:
    """
    Best-effort cleanup of pending tasks and async generators.
    
    ВНИМАНИЕ: Не вызывать после каждого выполнения, только периодически
    или при явной необходимости, чтобы не закрывать async генераторы
    из AsyncSession, которые еще используются.
    """
    if loop.is_closed():
        return
    
    try:
        # Проверяем только pending задачи, не трогаем async генераторы
        # чтобы не конфликтовать с AsyncSession
        pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
        if pending:
            logger.debug(f"Found {len(pending)} pending tasks during cleanup")
            try:
                gather = asyncio.gather(*pending, return_exceptions=True)
                loop.run_until_complete(asyncio.wait_for(gather, timeout=_PENDING_TIMEOUT))
            except (asyncio.TimeoutError, RuntimeError) as e:
                logger.debug(f"Timeout during task cleanup: {e}")
                for task in pending:
                    if not task.done():
                        task.cancel()
                try:
                    gather = asyncio.gather(*pending, return_exceptions=True)
                    loop.run_until_complete(asyncio.wait_for(gather, timeout=_CANCEL_TIMEOUT))
                except Exception as exc:
                    logger.debug(f"Error during task cancellation: {exc}")
    except Exception as exc:
        logger.debug("Failed to cleanup pending asyncio tasks: %s", exc)
    
    # НЕ вызываем shutdown_asyncgens() здесь, так как это закрывает
    # async генераторы из AsyncSession, которые могут быть еще использованы


def _maybe_cleanup_loop(loop: asyncio.AbstractEventLoop) -> None:
    """
    Периодически вызывать cleanup для предотвращения утечек.
    """
    global _execution_count
    
    with _execution_count_lock:
        _execution_count += 1
        should_cleanup = (_execution_count % _CLEANUP_INTERVAL == 0)
    
    if should_cleanup:
        logger.debug(f"Periodic cleanup (execution #{_execution_count})")
        _cleanup_loop(loop)


def run_async_task(coro: Awaitable[T]) -> T:
    """
    Execute an async coroutine inside the shared Celery event loop.
    
    Обрабатывает ошибки "different loop" путем пересоздания loop.
    """
    global _worker_loop
    
    if not asyncio.iscoroutine(coro):
        raise TypeError("run_async_task expects an awaitable/coroutine object")

    max_retries = 2
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            loop = get_or_create_loop()
            
            # Проверяем, что loop не закрыт и готов к использованию
            if loop.is_closed():
                logger.warning("Event loop is closed, recreating...")
                with _loop_lock:
                    _worker_loop = None
                loop = get_or_create_loop()
            
            result = loop.run_until_complete(coro)
            
            # Периодический cleanup вместо после каждого выполнения
            _maybe_cleanup_loop(loop)
            
            return result
            
        except RuntimeError as e:
            error_msg = str(e)
            if "different loop" in error_msg or "attached to a different loop" in error_msg:
                last_exception = e
                logger.warning(
                    f"Event loop conflict detected (attempt {attempt + 1}/{max_retries}): {e}"
                )
                
                # Пересоздаем loop при конфликте
                with _loop_lock:
                    if _worker_loop is not None:
                        try:
                            if not _worker_loop.is_closed():
                                _worker_loop.close()
                        except Exception:
                            pass
                    _worker_loop = None
                
                if attempt < max_retries - 1:
                    logger.debug("Recreating event loop and retrying...")
                    continue
                else:
                    logger.error("Failed to resolve event loop conflict after retries")
                    raise
            else:
                # Другие RuntimeError не связаны с event loop
                raise
        except Exception as e:
            # Другие исключения пробрасываем как есть
            raise
    
    # Если дошли сюда, значит все попытки исчерпаны
    if last_exception:
        raise last_exception
    raise RuntimeError("Failed to execute async task")


