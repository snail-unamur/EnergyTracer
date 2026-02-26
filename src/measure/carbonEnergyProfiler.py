from codecarbon import OfflineEmissionsTracker
from measure.abstractEnergyProfiler import AbstractEnergyProfiler

KWH_TO_MJ = 3_600_000_000 # 1 kWh = 3.6 MJ = 3.6e9 mJ

class EnergyProfiler(AbstractEnergyProfiler):
    '''
    Energy Profiler using the CodeCarbon library.

    Each call to measure_once wraps a single code execution in a measurement window,
    collecting energy metrics per iteration and storing them in a history list.

    The tracker is instantiated once and reused across iterations to avoid 
    per-iteration overhead.
    '''

    def __init__(self):
        self.history = []

        self._tracker = OfflineEmissionsTracker(
            project_name="energy_profiling",
            country_iso_code="BEL",
            save_to_file=False,
            log_level="error",
        )
        
        # Track cumulative energy so we can compute per-iteration deltas
        self._prev_cpu_kwh = 0.0
        self._prev_gpu_kwh = 0.0
        self._prev_ram_kwh = 0.0
        self._prev_emissions = 0.0

    def measure_once(self, label: str, fn) -> dict:
        '''
        Measures energy consumed during a single execution of fn.

        Inputs
        ------
            label: A unique string label for the measurement window.
            fn: A callable to execute and measure.

        Returns
        -------
            A dict with keys: i, cpu_mj, gpu_mj, ane_mj, dram_mj.
        
        Note
        ----
        ane_mj holds CO2 equivalent emissions in grams (g CO2eq),
        as CodeCarbon has no Apple Neural Engine equivalent.
        '''
        self._tracker.start()
        fn()
        self._tracker.stop()

        data = self._tracker.final_emissions_data

        # Compute per-iteration deltas from cumulative values
        cpu_kwh = (data.cpu_energy or 0.0)
        gpu_kwh = (data.gpu_energy or 0.0)
        ram_kwh = (data.ram_energy or 0.0)
        emissions = (data.emissions or 0.0)

        entry = {
            "i": len(self.history),
            "cpu_mj": (cpu_kwh - self._prev_cpu_kwh) * KWH_TO_MJ,
            "gpu_mj": (gpu_kwh - self._prev_gpu_kwh) * KWH_TO_MJ,
            "ane_mj": (emissions - self._prev_emissions) * 1_000,
            "dram_mj": (ram_kwh - self._prev_ram_kwh) * KWH_TO_MJ,
        }

        self._prev_cpu_kwh = cpu_kwh
        self._prev_gpu_kwh = gpu_kwh
        self._prev_ram_kwh = ram_kwh
        self._prev_emissions = emissions

        self.history.append(entry)
        return entry
