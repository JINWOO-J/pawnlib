#!/usr/bin/env python3
import common
import atexit
from pawnlib.config import pawn
from pawnlib.config.first_run_checker import  one_time_run
from pawnlib.output.color_print import *
import multiprocessing
import concurrent.futures


def test_one_time_run(num_processes=10, key_name="", function=None):
    pool = multiprocessing.Pool(processes=num_processes)
    pawn.console.log(f"function name => {function.__name__}")
    results = pool.map(function, [key_name] * num_processes)
    pool.close()
    pool.join()

    final_results = {
        "FAIL": 0,
        "OK": 0,
    }
    for result in results:
        if result:
            final_results['OK'] += 1
        else:
            final_results['FAIL'] += 1

    pawn.console.log(f"num_processes={num_processes}, key_name: {key_name}")
    pawn.console.log(final_results)
    if final_results.get("OK", 0) > 1:
        pawn.console.rule("[red]ERROR")


def test_one_time_run_with_concurrent(num_processes=10, key_name="", function=None):
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
        pawn.console.log(f"function name => {function.__name__}")
        results = executor.map(function, [key_name] * num_processes)
        final_results = {
            "FAIL": 0,
            "OK": 0,
        }
        for result in results:
            if result:
                final_results['OK'] += 1
            else:
                final_results['FAIL'] += 1

        pawn.console.log(f"num_processes={num_processes}, key_name: {key_name}")
        pawn.console.log(final_results)
        if final_results.get("OK", 0) > 1:
            pawn.console.rule("[red]ERROR")


def main():
    test_one_time_run(num_processes=100, key_name="", function=one_time_run)


if __name__ == "__main__":
    main()
