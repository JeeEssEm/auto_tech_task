import time


def heavy_task(weight: int) -> int:
    time.sleep(weight)
    return 42
