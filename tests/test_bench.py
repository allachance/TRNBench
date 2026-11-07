"""Needs no TRNSYS. Run with: uv run tests/test_bench.py"""

import contextlib
import io
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from trnrun import LogEvent, LogSeverity

from trnbench import batch, bench
from trnbench.batch import failure_reason, measure
from trnbench.report import print_readme_rows, read_rows, summarize
from trnbench.settings import DECK_SETTINGS


def row(n, elapsed=""):
    """Make a CSV row as read back from disk, with every value a string."""
    return {"deck": "fast", "n": str(n), "elapsed_s": str(elapsed)}


def sim(*, succeeded=True, fatals=0, logs=(), submitted_at=None, finished_at=None):
    """Make a fake Simulation with only the attributes trnbench reads."""
    return SimpleNamespace(
        succeeded=succeeded, fatals=fatals, logs=logs, error=None, status_message="", submitted_at=submitted_at, finished_at=finished_at
    )


def test_summarize_averages_good_repeats_from_csv_text():
    """A failed repeat is left out of the average."""
    [result] = summarize([row(4, 10.0), row(4, 20.0), row(4, 30.0), row(4)])
    assert result["avg_s"] == 20.0
    assert result["failed_reps"] == 1


def test_summarize_all_failed_has_no_average():
    """A group with no successful repeat reports None instead of crashing."""
    [result] = summarize([row(64)])
    assert result["avg_s"] is None


def test_readme_rows_have_a_cell_per_count():
    """Each deck gets one table row: average time per batch size, failed or blank where there is none."""
    machine = {"cpu": "CPU X", "cores": "4", "threads": "8"}
    rows = [{**row(1, 1.0), **machine}, {**row(1, 2.0), **machine}, {**row(2), **machine}]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        print_readme_rows(rows)
    assert out.getvalue() == "\n### fast\n\n| CPU X | 4 | 8 | 1.50 | failed |  |  |  |  |  |\n"
    with contextlib.redirect_stdout(out):
        print_readme_rows([])  # A run with nothing recorded prints nothing instead of crashing.


def test_summarize_sorts_n_as_a_number():
    """n=2 sorts before n=16 even though the CSV stores text."""
    assert [r["n"] for r in summarize([row(16, 1.0), row(2, 1.0)])] == [2, 16]


def test_failure_reason():
    """Success gives None; unfinished or fatal runs give a readable reason."""
    assert failure_reason(sim()) is None
    assert failure_reason(sim(succeeded=None)) == "simulation did not finish"  # Still running at the timeout.
    logs = [LogEvent(LogSeverity.NOTICE, 0.0, message="harmless"), LogEvent(LogSeverity.FATAL, 0.0, message="bad data file")]
    assert failure_reason(sim(succeeded=False, fatals=1, logs=logs)) == "bad data file"
    assert failure_reason(sim(fatals=1, logs=logs)) == "bad data file"  # A fatal fails it even if trnrun reports success.


def test_measure_times_from_first_submit_to_last_finish():
    """Elapsed time spans the whole batch, not one simulation."""
    start = datetime(2026, 1, 1)
    sims = [
        sim(submitted_at=start, finished_at=start + timedelta(seconds=10)),
        sim(submitted_at=start + timedelta(seconds=1), finished_at=start + timedelta(seconds=20)),
    ]
    assert measure(sims) == {"elapsed_s": 20.0}


def test_measure_reports_failures_instead_of_a_time():
    """One failed simulation turns the batch into an error."""
    assert measure([sim(), sim(succeeded=None)]) == {"error": "1/2 failed: simulation did not finish"}


def test_warmup_returns_only_the_failures():
    """Warmup lists failed decks by name and skips the ones that worked."""
    real = batch.run_sims
    batch.run_sims = lambda decks: [sim(), sim(succeeded=None)]
    try:
        assert batch.warmup([Path("a.dck"), Path("b.dck")]) == ["b: simulation did not finish"]
    finally:
        batch.run_sims = real


def run_bench():
    """Run the benchmark on fake batches where n=2 fails, and return the batches run, the warmups and the saved rows."""
    calls, warmups = [], []

    def fake_batch(deck, n):
        """Record the batch and fail it when n is 2."""
        calls.append((deck.stem, n))
        return {"error": "boom"} if n == 2 else {"elapsed_s": 1.0}

    def fake_warmup(decks):
        """Record the warmup and report no failures."""
        warmups.append(decks)
        return []

    real, real_warmup = bench.run_batch, bench.warmup
    bench.run_batch, bench.warmup = fake_batch, fake_warmup
    try:
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            out = Path(tmp) / "new" / "r.csv"
            bench.main(counts=[1, 2], reps=2, decks=["fast"], out=out)
            return calls, warmups, read_rows(out)
    finally:
        bench.run_batch, bench.warmup = real, real_warmup


def test_run_does_every_batch():
    """Every rep, deck and count runs once and is saved."""
    calls, _, rows = run_bench()
    assert calls == [("fast", 1), ("fast", 2)] * 2
    assert len(rows) == 4


def test_run_ignores_an_earlier_default_results_file():
    """A new run writes a new file and leaves older results untouched."""
    real_root, real_batch, real_warmup = bench.ROOT, bench.run_batch, bench.warmup
    with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
        bench.ROOT = Path(tmp)
        bench.run_batch = lambda deck, n: {"elapsed_s": 1.0}
        bench.warmup = lambda decks: []
        try:
            old = Path(tmp) / "results" / f"{bench.machine_info()['host']}-old.csv"
            old.parent.mkdir()
            old.write_text("old")
            bench.main(counts=[1], reps=1, decks=["fast"])
            assert old.read_text() == "old"
            [new] = set(old.parent.glob("*.csv")) - {old}
            assert len(read_rows(new)) == 1
        finally:
            bench.ROOT, bench.run_batch, bench.warmup = real_root, real_batch, real_warmup


def test_existing_out_is_refused_and_left_alone():
    """An explicit --out that already exists is refused, not overwritten."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "r.csv"
        out.write_text("old")
        try:
            bench.main(counts=[1], reps=1, decks=["fast"], out=out)
        except FileExistsError:
            assert out.read_text() == "old"
        else:
            raise AssertionError("ran over an existing results file")


def test_warmup_runs_once():
    """Warmup happens once per run, not once per repeat."""
    _, warmups, _ = run_bench()
    assert [[deck.stem for deck in decks] for decks in warmups] == [["fast"]]


def test_failed_batches_have_no_time():
    """Failed batches leave elapsed_s blank in the CSV."""
    _, _, rows = run_bench()
    assert all(r["elapsed_s"] == "" for r in rows if r["n"] == "2")


def test_deck_without_settings_stops_before_running():
    """A deck missing from DECK_SETTINGS stops the run up front."""
    try:
        bench.main(decks=["nope"])
    except ValueError as error:
        assert "nope" in str(error)
    else:
        raise AssertionError("accepted a deck with no settings")


def test_every_deck_has_settings():
    """Every deck in the decks folder has an entry in DECK_SETTINGS."""
    assert set(bench.deck_names()) <= DECK_SETTINGS.keys()


def test_cli_rejects_bad_options_instead_of_starting_a_run():
    """Typos and out-of-range values exit before any simulation starts."""
    for argv in (["--typo"], ["--reps", "0"], ["--counts", "-1"], ["--decks", "nope"]):
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                bench.parse_args(argv)
        except SystemExit:
            continue
        raise AssertionError(f"accepted {argv}")


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("ok")
