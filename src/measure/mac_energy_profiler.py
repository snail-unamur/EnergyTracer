import time

from zeus_apple_silicon import AppleEnergyMonitor

from .abstract_energy_profiler import AbstractEnergyProfiler


class EnergyProfiler(AbstractEnergyProfiler):
    """
    Energy Profiler for Apple Silicon, using the AppleEnergyMonitor from the zeus_apple_silicon library.

    Each call to measure_once wraps a single code execution in a measurement window,
    collecting energy metrics per iteration and storing them in a history list.
    """

    def __init__(self, verbose=False):
        self.monitor = AppleEnergyMonitor()
        self.history = []
        self._durations = []
        self._started = False
        self.verbose = verbose

    def measure_once(self, label: str, fn) -> dict:
        """
        Executes fn and records its wall-clock duration.
        Energy is computed later when finalize() is called to avoid overhead.
        """
        if not self._started:
            self.monitor.begin_window("total_run")
            self._started = True

        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()

        self._durations.append(t1 - t0)
        return {}

    def finalize(self):
        """
        Stops the monitor and distributes total energy across iterations
        proportionally to each iteration's wall-clock duration.
        """
        if self._started:
            metrics = self.monitor.end_window("total_run")
            self._started = False

            total_cpu_mj = metrics.cpu_total_mj or 0.0
            total_gpu_mj = metrics.gpu_mj or 0.0
            total_ane_mj = metrics.ane_mj or 0.0
            total_dram_mj = metrics.dram_mj or 0.0

            total_time = sum(self._durations)
            self.history = []

            for i, dt in enumerate(self._durations):
                ratio = (
                    dt / total_time if total_time > 0 else 1.0 / len(self._durations)
                )
                self.history.append(
                    {
                        "i": i,
                        "cpu_mj": total_cpu_mj * ratio,
                        "gpu_mj": total_gpu_mj * ratio,
                        "ane_mj": total_ane_mj * ratio,
                        "dram_mj": total_dram_mj * ratio,
                        "time_s": dt,
                    }
                )
