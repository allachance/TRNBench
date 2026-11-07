# TRNBench

Compares how fast different computers run TRNSYS. It runs four decks, each measuring one thing:

- `fast`: TRNSYS startup
- `normal`: typical simulation
- `graph`: impact of online plots
- `io`: disk write speed

Each deck runs in batches of 1, 2, 4, 8, 16, 32 and 64 simulations. It repeats the whole sweep 3 times and saves the timings to a CSV.

## Results

Average time in seconds for a whole batch to finish, for each batch size. Lower is better.

### fast

| CPU | Cores | Threads |   1 |   2 |   4 |   8 |  16 |  32 |  64 |
| --- | ----: | ------: | --: | --: | --: | --: | --: | --: | --: |
|     |       |         |     |     |     |     |     |     |     |

### normal

| CPU | Cores | Threads |   1 |   2 |   4 |   8 |  16 |  32 |  64 |
| --- | ----: | ------: | --: | --: | --: | --: | --: | --: | --: |
|     |       |         |     |     |     |     |     |     |     |

### graph

| CPU | Cores | Threads |   1 |   2 |   4 |   8 |  16 |  32 |  64 |
| --- | ----: | ------: | --: | --: | --: | --: | --: | --: | --: |
|     |       |         |     |     |     |     |     |     |     |

### io

| CPU | Cores | Threads |   1 |   2 |   4 |   8 |  16 |  32 |  64 |
| --- | ----: | ------: | --: | --: | --: | --: | --: | --: | --: |
|     |       |         |     |     |     |     |     |     |     |

## Requirements

- Windows x64
- TRNSYS 18, installed in `C:\TRNSYS18` (`normal` reads its weather file from there)
- [type3830](https://github.com/NRCan/TRNRun/tree/main/components/type3830)

## Run it

```powershell
git clone https://github.com/allachance/TRNBench.git
cd TRNBench
uv run trnbench
```

### Option

| Option     | Default                                | Meaning                                  |
| ---------- | -------------------------------------- | ---------------------------------------- |
| `--counts` | `1 2 4 8 16 32 64`                     | Batch sizes to run                       |
| `--reps`   | `3`                                    | Number of times to repeat the sweep      |
| `--decks`  | all                                    | Deck names, without `.dck`               |
| `--out`    | `results/<hostname>-<date>-<time>.csv` | New CSV to write; must not already exist |
