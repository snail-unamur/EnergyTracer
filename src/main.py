import argparse

from measure.carbonEnergyProfiler import EnergyProfiler as carbonEnergyProfiler
from measure.macEnergyProfiler import EnergyProfiler as macEnergyProfiler

from utilities.save_CSV import save_history
from plot.generate_plot import compare_histories

def run_profiling(energy_profiler_cls, src_file, label):
    '''Run energy profiling on a source file and return the measurement history.'''
    print(f"Running code {label}")
    print("-" * (len(f"Running code {label}")))

    code = open(src_file).read()
    monitor = energy_profiler_cls()
    try:
        for i in range(args.iter):
            monitor.measure_once(f"iter_{i}", lambda: exec(code))
        print(f"Energy profiling for code {label} completed.")
    except KeyboardInterrupt:
        print(f"Energy profiling for code {label} interrupted by user.")

    monitor.finalize()
    return monitor.history

def main(args, energy_profiler_cls):
    msg = f"Starting energy profiler"
    print(msg)
    print("-" * len(msg))
    print(f"Energy profiler: {args.profiler}")
    print(f"Number of iterations: {args.iter}")
    print(f"Source file with code smell: {args.src_file_1}")
    print(f"Source file without code smell: {args.src_file_2}\n")

    first_history = run_profiling(energy_profiler_cls, args.src_file_1, "with the code smell")
    print()
    second_history = run_profiling(energy_profiler_cls, args.src_file_2, "without the code smell")

    print("Energy profiling completed.")

    save_history(first_history, "history_with_smell.csv")
    save_history(second_history, "history_without_smell.csv")

    compare_histories(first_history, second_history, profiler=args.profiler)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Energy Profiler for Apple Silicon")
    parser.add_argument("-p", "--profiler", type=str, choices=["mac-silicon", "carbon"], default="carbon", help="Energy profiler to use: 'carbon' for CodeCarbon, 'mac-silicon' for zeus_apple_silicon. Default is 'carbon'.")
    parser.add_argument("-n", "--iter", type=int, default=1_000, help="Number of iterations for the code under measurement. Default is 1000.")
    parser.add_argument("-f1", "--src-file-1", type=str, default="src/python/file_with_code_smell.py", help="Path to the source file with the code smell to measure. Default is 'src/python/file_with_code_smell.py'.")
    parser.add_argument("-f2", "--src-file-2", type=str, default="src/python/file_without_code_smell.py", help="Path to the source file without the code smell to measure. Default is 'src/python/file_without_code_smell.py'.")

    args = parser.parse_args()

    energy_profiler_cls = macEnergyProfiler if args.profiler == "mac-silicon" else carbonEnergyProfiler
    
    main(args, energy_profiler_cls)