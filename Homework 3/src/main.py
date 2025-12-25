from time import perf_counter

from db import init_db, get_connection
from filters.filter1 import filter_1_get_symbols
from filters.filter2 import filter_2_check_dates
from filters.filter3 import filter_3_fill_data


def run_pipeline():
    start_ts = perf_counter()

    init_db()
    conn = get_connection()
    try:
        # Filter 1
        print("Filter 1")
        symbols = list(filter_1_get_symbols(conn))
        print("Filter 1 finished:", len(symbols), "symbols\n")

        # Filter 2
        print("Filter 2")
        tasks = list(filter_2_check_dates(symbols, conn))
        print("Filter 2 finished:", {len(tasks)}, "tasks\n")

        # Filter 3
        print("Filter 3")
        filter_3_fill_data(tasks, conn)
        print("Filter 3 finished.\n")

        end_ts = perf_counter()
        print("Total pipeline time:", end_ts - start_ts, "seconds")

    finally:
        conn.close()


if __name__ == "__main__":
    run_pipeline()
