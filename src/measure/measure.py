import time
import threading
from zeus_apple_silicon import AppleEnergyMonitor

class EnergyProfiler:
    '''
    Energy Profiler for Apple Silicon, using the AppleEnergyMonitor from the zeus_apple_silicon library. 
    
    It runs a measurement loop in a separate thread, collecting energy metrics at specified intervals and storing them in a history list. The stop method signals the loop to end and returns the collected metrics.
    '''

    def __init__(self):
        self.monitor = AppleEnergyMonitor()
        self.history = []
        self.stop_event = threading.Event()

    def start(self, interval=0.5):
        self.thread = threading.Thread(target=self.measure_loop, args=(interval,))
        self.thread.start()

    def measure_loop(self, interval=0.5):
        i = 0
        while not self.stop_event.is_set():
            label = f"t_{i}"
            self.monitor.begin_window(label)
            time.sleep(interval)
            metrics = self.monitor.end_window(label)
            self.history.append({
                "t": time.time(),
                "cpu_mj": metrics.cpu_total_mj,
                "gpu_mj": metrics.gpu_mj,
                "ane_mj": metrics.ane_mj,
                "dram_mj": metrics.dram_mj,
            })
            i += 1

    def stop(self) -> list[dict]:
        self.stop_event.set()
        if hasattr(self, 'thread'):
            self.thread.join()

        return self.history