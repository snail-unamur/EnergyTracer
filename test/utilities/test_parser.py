from src.utilities.parser import *

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

def test_parse_profiler_argument(monkeypatch):
    monkeypatch.setattr("sys.argv", ["ET", "-p", "mac-silicon"])
    assert parse_arguments().profiler == "mac-silicon"

    monkeypatch.setattr("sys.argv", ["ET", "-p", "carbon"])
    assert parse_arguments().profiler == "carbon"

def test_parse_iterations_argument(monkeypatch):
    ITERATION = 500
    monkeypatch.setattr("sys.argv", ["ET", "-n", str(ITERATION)])
    assert parse_arguments().iter == ITERATION

def test_parse_src_file_arguments(monkeypatch):
    SRC_FILE_1 = "custom_path_with_smell.py"
    SRC_FILE_2 = "custom_path_without_smell.py"
    monkeypatch.setattr("sys.argv", ["ET", "-f1", SRC_FILE_1, "-f2", SRC_FILE_2])
    args = parse_arguments()
    assert args.src_file_1 == SRC_FILE_1
    assert args.src_file_2 == SRC_FILE_2

def test_parse_output_dir_argument(monkeypatch):
    OUTPUT_DIR = "custom_output"
    monkeypatch.setattr("sys.argv", ["ET", "-o", OUTPUT_DIR])
    assert parse_arguments().output_dir == OUTPUT_DIR

def test_parse_shuffle_flag(monkeypatch):
    monkeypatch.setattr("sys.argv", ["ET", "--shuffle"])
    assert parse_arguments().shuffle == True

def test_parse_verbose_flag(monkeypatch):
    monkeypatch.setattr("sys.argv", ["ET", "--verbose"])
    assert parse_arguments().verbose == True

def test_parse_all_arguments(monkeypatch):
    PROFILER = "mac-silicon"
    ITERATION = 200
    SRC_FILE_1 = "custom_with_smell.py"
    SRC_FILE_2 = "custom_without_smell.py"
    OUTPUT_DIR = "custom_output_dir"
    SHUFFLE = True
    VERBOSE = True

    monkeypatch.setattr("sys.argv", [
        "ET",
        "-p", PROFILER,
        "-n", str(ITERATION),
        "-f1", SRC_FILE_1,
        "-f2", SRC_FILE_2,
        "-o", OUTPUT_DIR,
        "--shuffle",
        "--verbose"
    ])

    args = parse_arguments()
    assert args.profiler == PROFILER
    assert args.iter == ITERATION
    assert args.src_file_1 == SRC_FILE_1
    assert args.src_file_2 == SRC_FILE_2
    assert args.output_dir == OUTPUT_DIR
    assert args.shuffle == SHUFFLE
    assert args.verbose == VERBOSE