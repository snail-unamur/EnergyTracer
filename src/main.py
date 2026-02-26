import argparse, os

from measure.measure import EnergyProfiler

import pandas as pd
import matplotlib.pyplot as plt


def main(args):
    print("Starting energy profiler")
    print("------------------------")
    print(f"Measurement interval: {args.interval} seconds")
    print(f"Number of iterations: {args.iterations}")
    print(f"Source file with pattern: {args.src_file_1}")
    print(f"Source file without pattern: {args.src_file_2}\n")

    print("\tRunning code with the pattern")
    print("\t-----------------------------")

    try :
        monitor1 = EnergyProfiler()
        monitor1.start(interval=args.interval)

        for _ in range(args.iterations):
            exec(open(args.src_file_1).read())

        first_history = monitor1.stop()

        print("\tEnergy profiling for code with pattern completed.\n")
    except KeyboardInterrupt:
        print("\tEnergy profiling for code with pattern interrupted by user.\n")
        first_history = monitor1.stop()

    print("\tCollected energy metrics for code with pattern:")
    for entry in first_history:
        print(f"\t\t{entry}")

    print("\n\tRunning code without the pattern")
    print("\t-----------------------------")

    try :
        monitor2 = EnergyProfiler()
        monitor2.start(interval=args.interval)

        for _ in range(args.iterations):
            exec(open(args.src_file_2).read())

        second_history = monitor2.stop()
    except KeyboardInterrupt:
        print("\tEnergy profiling for code without pattern interrupted by user.\n")
        second_history = monitor2.stop()

    print("\tEnergy profiling for code without pattern completed.\n")
    print("\tCollected energy metrics for code without pattern:")
    for entry in second_history:
        print(f"\t\t{entry}")

    print("Energy profiling completed.")

    compare_histories(first_history, second_history)

def pad(lst, length):
    '''
    Pads a list with NaN values to ensure it has a specified length.

    Inputs
    -------
        lst: The original list to be padded.
        length: The desired length of the list after padding.

    Returns
    -------
        A new list that contains the original elements of lst followed by enough NaN values to reach
        the specified length.

    Author
    ------
        Claude Opus 4.6
    '''
    return lst + [float('nan')] * (length - len(lst))

def compare_histories(history1, history2):
    '''
    Creates pandas diagrams to compare the energy metrics collected from two different code executions.

    Inputs
    -------
        history1: list of dicts containing energy metrics for the first code execution (with pattern).
        history2: list of dicts containing energy metrics for the second code execution (without pattern).

    Notes
    -----
        Generates line plots for CPU, GPU, ANE, and DRAM energy consumption over time for both code versions, allowing for a visual comparison of their energy profiles.
    '''
    # Avoid including the last few measurements which may be affected by the profiler stopping process
    measurements_to_remove = 3
    history1 = history1[:-measurements_to_remove] if len(history1) > measurements_to_remove else history1
    history2 = history2[:-measurements_to_remove] if len(history2) > measurements_to_remove else history2

    cpu_metrics1, gpu_metrics1, ane_metrics1, dram_metrics1 = extract_metrics(history1)
    cpu_metrics2, gpu_metrics2, ane_metrics2, dram_metrics2 = extract_metrics(history2)

    # Pad shorter lists with NaN so all arrays have the same length
    max_len = max(len(history1), len(history2))

    time1 = [entry["t"] for entry in history1]
    time2 = [entry["t"] for entry in history2]

    if len(time1) >= len(time2):
        time_axis = pad(time1, max_len) 
    else:
        time_axis = pad(time2, max_len)

    # Create a DataFrame for plotting
    df = pd.DataFrame({
        "Time": time_axis,
        "CPU with pattern": pad(cpu_metrics1, max_len),
        "CPU without pattern": pad(cpu_metrics2, max_len),

        "GPU with pattern": pad(gpu_metrics1, max_len),
        "GPU without pattern": pad(gpu_metrics2, max_len),

        "ANE with pattern": pad(ane_metrics1, max_len),
        "ANE without pattern": pad(ane_metrics2, max_len),

        "DRAM with pattern": pad(dram_metrics1, max_len),
        "DRAM without pattern": pad(dram_metrics2, max_len),
    })

    # Create output directory if it doesn't exist
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    # Plotting
    plot_all_metrics(df, os.path.join(output_dir, "all_energy_comparison.png"))
    plot_specific_metrics(df, "cpu", os.path.join(output_dir, "cpu_energy_comparison.png"))
    plot_specific_metrics(df, "gpu", os.path.join(output_dir, "gpu_energy_comparison.png"))
    plot_specific_metrics(df, "ane", os.path.join(output_dir, "ane_energy_comparison.png"))
    plot_specific_metrics(df, "dram", os.path.join(output_dir, "dram_energy_comparison.png"))

    
def plot_all_metrics(df: pd.DataFrame, filename: str):
    plt.figure(figsize=(10, 6))
    plt.plot(df["Time"], df["CPU with pattern"], label="CPU with pattern")
    plt.plot(df["Time"], df["CPU without pattern"], label="CPU without pattern")

    plt.plot(df["Time"], df["GPU with pattern"], label="GPU with pattern")
    plt.plot(df["Time"], df["GPU without pattern"], label="GPU without pattern")

    plt.plot(df["Time"], df["ANE with pattern"], label="ANE with pattern")
    plt.plot(df["Time"], df["ANE without pattern"], label="ANE without pattern")

    plt.plot(df["Time"], df["DRAM with pattern"], label="DRAM with pattern")
    plt.plot(df["Time"], df["DRAM without pattern"], label="DRAM without pattern")

    plt.xlabel("Time (s)")
    plt.ylabel("Energy (mJ)")
    plt.title("Energy Consumption Comparison")
    plt.grid(True)
    plt.savefig(filename, dpi=300)
    plt.close()

def plot_specific_metrics(df: pd.DataFrame, metric: str, filename: str):
    plt.figure(figsize=(10, 6))

    for variant in ["with pattern", "without pattern"]:
        col = f"{metric.upper()} {variant}"
        avg = df[col].mean()
        line, = plt.plot(df["Time"], df[col], label=f"{metric.upper()} {variant}")
        plt.axhline(y=avg, color=line.get_color(), linestyle="--", alpha=0.5, label=f"Avg {variant}: {avg:.3f} mJ / {args.interval} s")

    plt.xlabel("Time (s)")
    plt.ylabel("Energy (mJ)")
    plt.title(f"{metric.upper()} Energy Consumption Comparison")
    plt.legend(fontsize="small")
    plt.grid(True)
    plt.savefig(filename, dpi=300)
    plt.close()

def extract_metrics(history: dict) :
    cpu_metrics = [entry["cpu_mj"] for entry in history]
    gpu_metrics = [entry["gpu_mj"] for entry in history]
    ane_metrics = [entry["ane_mj"] for entry in history]
    dram_metrics = [entry["dram_mj"] for entry in history]

    return cpu_metrics, gpu_metrics, ane_metrics, dram_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Energy Profiler for Apple Silicon")
    parser.add_argument("--interval", type=float, default=0.5, help="Measurement interval in seconds")
    parser.add_argument("--iterations", type=int, default=100_000, help="Number of iterations for the code under measurement")
    parser.add_argument("--src-file-1", type=str, default="src/python/file_with_pattern.py", help="Path to the source file with the pattern to measure")
    parser.add_argument("--src-file-2", type=str, default="src/python/file_without_pattern.py", help="Path to the source file without the pattern to measure")

    args = parser.parse_args()

    main(args)