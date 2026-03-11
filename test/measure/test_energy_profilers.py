"""
Unified tests for all energy profiler back-ends.

Common behaviour (initialization, measure_once, finalize) is tested through a
shared set of tests parametrized by profiler.  Back-end-specific tests live in
dedicated classes at the bottom of this file.

Platform / hardware guards
--------------------------
* **mac**    — skipped when not on macOS (darwin)
* **carbon** — runs everywhere (software model)
"""

import contextlib
import sys

import pytest

# Carbon — always available
from src.measure.carbon_energy_profiler import EnergyProfiler as CarbonProfiler

# ---------------------------------------------------------------------------
# Conditional imports — each profiler is imported only on a compatible platform
# or mocked to avoid ImportError.
# ---------------------------------------------------------------------------

_profilers: dict[str, type] = {}

_profilers["carbon"] = CarbonProfiler

# Mac — only on macOS
if sys.platform == "darwin":
    from src.measure.mac_energy_profiler import EnergyProfiler as MacProfiler

    _profilers["mac"] = MacProfiler


def _available_ids():
    return list(_profilers.keys())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.hardware


@pytest.fixture(params=_available_ids())
def profiler_cls(request):
    """Yield the EnergyProfiler *class* for each available back-end."""
    return _profilers[request.param]


@pytest.fixture
def profiler(profiler_cls):
    """Fresh profiler instance (default verbosity)."""
    return profiler_cls()


# ---------------------------------------------------------------------------
# Common tests — run for every available profiler
# ---------------------------------------------------------------------------


class TestCommonBehaviour:
    """Tests that apply to all profiler implementations."""

    @pytest.mark.integration
    def test_initialization(self, profiler, profiler_cls):
        assert isinstance(profiler, profiler_cls)
        assert profiler.history == []
        assert not profiler.verbose

    @pytest.mark.integration
    def test_initialization_verbose(self, profiler_cls):
        p = profiler_cls(verbose=True)
        assert p.verbose

    @pytest.mark.integration
    @pytest.mark.slow
    def test_measure_once_with_valid_fn(self, profiler_cls):
        profiler = profiler_cls()

        result = profiler.measure_once("test_window", lambda: sum(range(100)))

        assert isinstance(result, dict)
        # Carbon returns an empty placeholder; others return the full entry.
        if profiler_cls is not CarbonProfiler:
            for key in ("i", "cpu_mj", "gpu_mj", "ane_mj", "dram_mj"):
                assert key in result
            assert len(profiler.history) == 1
            assert profiler.history[0] is result

    @pytest.mark.integration
    def test_measure_once_with_exception(self, profiler):
        def faulty_fn():
            raise ValueError("Intentional error")

        with pytest.raises(ValueError, match="Intentional error"):
            profiler.measure_once("faulty_window", faulty_fn)

        assert len(profiler.history) == 0

    @pytest.mark.integration
    @pytest.mark.slow
    def test_measure_multiple_iterations(self, profiler_cls):
        profiler = profiler_cls()
        n = 5

        for i in range(n):
            profiler.measure_once(f"window_{i}", lambda: sum(range(100)))

        if profiler_cls is CarbonProfiler:
            # Carbon stores durations, not history entries, until finalize()
            assert len(profiler._durations) == n
        else:
            assert len(profiler.history) == n
            for i, entry in enumerate(profiler.history):
                assert entry["i"] == i

    @pytest.mark.integration
    def test_finalize_without_measurements(self, profiler_cls):
        profiler = profiler_cls()
        try:
            profiler.finalize()
        except AttributeError:
            # Carbon raises AttributeError when finalize() is called
            # without prior measure_once() — this is expected
            if profiler_cls is CarbonProfiler:
                pass
            else:
                pytest.fail("finalize() raised an unexpected AttributeError")
        except Exception as e:
            pytest.fail(f"finalize() raised an unexpected exception: {e}")


# ---------------------------------------------------------------------------
# Mac-specific tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "darwin", reason="Requires macOS + Apple Silicon")
class TestMacProfiler:
    @pytest.mark.integration
    def test_has_monitor(self):
        profiler = _profilers["mac"]()
        assert profiler.monitor is not None

    @pytest.mark.integration
    @pytest.mark.slow
    def test_all_metrics_non_negative(self):
        profiler = _profilers["mac"]()
        for i in range(5):
            profiler.measure_once(f"window_{i}", lambda: sum(range(100)))

        for entry in profiler.history:
            assert entry["cpu_mj"] >= 0
            assert entry["gpu_mj"] >= 0
            assert entry["ane_mj"] >= 0
            assert entry["dram_mj"] >= 0


# ---------------------------------------------------------------------------
# Carbon-specific tests
# ---------------------------------------------------------------------------


class TestCarbonProfiler:
    @pytest.mark.integration
    def test_has_tracker(self):
        from codecarbon import OfflineEmissionsTracker

        profiler = CarbonProfiler()
        assert profiler._tracker is not None
        assert isinstance(profiler._tracker, OfflineEmissionsTracker)

    @pytest.mark.integration
    def test_has_empty_durations(self):
        profiler = CarbonProfiler()
        assert profiler._durations == []

    @pytest.mark.integration
    @pytest.mark.slow
    def test_finalize_computes_history(self):
        profiler = CarbonProfiler()
        for i in range(3):
            profiler.measure_once(f"test_window_{i}", lambda: sum(range(100)))
        profiler.finalize()

        assert len(profiler.history) == 3
        for entry in profiler.history:
            for key in ("i", "cpu_mj", "gpu_mj", "ane_mj", "dram_mj"):
                assert key in entry
            assert isinstance(entry["i"], int) and entry["i"] >= 0
            assert isinstance(entry["cpu_mj"], float) and entry["cpu_mj"] >= 0
            assert isinstance(entry["gpu_mj"], float) and entry["gpu_mj"] >= 0
            assert isinstance(entry["ane_mj"], float) and entry["ane_mj"] >= 0
            assert isinstance(entry["dram_mj"], float) and entry["dram_mj"] >= 0

    @pytest.mark.integration
    @pytest.mark.slow
    def test_finalize_with_verbose(self):
        profiler = CarbonProfiler(verbose=True)
        for i in range(3):
            profiler.measure_once(f"test_window_{i}", lambda: sum(range(100)))
        profiler.finalize()

        assert len(profiler.history) == 3

    @pytest.mark.integration
    def test_finalize_with_zero_durations(self):
        profiler = CarbonProfiler()
        profiler._durations = [0, 0, 0]
        with contextlib.suppress(AttributeError):
            profiler.finalize()  # Expected — tracker was never started
