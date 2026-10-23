from .errors import TransientError

WAITS = (1, 2, 4)  # seconds before retry 1, 2, 3
MAX_WAIT = 30  # a longer retry_after means: stop now, do not hammer the service


class GaveUp(Exception):
    pass


def human(seconds):
    if seconds >= 3600:
        return f"{seconds / 3600:g}h"
    if seconds >= 60:
        return f"{seconds / 60:g}m"
    return f"{seconds:g}s"


def call_with_retry(fn, sleep, attempts):
    # only TransientError is retried. ValidationError and bugs go straight up.
    for n in range(1, len(WAITS) + 2):
        try:
            result = fn()
        except TransientError as ex:
            entry = {"attempt": n, "error": str(ex)}
            attempts.append(entry)
            if n > len(WAITS):
                raise GaveUp(f"gave up after {n} attempts: {ex}") from None
            wait = WAITS[n - 1] if ex.retry_after is None else ex.retry_after
            if wait > MAX_WAIT:
                raise GaveUp(f"gave up: retry after {human(wait)} is too long to wait ({ex})") from None
            entry["wait_s"] = wait
            sleep(wait)
        else:
            if attempts:
                attempts.append({"attempt": n, "result": "ok"})
            return result
