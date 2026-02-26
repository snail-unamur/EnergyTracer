EnergyTracer
============

*A tool to measure the energy consumption of a MacOS computer per code iteration, comparing two variants of the same code.*

---

## Description

This small project is a tool to measure the energy consumption of a computer while executing a specific code. It supports two measurement backends and collects energy metrics (CPU, GPU, ANE, DRAM) for each individual iteration of the code. The results are then plotted using `matplotlib` to compare the energy consumption per iteration between two code variants — typically one implementing a code smell (or a specific pattern) and one without.

## Supported Profilers

| Profiler | Library | Method | Best for |
|---|---|---|---|
| `mac-silicon` | `zeus_apple_silicon` | Reads Apple Silicon **hardware power counters** directly (IOKit) | Accurate absolute energy values **on M-series Macs** |
| `carbon` | `codecarbon` | **Software model** — estimates power from CPU TDP, utilization, and time | CO₂ emission estimates; better suited **for x86** with Intel RAPL |

> **Note on measurement differences:** The two backends will report different absolute values for the same workload (e.g. Zeus may report ~600 mJ where CodeCarbon reports ~200 mJ). This is expected because they use fundamentally different measurement methods. However, the **ratio** between two code variants remains consistent across backends, so both are valid for **relative** comparison.

## Usage

This project is designed to be easy to use. To perform this, `uv` is used to manage the Python environment and dependencies. Once `uv` is installed on your system, you can follow these steps:

```shell
# Install dependencies
uv sync

# Run the energy tracer
uv run src/main.py
```

This will execute the `main.py` script, which will measure the energy consumption of the default code variants and plot the results. To customize the code variants and metrics, you can use command-line arguments as follows:

| Flag | Description | Default |
|---|---|---|
| `-h`, `--help` | Show the help message and exit | — |
| `-p`, `--profiler` | Energy profiler to use: `carbon` or `mac-silicon` | `carbon` |
| `-n`, `--iter` | Number of iterations for the code under measurement | `1000` |
| `-f1`, `--src-file-1` | Path to the source file **with** the code smell | `src/python/file_with_code_smell.py` |
| `-f2`, `--src-file-2` | Path to the source file **without** the code smell | `src/python/file_without_code_smell.py` |

### Example

```shell
# Compare two files for 500 iterations using the Zeus Apple Silicon profiler
uv run src/main.py -p mac-silicon -n 500 -f1 src/python/file_with_code_smell.py -f2 src/python/file_without_code_smell.py
```

As you can specify the source files, you can easily compare the energy consumption of different code variants, allowing you to identify which one is more energy-efficient. By default, the tool will compare a code located in `src/python/file_with_code_smell.py` with another code located in `src/python/file_without_code_smell.py`, but you can change these paths to compare any two Python scripts you want.

The generated plots are saved in the `output` directory.

## Project Structure

```
src/
├── main.py                          # Entry point & CLI argument parsing
├── measure/
│   ├── abstractEnergyProfiler.py    # Abstract base class for profilers
│   ├── macEnergyProfiler.py         # Zeus Apple Silicon backend
│   └── carbonEnergyProfiler.py      # CodeCarbon backend (OfflineEmissionsTracker)
├── plot/
│   ├── generate_plot.py             # Comparison plot generation
│   └── utilities/                   # Metrics extraction & padding helpers
├── python/
│   ├── file_with_code_smell.py      # Default code variant A
│   └── file_without_code_smell.py   # Default code variant B
└── utilities/
    └── save_CSV.py                  # CSV export for measurement histories
```

## Author

Florian Stormacq - [GitHub](https://github.com/fstormacq)

## Acknowledgements

This project was developed as part of the Master 1 Computer Science program at the University of Namur, Belgium.