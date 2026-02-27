"""Minimal Celery stub for offline/test environments."""
from __future__ import annotations

import asyncio
import concurrent.futures


class Celery:
    def __init__(self, name="celery", broker=None, backend=None, **kwargs):
        self.name = name
        self.conf = _CeleryConf()
        self._tasks = {}

    def conf_update(self, **kwargs):
        pass

    def task(self, *args, **kwargs):
        task_name = kwargs.get("name")

        def decorator(func):
            name = task_name or f"{func.__module__}.{func.__qualname__}"
            self._tasks[name] = func
            return func

        if args and callable(args[0]):
            func = args[0]
            name = task_name or f"{func.__module__}.{func.__qualname__}"
            self._tasks[name] = func
            return func
        return decorator

    def send_task(self, name, args=None, kwargs=None, **options):
        return _AsyncResult()

    def signature(self, name, args=None, kwargs=None, **options):
        return _Signature(self, name, args, kwargs)


class _Signature:
    def __init__(self, app, name, args=None, kwargs=None):
        self._app = app
        self.name = name
        self.args = args or []
        self.kwargs = kwargs or {}

    def apply_async(self, countdown=None, **options):
        eager = getattr(self._app.conf, "task_always_eager", False)
        if eager:
            task_func = self._app._tasks.get(self.name)
            if task_func is not None:
                propagate = getattr(self._app.conf, "task_eager_propagates", False)
                return _run_task_eagerly(task_func, self.args, self.kwargs, propagate)
        return _AsyncResult()

    def delay(self, *args, **kwargs):
        return _AsyncResult()


def _run_task_eagerly(task_func, args, kwargs, propagate=False):
    """Run a task eagerly, using a thread pool if called from a running event loop."""
    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    if running_loop and running_loop.is_running():
        # Called from within a running event loop (e.g. an ASGI endpoint).
        # Execute in a thread pool so the task's asyncio.run() calls don't
        # try to schedule onto the already-running loop (which would deadlock).
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(task_func, *args, **kwargs)
            try:
                result = future.result()
                return _AsyncResult(result=result)
            except Exception as exc:  # noqa: BLE001
                if propagate:
                    raise
                return _AsyncResult(result=exc, failed=True)
    else:
        try:
            result = task_func(*args, **kwargs)
            return _AsyncResult(result=result)
        except Exception as exc:  # noqa: BLE001
            if propagate:
                raise
            return _AsyncResult(result=exc, failed=True)


class _CeleryConf:
    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _AsyncResult:
    def __init__(self, result=None, failed=False):
        self.id = "stub-task-id"
        self.status = "FAILURE" if failed else "SUCCESS"
        self._result = result
        self._failed = failed

    def get(self, timeout=None):
        return self._result

    def ready(self):
        return True

    def failed(self):
        return self._failed
