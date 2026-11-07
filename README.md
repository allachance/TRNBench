# TRNBench

Compares how fast different computers run TRNSYS. It runs four decks, each measuring one thing:

- `fast`: TRNSYS startup
- `normal`: typical simulation
- `graph`: impact of online plots
- `io`: disk write speed

Each deck runs in batches of 1, 2, 4, 8, 16, 32 and 64 simulations. It repeats the whole sweep 3 times and saves the timings to a CSV.

## Results

Average time in seconds for a whole batch to finish, for each batch size. Lower is better. C/T is cores/threads.

### fast

| CPU                 |  C/T |        1 |        2 |        4 |        8 |       16 |       32 |       64 |
| ------------------- | ---: | -------: | -------: | -------: | -------: | -------: | -------: | -------: |
| AMD Ryzen 7 9800X3D | 8/16 |   0.15 s |   0.21 s |   0.33 s |   0.59 s |   1.06 s |   2.00 s |   3.92 s |

### normal

| CPU                 |  C/T |        1 |        2 |        4 |        8 |       16 |       32 |       64 |
| ------------------- | ---: | -------: | -------: | -------: | -------: | -------: | -------: | -------: |
| AMD Ryzen 7 9800X3D | 8/16 |  15.15 s |  15.46 s |  15.75 s |  18.29 s |  30.31 s |  61.62 s | 120.58 s |

### graph

| CPU                 |  C/T |        1 |        2 |        4 |        8 |       16 |       32 |       64 |
| ------------------- | ---: | -------: | -------: | -------: | -------: | -------: | -------: | -------: |
| AMD Ryzen 7 9800X3D | 8/16 |   4.68 s |   4.97 s |  14.17 s |  28.69 s |  55.03 s | 146.82 s | 357.58 s |

### io

| CPU                 |  C/T |        1 |        2 |        4 |        8 |       16 |       32 |       64 |
| ------------------- | ---: | -------: | -------: | -------: | -------: | -------: | -------: | -------: |
| AMD Ryzen 7 9800X3D | 8/16 |  17.19 s |  17.39 s |  17.53 s |  20.38 s |  35.60 s |  72.06 s | 143.49 s |

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
