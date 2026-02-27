import argparse, os, random

from measure.carbonEnergyProfiler import EnergyProfiler as carbonEnergyProfiler
from measure.macEnergyProfiler import EnergyProfiler as macEnergyProfiler

from utilities.save_CSV import save_history
from plot.generate_plot import compare_histories

# Labels
LABEL_WITH_SMELL    = "with the code smell"
LABEL_WITHOUT_SMELL = "without the code smell"

# Output filenames
CSV_WITH_SMELL    = "history_with_smell.csv"
CSV_WITHOUT_SMELL = "history_without_smell.csv"

# Default argument values
DEFAULT_PROFILER    = "carbon"
DEFAULT_ITERATIONS  = 1_000
DEFAULT_SRC_FILE_1  = "src/python/file_with_code_smell.py"
DEFAULT_SRC_FILE_2  = "src/python/file_without_code_smell.py"
DEFAULT_OUTPUT_DIR  = "output"

def run_profiling(energy_profiler_cls, src_file, label, verbose=False):
    '''Run energy profiling on a source file and return the measurement history.'''
    if verbose:
        print(f"Running code {label}")
        print("-" * (len(f"Running code {label}")))

    code = open(src_file).read()
    monitor = energy_profiler_cls(verbose=verbose)
    try:
        for i in range(args.iter):
            monitor.measure_once(f"iter_{i}", lambda: exec(code))
        if verbose:
            print(f"Energy profiling for code {label} completed.")
    except KeyboardInterrupt:
        if verbose:
            print(f"Energy profiling for code {label} interrupted by user.")

    monitor.finalize()
    return monitor.history

def main(args, energy_profiler_cls):
    if args.verbose:
        msg = f"Starting energy profiler"
        print(msg)
        print("-" * len(msg))
        print(f"Energy profiler: {args.profiler}")
        print(f"Number of iterations: {args.iter}")
        print(f"Source file with code smell: {args.src_file_1}")
        print(f"Source file without code smell: {args.src_file_2}\n")

    runs = [
        (args.src_file_1, LABEL_WITH_SMELL),
        (args.src_file_2, LABEL_WITHOUT_SMELL),
    ]

    swapped = False
    if args.shuffle:
        if args.verbose:
            print("Shuffling the order of code execution to mitigate temporal effects.")
        if random.random() < 0.5:
            runs.reverse()
            swapped = True
            if args.verbose:
                print("Order shuffled: first measuring code without code smell.")
        else:
            if args.verbose:
                print("Order shuffled: first measuring code with code smell.")

    first_result = run_profiling(energy_profiler_cls, runs[0][0], runs[0][1], verbose=args.verbose)

    if args.verbose:
        print()

    second_result = run_profiling(energy_profiler_cls, runs[1][0], runs[1][1], verbose=args.verbose)

    if args.verbose:
        print("Energy profiling completed.")

    if swapped:
        history_with_smell = second_result
        history_without_smell = first_result
    else:
        history_with_smell = first_result
        history_without_smell = second_result

    output_directory = os.path.join("output", args.profiler, args.output_dir)

    save_history(history_with_smell, CSV_WITH_SMELL, directory=output_directory)
    save_history(history_without_smell, CSV_WITHOUT_SMELL, directory=output_directory)

    compare_histories(history_with_smell, history_without_smell, profiler=args.profiler, directory=output_directory)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Energy Profiler for Apple Silicon")
    parser.add_argument("-p", "--profiler", type=str, choices=["mac-silicon", "carbon"], default=DEFAULT_PROFILER, help="Energy profiler to use: 'carbon' for CodeCarbon, 'mac-silicon' for zeus_apple_silicon. Default is 'carbon'.")
    parser.add_argument("-n", "--iter", type=int, default=DEFAULT_ITERATIONS, help="Number of iterations for the code under measurement. Default is 1000.")
    parser.add_argument("-f1", "--src-file-1", type=str, default=DEFAULT_SRC_FILE_1, help="Path to the source file with the code smell to measure. Default is 'src/python/file_with_code_smell.py'.")
    parser.add_argument("-f2", "--src-file-2", type=str, default=DEFAULT_SRC_FILE_2, help="Path to the source file without the code smell to measure. Default is 'src/python/file_without_code_smell.py'.")
    parser.add_argument("-o", "--output-dir", type=str, default=DEFAULT_OUTPUT_DIR, help="Path to the output directory. Default is 'output'.")
    parser.add_argument("--shuffle", action="store_true", help="Shuffle the order of code execution (with and without code smell) to mitigate temporal effects.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output during profiling.")

    args = parser.parse_args()

    energy_profiler_cls = macEnergyProfiler if args.profiler == "mac-silicon" else carbonEnergyProfiler
    
    main(args, energy_profiler_cls)