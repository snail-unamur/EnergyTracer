macEnergyTracer
===============

*A tool to trace the energy consumption of a MacOS computer over time, while executing a specific code.*

---

## Description

This small project is a tool to trace the energy consumption of a MacOS computer over time, while executing a specific code. It uses the `zeus_apple_silicon` library to measure multiple energy metrics. The results are then plotted using `matplotlib` to visualize the energy consumption over time, comparing different variants of the code.

## Usage

This project is designed to be easy to use. To perform this, `uv` is used to manage the Python environment and dependencies. Once `uv` is installed on your system, you can follow these steps:

```shell
# Install dependencies
uv sync

# Run the energy tracer
uv run src/main.py
```

This will execute the `main.py` script, which will trace the energy consumption of the default code variant and plot the results. To customize the code variants and metrics, you can use command-line arguments as follows:

1. `--help` or `-h`: Show the help message and exit.
2. `--interval INTERVAL`: Set the measurement interval in seconds (default is 0.5 second).
3. `--iterations ITERATIONS`: Set the number of iterations for the code under measurement (default is 100_000).
4. `--src-file-1 SRC_FILE_1`: Path to the source file with the pattern to measure (default is `src/python/file_with_pattern.py`).
5. `--src-file-2 SRC_FILE_2`: Path to the source file without the pattern to measure (default is `src/python/file_without_pattern.py`).

> Further improvments could include other measurement libraries, with other metrics.

As you can specify the source files, you can easily compare the energy consumption of different code variants, allowing you to identify which one is more energy-efficient. By default, the tool will compare a code located in `src/python/file_with_pattern.py` with another code located in `src/python/file_without_pattern.py`, but you can change these paths to compare any two Python scripts you want.

The generated plot are saved in the `output` directory.

## Author

Florian Stormacq - [GitHub](https://github.com/fstormacq)

## Aknowledgements

This project was developed as part of the Master 1 Computer Science program at the University of Namur, Belgium.