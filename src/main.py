import argparse

from measure.measure import EnergyProfiler
from plot.generate_plot import compare_histories

def main(args):
    print("Starting energy profiler")
    print("------------------------")
    print(f"Number of iterations: {args.iterations}")
    print(f"Source file with code smell: {args.src_file_1}")
    print(f"Source file without code smell: {args.src_file_2}\n")

    print("\tRunning code with the code smell")
    print("\t--------------------------------")

    code1 = open(args.src_file_1).read()
    monitor1 = EnergyProfiler()
    try:
        for i in range(args.iterations):
            monitor1.measure_once(f"iter_{i}", lambda: exec(code1))
        print("\tEnergy profiling for code with code smell completed.\n")
    except KeyboardInterrupt:
        print("\tEnergy profiling for code with code smell interrupted by user.\n")
    
    first_history = monitor1.history

    print("\n\tRunning code without the code smell")
    print("\t-------------------------------------")

    code2 = open(args.src_file_2).read()
    monitor2 = EnergyProfiler()
    try:
        for i in range(args.iterations):
            monitor2.measure_once(f"iter_{i}", lambda: exec(code2))
        print("\tEnergy profiling for code without code smell completed.\n")
    except KeyboardInterrupt:
        print("\tEnergy profiling for code without code smell interrupted by user.\n")
    
    second_history = monitor2.history

    print("Energy profiling completed.")

    compare_histories(first_history, second_history)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Energy Profiler for Apple Silicon")
    parser.add_argument("--iterations", type=int, default=100_000, help="Number of iterations for the code under measurement")
    parser.add_argument("--src-file-1", type=str, default="src/python/file_with_code_smell.py", help="Path to the source file with the code smell to measure")
    parser.add_argument("--src-file-2", type=str, default="src/python/file_without_code_smell.py", help="Path to the source file without the code smell to measure")

    args = parser.parse_args()

    main(args)