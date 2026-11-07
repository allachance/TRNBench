"""Compare computers by how long they take to finish batches of TRNSYS simulations at each level of concurrency.

Full run:    uv run trnbench
Setup check: uv run trnbench --counts 1 --reps 1

Every run starts fresh and writes a new results/<hostname>-<date>-<time>.csv, one row per batch as it finishes.
Each deck runs once first as an unrecorded warmup, all at the same time.
"""

import argparse
import itertools
import os
import platform
import subprocess
import winreg
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from trnrun import TrnrunError

from trnbench.batch import run_batch, warmup
from trnbench.report import (
    append_row,
    print_readme_rows,
    print_result,
    print_summary,
    print_warmup_failures,
    read_rows,
    summarize,
)
from trnbench.settings import COUNTS, DECK_DIR, DECK_SETTINGS, REPS, ROOT


def cpu_name() -> str:
    """Read the CPU model name from the Windows registry."""
    with winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
    ) as key:
        return winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()


def core_count() -> int:
    """Count the physical CPU cores across all sockets; os.cpu_count gives threads."""
    powershell = Path(os.environ["SYSTEMROOT"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    command = "(Get-CimInstance Win32_Processor | Measure-Object NumberOfCores -Sum).Sum"
    return int(subprocess.run([powershell, "-NoProfile", "-Command", command], capture_output=True, text=True, check=True).stdout)


def machine_info() -> dict:
    """Describe this computer for the host, cpu, cores and threads CSV columns."""
    return {"host": platform.node(), "cpu": cpu_name(), "cores": core_count(), "threads": os.cpu_count()}


def deck_names() -> list[str]:
    """List the names of the decks in DECK_DIR, sorted."""
    return sorted(deck.stem for deck in DECK_DIR.glob("*.dck"))


def check_decks(decks: Sequence[str]) -> None:
    """Stop before a long run if a deck has no settings."""
    unset = [deck for deck in decks if deck not in DECK_SETTINGS]
    if unset:
        raise ValueError(
            f"deck has no entry in DECK_SETTINGS (trnbench/settings.py): {unset[0]}",
        )


def try_batch(deck: Path, n: int) -> dict:
    """Run a batch, turning a trnrun error into a result."""
    try:
        return run_batch(deck, n)
    except TrnrunError as error:
        return {"error": str(error)}  # A limit reached at high n is a result too.


def run_jobs(
    jobs: list[tuple[int, str, int]], reps: int, machine: dict, out: Path,
) -> None:
    """Run each batch, saving and printing its result straight away.

    Parameters
    ----------
    jobs : list of tuple of (int, str, int)
        ``(rep, deck, n)`` for each batch, in the order to run them.
    reps : int
        Total number of repeats, for the progress line only.
    machine : dict
        Machine columns from `machine_info`, added to every row.
    out : Path
        CSV file each result is appended to.
    """
    for rep, deck, n in jobs:
        result = try_batch(DECK_DIR / f"{deck}.dck", n)
        append_row(out, {**machine, "deck": deck, "n": n, "rep": rep, **result})
        print_result(rep, reps, deck, n, result)


def main(
    counts: Sequence[int] = COUNTS,
    reps: int = REPS,
    decks: Sequence[str] | None = None,
    out: Path | None = None,
) -> None:
    """Run the whole benchmark, save every batch to a new CSV and print a summary.

    Parameters
    ----------
    counts : sequence of int, optional
        Numbers of simulations to run at once. Defaults to `COUNTS`.
    reps : int, optional
        Times to repeat the full sweep. Defaults to `REPS`.
    decks : sequence of str, optional
        Deck names to run. Defaults to every deck in `DECK_DIR`.
    out : Path, optional
        New CSV to write. Defaults to ``results/<hostname>-<date>-<time>.csv``.

    Raises
    ------
    ValueError
        If a deck has no entry in `DECK_SETTINGS`.
    FileExistsError
        If `out` already exists, so earlier results are never overwritten.
    """
    decks = sorted(decks or deck_names())
    check_decks(decks)

    machine = machine_info()
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    out = out or ROOT / "results" / f"{machine['host']}-{stamp}.csv"
    if out.exists():
        raise FileExistsError(f"results file already exists, choose another --out: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"{machine['cpu']}, {machine['cores']} cores, {machine['threads']} threads")

    # Each repeat sweeps everything, so slow drift such as CPU heating spreads across repeats instead of skewing one.
    todo = list(itertools.product(range(1, reps + 1), decks, counts))
    if todo:
        print("Warming up", flush=True)
        print_warmup_failures(warmup([DECK_DIR / f"{deck}.dck" for deck in decks]))
    run_jobs(todo, reps, machine, out)
    rows = read_rows(out)
    print_summary(summarize(rows))
    print("\nREADME results rows:")
    print_readme_rows(rows)
    print(f"\nRaw results: {out}")


def positive_int(text: str) -> int:
    """Parse a command-line value as an integer of at least 1."""
    value = int(text)
    if value < 1:
        raise ValueError
    return value


def parse_args(argv: Sequence[str] | None = None) -> dict:
    """Parse the command line into keyword arguments for `main`.

    Parameters
    ----------
    argv : sequence of str, optional
        Arguments to parse. Defaults to ``sys.argv[1:]``.

    Returns
    -------
    dict
        ``counts``, ``reps``, ``decks`` and ``out``, ready for ``main(**args)``.

    Raises
    ------
    SystemExit
        If an option is unknown or invalid, after argparse prints the error.
    """
    parser = argparse.ArgumentParser(
        prog="trnbench",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--counts",
        nargs="+",
        type=positive_int,
        default=COUNTS,
        metavar="N",
        help="simulations to run at once (default: %(default)s)",
    )
    parser.add_argument(
        "--reps",
        type=positive_int,
        default=REPS,
        metavar="N",
        help="times to repeat the sweep (default: %(default)s)",
    )
    parser.add_argument(
        "--decks", nargs="+", choices=deck_names(), help="decks to run (default: all)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        metavar="CSV",
        help="new CSV to write (default: results/<hostname>-<date>-<time>.csv)",
    )
    return vars(parser.parse_args(argv))


def cli() -> None:
    """Entry point for the trnbench command."""
    main(**parse_args())


if __name__ == "__main__":
    cli()
