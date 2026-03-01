import pytest

from src.measure.mac_energy_profiler import EnergyProfiler


@pytest.fixture
def profiler():
    return EnergyProfiler()


@pytest.mark.integration
def test_initialization(profiler):
    assert isinstance(profiler, EnergyProfiler)
    assert profiler.monitor is not None
    assert profiler.history == []
    assert not profiler.verbose


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
    assert "i" in result
    assert "cpu_mj" in result
    assert "gpu_mj" in result
    assert "ane_mj" in result
    assert "dram_mj" in result
    assert len(profiler.history) == 1
    assert profiler.history[0] == result


@pytest.mark.integration
def test_measure_once_with_exception(profiler):
    def faulty_fn():
        raise ValueError("Intentional error")

    try:
        profiler.measure_once("faulty_window", faulty_fn)
        pytest.fail("Expected ValueError was not raised")
    except ValueError as e:
        assert str(e) == "Intentional error"
        assert len(profiler.history) == 0


@pytest.mark.integration
@pytest.mark.slow
def test_measure_multiple_iterations(profiler):
    def sample_fn():
        sum(range(100))

    for i in range(5):
        result = profiler.measure_once(f"window_{i}", sample_fn)
        assert result["i"] == i

    assert len(profiler.history) == 5
    for i in range(5):
        assert profiler.history[i]["i"] == i
        assert profiler.history[i]["cpu_mj"] >= 0
        assert profiler.history[i]["gpu_mj"] >= 0
        assert profiler.history[i]["ane_mj"] >= 0
        assert profiler.history[i]["dram_mj"] >= 0


@pytest.mark.integration
def test_finalize(profiler):
    try:
        profiler.finalize()
    except Exception as e:
        pytest.fail(f"finalize() raised an unexpected exception: {e}")
