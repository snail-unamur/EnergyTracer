import pytest

from src.utilities.parser import (
    DEFAULT_ITERATIONS,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PROFILER,
    DEFAULT_SRC_FILE_1,
    DEFAULT_SRC_FILE_2,
    parse_arguments,
)


@pytest.mark.unit
def test_parse_arguments_defaults(monkeypatch):
    monkeypatch.setattr("sys.argv", ["ET"])
    args = parse_arguments()
    assert args.profiler == DEFAULT_PROFILER
    assert args.iter == DEFAULT_ITERATIONS
    assert args.src_file_1 == DEFAULT_SRC_FILE_1
    assert args.src_file_2 == DEFAULT_SRC_FILE_2
    assert args.output_dir == DEFAULT_OUTPUT_DIR
    assert not args.shuffle
    assert not args.verbose


@pytest.mark.unit
def test_parse_profiler_argument(monkeypatch):
    monkeypatch.setattr("sys.argv", ["ET", "-p", "mac-silicon"])
    assert parse_arguments().profiler == "mac-silicon"

    monkeypatch.setattr("sys.argv", ["ET", "-p", "carbon"])
    assert parse_arguments().profiler == "carbon"


@pytest.mark.unit
def test_parse_iterations_argument(monkeypatch):
    iteration = 500
    monkeypatch.setattr("sys.argv", ["ET", "-n", str(iteration)])
    assert parse_arguments().iter == iteration


@pytest.mark.unit
def test_parse_src_file_arguments(monkeypatch):
    src_file_1 = "custom_path_with_smell.py"
    src_file_2 = "custom_path_without_smell.py"
    monkeypatch.setattr("sys.argv", ["ET", "-f1", src_file_1, "-f2", src_file_2])
    args = parse_arguments()
    assert args.src_file_1 == src_file_1
    assert args.src_file_2 == src_file_2


@pytest.mark.unit
def test_parse_output_dir_argument(monkeypatch):
    output_dir = "custom_output"
    monkeypatch.setattr("sys.argv", ["ET", "-o", output_dir])
    assert parse_arguments().output_dir == output_dir


@pytest.mark.unit
def test_parse_shuffle_flag(monkeypatch):
    monkeypatch.setattr("sys.argv", ["ET", "--shuffle"])
    assert parse_arguments().shuffle


@pytest.mark.unit
def test_parse_verbose_flag(monkeypatch):
    monkeypatch.setattr("sys.argv", ["ET", "--verbose"])
    assert parse_arguments().verbose


@pytest.mark.unit
def test_parse_all_arguments(monkeypatch):
    profiler = "mac-silicon"
    iteration = 200
    src_file_1 = "custom_with_smell.py"
    src_file_2 = "custom_without_smell.py"
    output_dir = "custom_output_dir"
    shuffle = True
    verbose = True

    monkeypatch.setattr(
        "sys.argv",
        [
            "ET",
            "-p",
            profiler,
            "-n",
            str(iteration),
            "-f1",
            src_file_1,
            "-f2",
            src_file_2,
            "-o",
            output_dir,
            "--shuffle",
            "--verbose",
        ],
    )

    args = parse_arguments()
    assert args.profiler == profiler
    assert args.iter == iteration
    assert args.src_file_1 == src_file_1
    assert args.src_file_2 == src_file_2
    assert args.output_dir == output_dir
    assert args.shuffle == shuffle
    assert args.verbose == verbose
