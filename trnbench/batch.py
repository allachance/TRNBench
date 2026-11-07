"""Run and measure one batch of simulations."""

import contextlib
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from trnrun import LogSeverity, Simulation, SimulationManager

from trnbench.settings import DECK_SETTINGS, TIMEOUT_S


def failure_reason(sim: Simulation) -> str | None:
    """Say why a simulation failed, or None if it succeeded."""
    if sim.succeeded and not sim.fatals:
        return None
    fatal = next((e.message for e in sim.logs if e.severity == LogSeverity.FATAL), None)
    return fatal or sim.error or sim.status_message or "simulation did not finish"


def copy_decks(decks: list[Path], tmp: str) -> list[str]:
    """Copy each deck into its own numbered folder."""
    copies = []
    for i, deck in enumerate(decks):
        folder = Path(tmp, f"{i:03}")
        folder.mkdir()
        copies.append(shutil.copy(deck, folder))
    return copies


def run_sims(decks: list[Path]) -> list[Simulation]:
    """Run the decks all at once, one worker each, in temporary folders.

    Parameters
    ----------
    decks : list of Path
        Deck files to run. The same deck may appear more than once; each entry
        gets its own copy and worker. Each stem must be a key of `DECK_SETTINGS`.

    Returns
    -------
    list of Simulation
        One simulation per deck, in the same order. Simulations still running
        after `TIMEOUT_S` are returned unfinished rather than raising.

    Raises
    ------
    trnrun.TrnrunError
        If trnrun cannot start or manage the simulations.
    """
    with TemporaryDirectory(prefix="trnbench_", ignore_cleanup_errors=True) as tmp:
        copies = copy_decks(decks, tmp)
        with SimulationManager(workers=len(decks), display=False, poll_interval=0.25) as manager:
            sims = [manager.add(copy, DECK_SETTINGS[deck.stem]) for deck, copy in zip(decks, copies, strict=True)]
            # Unfinished simulations are reported by failure_reason.
            with contextlib.suppress(TimeoutError):
                manager.wait(timeout=TIMEOUT_S)
    return sims


def warmup(decks: list[Path]) -> list[str]:
    """Run each deck once, all at once, so the first measured batch doesn't start cold, and return any failures."""
    return [f"{deck.stem}: {reason}" for deck, sim in zip(decks, run_sims(decks), strict=True) if (reason := failure_reason(sim))]


def run_batch(deck: Path, n: int) -> dict:
    """Run n copies of a deck all at once and return the measurements for one CSV row.

    Parameters
    ----------
    deck : Path
        Deck file to run.
    n : int
        Number of copies to run at the same time.

    Returns
    -------
    dict
        Same as `measure`: ``elapsed_s`` or ``error``.
    """
    return measure(run_sims([deck] * n))


def measure(sims: list[Simulation]) -> dict:
    """Turn a finished batch into the measurements for one CSV row.

    Elapsed time runs from the first submission to the last finish, so it
    covers the whole batch rather than any single simulation.

    Parameters
    ----------
    sims : list of Simulation
        The batch, as returned by `run_sims`.

    Returns
    -------
    dict
        ``{"elapsed_s": float}`` if every simulation
        succeeded, otherwise ``{"error": str}`` with the failure count and the
        first failure reason.
    """
    n = len(sims)
    errors = [reason for sim in sims if (reason := failure_reason(sim))]
    if errors:
        return {"error": f"{len(errors)}/{n} failed: {errors[0]}"}

    last_finish = max(sim.finished_at for sim in sims if sim.finished_at)
    first_submit = min(sim.submitted_at for sim in sims if sim.submitted_at)
    return {"elapsed_s": round((last_finish - first_submit).total_seconds(), 3)}
