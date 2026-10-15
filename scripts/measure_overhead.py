"""Measure C0 baseline pipeline overhead — 7 repeats, clean data, take median."""
import sys, os, time, json, statistics
sys.stdout.reconfigure(encoding='utf-8')

import duckdb
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = str(PROJECT_ROOT / "data" / "warehouse.duckdb")
DBT_DIR = str(PROJECT_ROOT / "dbt_project")
RESULTS_DIR = PROJECT_ROOT / "results" / "baseline"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def reset_db(sf=0.1):
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS source")
    con.execute("INSTALL tpch; LOAD tpch;")
    con.execute(f"CALL dbgen(sf={sf}, schema='source')")
    con.close()


def read_dbt_times():
    """dbt-reported times from run_results.json (exclude CLI/python startup)."""
    data = json.loads((Path(DBT_DIR) / "target" / "run_results.json").read_text(encoding="utf-8"))
    model_exec = sum(r.get("execution_time", 0) for r in data["results"]) * 1000
    return model_exec, data.get("elapsed_time", 0) * 1000


def run_dbt_timed():
    start = time.perf_counter()
    subprocess.run(
        ["dbt", "run", "--profiles-dir", ".", "--project-dir", "."],
        capture_output=True, text=True, check=True,
        cwd=DBT_DIR, timeout=120,
    )
    wall = (time.perf_counter() - start) * 1000
    model_exec, dbt_elapsed = read_dbt_times()
    return wall, model_exec, dbt_elapsed


def stats(values):
    return {
        "values_ms": [round(v, 1) for v in values],
        "median_ms": round(statistics.median(values), 1),
        "mean_ms": round(statistics.mean(values), 1),
        "stdev_ms": round(statistics.stdev(values), 1),
        "min_ms": round(min(values), 1),
        "max_ms": round(max(values), 1),
    }


def main():
    sf = 0.1
    repeats = 7
    walls, execs, elapsed = [], [], []

    print(f"Measuring C0 pipeline time: {repeats} repeats, SF={sf}, clean data")
    print("=" * 64)

    for i in range(repeats):
        reset_db(sf)
        w, e, d = run_dbt_timed()
        walls.append(w); execs.append(e); elapsed.append(d)
        print(f"  Run {i+1}/{repeats}: wall={w:.0f}ms | dbt_elapsed={d:.0f}ms | model_exec={e:.0f}ms")

    wall_s, exec_s, el_s = stats(walls), stats(execs), stats(elapsed)
    print(f"\n{'='*64}")
    print(f"  Wall-clock (incl. dbt CLI startup): median {wall_s['median_ms']:.0f}ms, stdev {wall_s['stdev_ms']:.0f}ms")
    print(f"  dbt elapsed (graph execution):     median {el_s['median_ms']:.0f}ms, stdev {el_s['stdev_ms']:.0f}ms")
    print(f"  Sum of model exec times:           median {exec_s['median_ms']:.0f}ms, stdev {exec_s['stdev_ms']:.0f}ms")

    result = {
        "config": "C0",
        "scale_factor": sf,
        "repeat_count": repeats,
        "note": ("wall = subprocess wall-clock incl. ~python/dbt CLI startup; "
                 "dbt_elapsed = run_results.json elapsed_time; "
                 "model_exec = sum of per-model execution_time (threads=4, so can exceed elapsed). "
                 "Overhead % of later configs should be computed on BOTH wall and dbt_elapsed."),
        "wall": wall_s,
        "dbt_elapsed": el_s,
        "model_exec": exec_s,
        # backward-compatible keys (wall-clock)
        "times_ms": wall_s["values_ms"],
        "median_ms": wall_s["median_ms"],
        "mean_ms": wall_s["mean_ms"],
        "stdev_ms": wall_s["stdev_ms"],
        "min_ms": wall_s["min_ms"],
        "max_ms": wall_s["max_ms"],
    }

    out = RESULTS_DIR / "baseline_c0_overhead.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved to: {out}")


if __name__ == "__main__":
    main()
