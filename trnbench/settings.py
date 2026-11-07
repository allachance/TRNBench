"""What the benchmark runs: edit this one."""

from pathlib import Path

from trnrun import SimulationSettings

ROOT = Path(__file__).parents[1]
DECK_DIR = ROOT / "decks"
COUNTS = [1, 2, 4, 8, 16, 32, 64]
REPS = 3
TIMEOUT_S = 7200

DECK_SETTINGS = {
    "fast": SimulationSettings(keep_awake=True, poll_ms=10, watch_log=False, watch_tmp=False, severity="Fatal"),
    "graph": SimulationSettings(keep_awake=True, poll_ms=100, watch_log=False, watch_tmp=False, severity="Fatal"),
    "io": SimulationSettings(keep_awake=True, poll_ms=100, watch_log=False, watch_tmp=False, severity="Fatal"),
    "normal": SimulationSettings(keep_awake=True, poll_ms=100, watch_log=False, watch_tmp=False, severity="Fatal"),
}
