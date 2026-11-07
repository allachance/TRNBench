"""Save results to CSV and summarize them."""

import csv
import statistics
from pathlib import Path

from trnbench.settings import COUNTS

FIELDS = ["host", "cpu", "cores", "threads", "deck", "n", "rep", "elapsed_s", "error"]


def read_rows(out: Path) -> list[dict]:
    """Read every row of a results CSV as strings, or nothing if it doesn't exist."""
    if not out.exists():
        return []
    with out.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def append_row(out: Path, row: dict) -> None:
    """Add one result to the CSV straight away, so an interrupted run keeps its data.

    Parameters
    ----------
    out : Path
        CSV file to append to. Created with a header row if it doesn't exist.
    row : dict
        Values keyed by names in `FIELDS`. Missing fields are left blank.

    Raises
    ------
    ValueError
        If `row` has a key not in `FIELDS`.
    """
    is_new = not out.exists()
    with out.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def group_rows(rows: list[dict]) -> dict[tuple, list[dict]]:
    """Group the rows by deck and concurrency."""
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        groups.setdefault((row["deck"], int(row["n"])), []).append(row)
    return groups


def summarize(rows: list[dict]) -> list[dict]:
    """Average the successful repeats of each deck and concurrency.

    Parameters
    ----------
    rows : list of dict
        Rows as read by `read_rows` (all values are strings). A blank
        ``elapsed_s`` marks a failed repeat.

    Returns
    -------
    list of dict
        One entry per (deck, n), sorted by deck then n, with keys ``deck``,
        ``n``, ``avg_s`` and ``failed_reps``. ``avg_s`` is None if every
        repeat failed.
    """
    summary = []
    for (deck, n), group in sorted(group_rows(rows).items()):
        times = [float(row["elapsed_s"]) for row in group if row["elapsed_s"]]
        summary.append({
            "deck": deck,
            "n": n,
            "avg_s": statistics.mean(times) if times else None,
            "failed_reps": len(group) - len(times),
        })
    return summary


def print_warmup_failures(failures: list[str]) -> None:
    """Print each warmup failure on its own line."""
    for failure in failures:
        print(f"warmup failed: {failure}", flush=True)


def print_result(rep: int, reps: int, deck: str, n: int, result: dict) -> None:
    """Print one progress line for a finished batch."""
    print(f"rep {rep}/{reps}  {deck:<8} n={n:<3} {result.get('elapsed_s', '-'):>10} s  {result.get('error', 'ok')}", flush=True)


def print_summary(summary: list[dict]) -> None:
    """Print the summary from `summarize` as a table."""
    print(f"\n{'deck':<10}{'n':>4}{'avg s':>12}{'failed':>8}")
    for row in summary:
        if row["avg_s"] is None:
            print(f"{row['deck']:<10}{row['n']:>4}{'all repeats failed':>20}")
        else:
            print(f"{row['deck']:<10}{row['n']:>4}{row['avg_s']:>12.3f}{row['failed_reps']:>8}")


def print_readme_rows(rows: list[dict]) -> None:
    """Print one README results row per deck, with an average time cell for each batch size in `COUNTS`."""
    cells: dict[str, dict[int, str]] = {}
    for row in summarize(rows):
        cell = "failed" if row["avg_s"] is None else f"{row['avg_s']:.2f}"
        cells.setdefault(row["deck"], {})[row["n"]] = cell
    for deck, by_n in cells.items():
        machine = f"| {rows[0]['cpu']} | {rows[0]['cores']}/{rows[0]['threads']} |"
        print(f"\n### {deck}\n\n{machine} {' | '.join(by_n.get(n, '') for n in COUNTS)} |")
