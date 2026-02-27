EnergyTracer
============

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

---

*Measure it all, from energy consumption to environmental impact*

## Description

Have you ever wondered how much energy your code consumes? How to optimize it for better energy efficiency? Or how it impacts the environment? EnergyTracer is here to help you answer these questions, and more! This tool allows you to measure the energy consumption of your code, compare different implementations, and even estimate the CO₂ emissions associated with running your code. Sounds great, right?

## Profilers

To enable accurate energy measurements, EnergyTracer supports various profilers that can be used to collect energy metrics. Here is a table summarizing the supported profilers:
| Profiler | Library | Method | Hardware | Precision | Best for |
|---|---|---|---|:---:|---|
| `mac-silicon` | `zeus_apple_silicon` | Reads Apple Silicon **hardware power counters** directly (IOKit) | **Apple M-series only** | ⭐⭐⭐ | Accurate absolute energy measurement on M-series Macs; fine-grained profiling of code blocks |
| `carbon` | `codecarbon` | **Software model**: estimates power from CPU TDP, utilization, and time | **Cross-platform** | ⭐⭐ | CO₂ emission reports; long-running workloads; multi-platform projects or mixed hardware |

> **Note on measurement differences:** The different profilers will report different values for the exact same workload. This is expected because they use fundamentally different measurement methods.
>
> **Further improvements:** It is not excluded that, in the future, support for additional profilers may be added. The modular design of EnergyTracer allows for easy integration of new measurement backends.

### Mac Silicon (Zeus)

The `mac-silicon` profiler reads energy data directly from Apple Silicon hardware counters via IOKit, Apple's private kernel framework. This gives sub-millisecond, per-component accuracy without requiring `sudo` or any background daemon.

The following metrics are collected over time:

- **CPU**: energy consumed by all CPU clusters (E-cores and P-cores)
- **GPU**: energy consumed by the integrated GPU
- **ANE**: energy consumed by the Apple Neural Engine
- **DRAM**: energy consumed by unified memory

All metrics are measured in millijoules (mJ).

### CodeCarbon

The `carbon` profiler uses a software estimation model: it samples CPU utilization and maps it against the processor's thermal design power (TDP) to estimate electricity consumption, then converts it to CO₂ equivalent using the carbon intensity of your region.

The following metrics are collected over time:

- **CPU**: estimated energy from CPU TDP and utilization
- **GPU**: estimated energy from GPU utilization (if supported)
- **DRAM**: estimated energy based on memory usage
- **gCO₂**: estimated CO₂ emissions based on energy consumption and regional carbon intensity. This measure replaces the `ANE` metric since CodeCarbon does not have access to the Apple Neural Engine's energy data.

All energy metrics are estimated in millijoules (mJ), and CO₂ emissions are estimated in milligrams of CO₂ equivalent (mgCO₂e).

## Usage

To use EnergyTracer, you need to have Python installed on your system. The project uses `uv` to manage the Python environment and dependencies. Once you have `uv` installed, you can follow these steps:

```shell
# Initialize the project (install dependencies)
./init.sh
```

It is as simple as that! The `init.sh` script will set up and install all the necessary dependencies in a dedicated virtual environment managed by `uv`. After running this command, you will be ready to run the tool and start measuring the energy consumption of your code.

To run the EnergyTracer, you can use the following command:

```shell
uv run src/main.py
```

This command will execute the `main.py` script, which will measure the energy consumption of the default code variants (located in `src/python/file_with_code_smell.py` and `src/python/file_without_code_smell.py`) and plot the results.

### CLI Arguments

For more control over the measurement process, you can use the following command-line arguments:

| Flag | Description | Default |
|---|---|---|
| `-h`, `--help` | Show the help message and exit | — |
| `-p`, `--profiler` | Energy profiler to use: `carbon` or `mac-silicon` | `carbon` |
| `-n`, `--iter` | Number of iterations for the code under measurement | `1000` |
| `-f1`, `--src-file-1` | Path to the source file **with** the code smell | `src/python/file_with_code_smell.py` |
| `-f2`, `--src-file-2` | Path to the source file **without** the code smell | `src/python/file_without_code_smell.py` |
| `-o`, `--output-dir` | Directory to save generated plots and CSV files | `output` |
| `--shuffle` | Randomize execution order of code variants to mitigate temporal effects | off |
| `-v`, `--verbose` | Enable verbose output during profiling | off |

Here is an example of how to use these arguments:

```shell
# Compare two files for 500 iterations using the Zeus Apple Silicon profiler, 
# with shuffling and verbose output
uv run src/main.py -p mac-silicon -n 500 --shuffle -v
```

All the generated data will be saved in the `output/{profiler}/{output_dir}` directory, where `{profiler}` is the name of the profiler used (e.g., `mac-silicon` or `carbon`) and `{output_dir}` is the value of the `--output-dir` argument (default is `output`).

### Outputs

EnergyTracer generates two main types of outputs:

1. **Plots**: For each energy metric (CPU, GPU, ANE/gCO₂, DRAM), a plot is generated comparing the two code variants across iterations. These plots are saved as PNG files in the output directory. In addition to the per-metric plots, an overall comparison plot is also generated, showing all metrics together for a comprehensive view of energy consumption differences.
2. **CSV Files**: The raw energy data collected during the measurements is saved in CSV format for further analysis. Each row corresponds to an iteration, and columns include the iteration index and energy values for each metric (CPU, GPU, ANE/CO₂, DRAM). This allows you to perform your own custom analysis or create additional visualizations as needed.

### Automated Measurement Script

To facilitate repeated measurements and comparisons, a shell script named `run_experiment.sh` is provided. This script automates what would be a complex manual process of running the measurements with multiple phases (e.g., warm-up, measurement, cooldown) and ensures that the correct parameters are used consistently across runs. You can run this script as follows:

```shell
./run_experiment.sh
```

The script performs the following steps:

1. **Warm-up phases**: It runs 10 iterations of all profilers to stabilize the system and mitigate any initial variability in measurements.
2. **Measurement phases**: It runs 30 iterations of measurements for each profiler, with 1000 iterations of the code under test in each measurement phase. 
3. **Cooldown periods**: Between measurement phases, it includes a cooldown period of a minute to allow the system to return to baseline conditions and minimize thermal effects on measurements.

To further reduce temporal bias, the execution order of code variants is randomized in each iteration using the `--shuffle` flag. The script also provides a terminal progress bar to indicate the current phase and iteration, giving you real-time feedback on the measurement process.

> **Important note on reproducibility**: The results of energy measurements can be affected by various factors such as background processes, thermal conditions, network activity, and more. To ensure that your measurements are as reproducible as possible, it is recommended to set up your system in a consistent state before running the measurements. For more details on how to achieve this, you can refer to this [guide](https://luiscruz.github.io/2021/10/10/scientific-guide.html) that provides best practices for setting up a good environment for reproducible measurements. 
> 
> Note that while the `run_experiment.sh` script runs, it is advisable to avoid using the system for any other tasks to minimize interference with the measurements.

## Author

Florian Stormacq - [GitHub](https://github.com/fstormacq)

## Acknowledgements

This project was developed as part of a Master degree in Computer Science at the University of Namur, Belgium.

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-nc-sa/4.0/).

© 2026 Florian Stormacq. You are free to use, share, and adapt this work for non-commercial purposes, as long as you give appropriate credit and distribute your contributions under the same license.
