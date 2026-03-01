from codecarbon import OfflineEmissionsTracker
import pytest

from src.measure.carbon_energy_profiler import EnergyProfiler


@pytest.fixture
def profiler():
    return EnergyProfiler()


@pytest.fixture
def profiler_executed(profiler):
    def sample_fn():
        sum(range(100))

    iterations = 3
    for i in range(iterations):
        profiler.measure_once(f"test_window_{i}", sample_fn)
    profiler.finalize()
    return profiler


@pytest.fixture
def profiler_executed_with_verbose():
    profiler = EnergyProfiler(verbose=True)

    def sample_fn():
        sum(range(100))

    iterations = 3
    for i in range(iterations):
        profiler.measure_once(f"test_window_{i}", sample_fn)
    profiler.finalize()
    return profiler


@pytest.mark.integration
def test_initialization(profiler):
    assert isinstance(profiler, EnergyProfiler)
    assert profiler.history == []
    assert profiler._durations == []
    assert not profiler.verbose
    assert profiler._tracker is not None
    assert isinstance(profiler._tracker, OfflineEmissionsTracker)


@pytest.mark.integration
def test_initialisation_verbose():
    profiler = EnergyProfiler(verbose=True)
    assert profiler.verbose


@pytest.mark.integration
@pytest.mark.slow
def test_measure_once_with_valid_fn(profiler):
    def sample_fn():
        sum(range(100))

    result = profiler.measure_once("test_window", sample_fn)

    assert isinstance(result, dict)
    assert len(result) == 0  # measure_once returns empty dict as placeholder
    assert len(profiler._durations) == 1
    assert profiler._durations[0] > 0


@pytest.mark.integration
@pytest.mark.slow
def test_measure_once_with_exception(profiler):
    def faulty_fn():
        raise ValueError("Intentional error")

    try:
        profiler.measure_once("faulty_window", faulty_fn)
        pytest.fail("Expected ValueError was not raised")
    except ValueError as e:
        assert str(e) == "Intentional error"
        assert len(profiler.history) == 0
        assert len(profiler._durations) == 0


@pytest.mark.integration
@pytest.mark.slow
def test_measure_multiple_iterations(profiler):
    def sample_fn():
        sum(range(100))

    iterations = 5
    for _ in range(iterations):
        profiler.measure_once("test_window", sample_fn)

    assert len(profiler._durations) == iterations
    for duration in profiler._durations:
        assert duration > 0


@pytest.mark.integration
@pytest.mark.slow
def test_finalize_computes_history(profiler_executed):
    assert len(profiler_executed.history) == 3
    for entry in profiler_executed.history:
        assert "i" in entry
        assert "cpu_mj" in entry
        assert "gpu_mj" in entry
        assert "ane_mj" in entry
        assert "dram_mj" in entry
        assert isinstance(entry["i"], int) and entry["i"] >= 0
        assert isinstance(entry["cpu_mj"], float) and entry["cpu_mj"] >= 0
        assert isinstance(entry["gpu_mj"], float) and entry["gpu_mj"] >= 0
        assert isinstance(entry["ane_mj"], float) and entry["ane_mj"] >= 0
        assert isinstance(entry["dram_mj"], float) and entry["dram_mj"] >= 0


@pytest.mark.integration
@pytest.mark.slow
def test_finalize_with_verbose(profiler_executed_with_verbose):
    test_finalize_computes_history(profiler_executed_with_verbose)


@pytest.mark.integration
def test_finalize_without_measure(profiler):
    try:
        profiler.finalize()
    except Exception as e:
        assert isinstance(e, AttributeError), f"Expected AttributeError, got {type(e)}"


@pytest.mark.integration
def test_finalize_with_zero_durations(profiler):

    profiler._durations = [0, 0, 0]
    try:
        profiler.finalize()
        assert len(profiler.history) == 3
        for i, entry in profiler.history:
            assert entry["i"] == i
            assert entry["cpu_mj"] >= 0
            assert entry["gpu_mj"] >= 0
            assert entry["ane_mj"] >= 0
            assert entry["dram_mj"] >= 0
    except Exception as e:
        assert isinstance(e, AttributeError), f"Expected AttributeError, got {type(e)}"
