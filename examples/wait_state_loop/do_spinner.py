#!/usr/bin/env python3
try:
    import common
except:
    pass
import time
from pawnlib.utils.operate_handler import WaitStateLoop, Spinner
import random


def check_func():
    time.sleep(0.2)
    random_int = random.randint(1, 100)
    return random_int


def loop_exit_func(result):
    if result % 10 == 1.5:
        return True
    return False


def main():
    with Spinner(text="Wait message") as spinner:
        while True:
            res = check_func()
            spinner.title(f"new message {res}")

if __name__ == "__main__":
    main()
