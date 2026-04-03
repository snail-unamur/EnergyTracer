"""
Tests for src/analysis/utils/get_hardware_details.py

Coverage strategy
─────────────────
  Shared helpers        _read_text, _sysctl, _first_nonempty
  macOS                 _darwin_model, _darwin_chip, _detect_darwin
  Linux - model         _linux_model  (device-tree, DMI paths, junk values, all-missing)
  Linux - chip sources  _chip_from_device_tree, _chip_from_cpuinfo, _chip_from_lscpu
  Linux - orchestrator  _linux_chip   (priority chain, total miss)
  Windows               _detect_windows
  Public API            get_hardware_details (OS dispatch, unsupported OS, chip present/absent)
"""

from __future__ import annotations

from pathlib import Path
import subprocess
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.analysis.utils.get_hardware_details import (
    _chip_from_cpuinfo,
    _chip_from_device_tree,
    _chip_from_lscpu,
    _darwin_chip,
    _darwin_model,
    _detect_darwin,
    _detect_windows,
    _first_nonempty,
    _linux_chip,
    _linux_model,
    _read_text,
    _sysctl,
    get_hardware_details,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_file(tmp_path: Path):
    """Factory: create a temporary file with given content and return its path."""

    def _make(content: str, name: str = "file.txt") -> str:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return str(p)

    return _make


@pytest.fixture()
def missing_path(tmp_path: Path) -> str:
    """A path that is guaranteed not to exist."""
    return str(tmp_path / "does_not_exist")


@pytest.fixture()
def sysctl_ok():
    """Patch subprocess.check_output to simulate a successful sysctl call."""
    with patch("subprocess.check_output", return_value="MacBookPro18,3\n") as m:
        yield m


@pytest.fixture()
def sysctl_fail():
    """Patch subprocess.check_output to always raise CalledProcessError."""
    with patch(
        "subprocess.check_output",
        side_effect=subprocess.CalledProcessError(1, "sysctl"),
    ) as m:
        yield m


# ── _read_text ────────────────────────────────────────────────────────────────


class TestReadText:
    def test_reads_plain_text(self, tmp_file):
        path = tmp_file("hello world")
        assert _read_text(path) == "hello world"

    def test_strips_null_bytes(self, tmp_file):
        path = tmp_file("Raspberry Pi 3 Model B Rev 1.2\x00")
        assert _read_text(path) == "Raspberry Pi 3 Model B Rev 1.2"

    def test_strips_surrounding_whitespace(self, tmp_file):
        path = tmp_file("  value  \n")
        assert _read_text(path) == "value"

    def test_returns_none_on_missing_file(self, missing_path):
        assert _read_text(missing_path) is None


# ── _sysctl ───────────────────────────────────────────────────────────────────


class TestSysctl:
    def test_returns_stripped_output(self):
        with patch("subprocess.check_output", return_value="MacBookPro18,3\n"):
            assert _sysctl("hw.model", "/usr/sbin/sysctl") == "MacBookPro18,3"

    def test_returns_none_on_empty_output(self):
        with patch("subprocess.check_output", return_value="   "):
            assert _sysctl("hw.model", "/usr/sbin/sysctl") is None

    def test_returns_none_on_called_process_error(self):
        with patch(
            "subprocess.check_output",
            side_effect=subprocess.CalledProcessError(1, "sysctl"),
        ):
            assert _sysctl("hw.chip_model", "/usr/sbin/sysctl") is None

    def test_returns_none_on_file_not_found(self):
        with patch("subprocess.check_output", side_effect=FileNotFoundError):
            assert _sysctl("hw.model", "/nonexistent/sysctl") is None


# ── _first_nonempty ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "contents, junk, expected",
    [
        # First path is readable and valid
        (["good value", "other"], set(), "good value"),
        # First path is junk → falls through to second
        (
            ["To be filled by O.E.M.", "real model"],
            {"To be filled by O.E.M."},
            "real model",
        ),
        # All paths are junk
        (["Default string", ""], {"Default string", ""}, None),
        # All paths missing (simulated by returning None from _read_text)
        ([None, None], set(), None),
        # Empty string is always skipped (falsy)
        (["", "valid"], set(), "valid"),
    ],
)
def test_first_nonempty(tmp_path, contents, junk, expected):
    paths = []
    for i, content in enumerate(contents):
        if content is None:
            paths.append(str(tmp_path / f"missing_{i}"))  # non-existent
        else:
            p = tmp_path / f"file_{i}.txt"
            p.write_text(content, encoding="utf-8")
            paths.append(str(p))

    assert _first_nonempty(tuple(paths), junk=junk) == expected


# ── _darwin_model ─────────────────────────────────────────────────────────────


class TestDarwinModel:
    def test_returns_sysctl_result(self, sysctl_ok):
        with patch("platform.machine", return_value="arm64"):
            assert _darwin_model("/usr/sbin/sysctl") == "MacBookPro18,3"

    def test_fallback_to_machine_on_failure(self, sysctl_fail):
        with patch("platform.machine", return_value="arm64"):
            result = _darwin_model("/usr/sbin/sysctl")
        assert result == "arm64"

    def test_warns_on_failure(self, sysctl_fail):
        with (
            patch("src.analysis.utils.get_hardware_details.warn") as mock_warn,
            patch("platform.machine", return_value="arm64"),
        ):
            _darwin_model("/usr/sbin/sysctl")
        mock_warn.assert_called_once()
        assert "hw.model" in mock_warn.call_args[0][0]


# ── _darwin_chip ──────────────────────────────────────────────────────────────


class TestDarwinChip:
    def test_returns_brand_string_for_intel(self):
        with patch(
            "subprocess.check_output", return_value="Intel(R) Core(TM) i9-9880H\n"
        ):
            result = _darwin_chip("/usr/sbin/sysctl")
        assert result == "Intel(R) Core(TM) i9-9880H"

    def test_falls_back_to_system_profiler_chip_line(self):
        sp_output = (
            "Hardware Overview:\n"
            "      Chip: Apple M1 Pro\n"
            "      Total Number of Cores: 10\n"
        )
        with (
            patch(
                "subprocess.check_output",
                side_effect=subprocess.CalledProcessError(1, "sysctl"),
            ),
            patch("shutil.which", return_value="/usr/sbin/system_profiler"),
            patch("subprocess.check_output", return_value=sp_output),
        ):
            # Re-patch check_output globally for the system_profiler call
            pass

        # Cleaner approach: first call fails, second succeeds
        results = [
            subprocess.CalledProcessError(1, "sysctl"),
            sp_output,
        ]
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            val = results[call_count]
            call_count += 1
            if isinstance(val, Exception):
                raise val
            return val

        with (
            patch("subprocess.check_output", side_effect=side_effect),
            patch("shutil.which", return_value="/usr/sbin/system_profiler"),
        ):
            result = _darwin_chip("/usr/sbin/sysctl")
        assert result == "Apple M1 Pro"

    def test_falls_back_to_system_profiler_processor_name_line(self):
        sp_output = "      Processor Name: Intel Core i9\n"
        results = [subprocess.CalledProcessError(1, "sysctl"), sp_output]
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            val = results[call_count]
            call_count += 1
            if isinstance(val, Exception):
                raise val
            return val

        with (
            patch("subprocess.check_output", side_effect=side_effect),
            patch("shutil.which", return_value="/usr/sbin/system_profiler"),
        ):
            result = _darwin_chip("/usr/sbin/sysctl")
        assert result == "Intel Core i9"

    def test_returns_none_when_system_profiler_missing(self):
        with (
            patch(
                "subprocess.check_output",
                side_effect=subprocess.CalledProcessError(1, "sysctl"),
            ),
            patch("shutil.which", return_value=None),
        ):
            result = _darwin_chip("/usr/sbin/sysctl")
        assert result is None

    def test_returns_none_when_system_profiler_raises(self):
        results = [subprocess.CalledProcessError(1, "sysctl"), OSError("boom")]
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            val = results[call_count]
            call_count += 1
            if isinstance(val, Exception):
                raise val
            return val

        with (
            patch("subprocess.check_output", side_effect=side_effect),
            patch("shutil.which", return_value="/usr/sbin/system_profiler"),
        ):
            result = _darwin_chip("/usr/sbin/sysctl")
        assert result is None


# ── _detect_darwin ────────────────────────────────────────────────────────────


class TestDetectDarwin:
    def test_returns_fallback_when_sysctl_missing(self):
        with (
            patch("shutil.which", return_value=None),
            patch("platform.machine", return_value="arm64"),
        ):
            model, chip = _detect_darwin()
        assert model == "arm64"
        assert chip is None

    def test_calls_darwin_model_and_chip(self):
        with (
            patch("shutil.which", return_value="/usr/sbin/sysctl"),
            patch(
                "src.analysis.utils.get_hardware_details._darwin_model",
                return_value="MacBookPro18,3",
            ),
            patch(
                "src.analysis.utils.get_hardware_details._darwin_chip",
                return_value="Apple M1 Pro",
            ),
        ):
            model, chip = _detect_darwin()
        assert model == "MacBookPro18,3"
        assert chip == "Apple M1 Pro"


# ── _linux_model ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "readable_path_index, content, expected",
    [
        # device-tree/model - Raspberry Pi
        (0, "Raspberry Pi 3 Model B Rev 1.2\x00", "Raspberry Pi 3 Model B Rev 1.2"),
        # sys/firmware/devicetree - alternate DT mount
        (1, "Raspberry Pi 4 Model B", "Raspberry Pi 4 Model B"),
        # DMI canonical - x86 bare-metal
        (2, "HP EliteBook 840", "HP EliteBook 840"),
        # DMI legacy alias
        (3, "r7i.xlarge", "r7i.xlarge"),
    ],
)
def test_linux_model_sources(readable_path_index: int, content: str, expected: str):
    """_linux_model returns the value of the first valid path."""
    paths = [
        "/proc/device-tree/model",
        "/sys/firmware/devicetree/base/model",
        "/sys/class/dmi/id/product_name",
        "/sys/devices/virtual/dmi/id/product_name",
        "/sys/class/dmi/id/board_name",
        "/sys/devices/virtual/dmi/id/board_name",
    ]

    def fake_read_text(path: str) -> str | None:
        if path == paths[readable_path_index]:
            return content.rstrip("\x00").strip()
        return None

    with patch(
        "src.analysis.utils.get_hardware_details._read_text", side_effect=fake_read_text
    ):
        assert _linux_model() == expected


@pytest.mark.parametrize("junk_value", ["", "To be filled by O.E.M.", "Default string"])
def test_linux_model_skips_junk_values(junk_value: str):
    """DMI junk values are ignored; falls back to platform.machine()."""
    with (
        patch(
            "src.analysis.utils.get_hardware_details._read_text",
            return_value=junk_value,
        ),
        patch("platform.machine", return_value="x86_64"),
        patch("src.analysis.utils.get_hardware_details.warn"),
    ):
        assert _linux_model() == "x86_64"


def test_linux_model_warns_when_all_sources_missing():
    with (
        patch("src.analysis.utils.get_hardware_details._read_text", return_value=None),
        patch("platform.machine", return_value="x86_64"),
        patch("src.analysis.utils.get_hardware_details.warn") as mock_warn,
    ):
        _linux_model()
    mock_warn.assert_called_once()
    assert "no recognised source" in mock_warn.call_args[0][0]


# ── _chip_from_device_tree ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw_bytes, expected",
    [
        # Pi 3 - two tokens, last is the SoC
        (b"raspberrypi,3-model-b\x00brcm,bcm2837\x00", "brcm,bcm2837"),
        # Pi 4
        (b"raspberrypi,4-model-b\x00brcm,bcm2711\x00", "brcm,bcm2711"),
        # Single token
        (b"brcm,bcm2835\x00", "brcm,bcm2835"),
        # Trailing garbage null
        (b"foo,bar\x00baz,qux\x00\x00", "baz,qux"),
    ],
)
def test_chip_from_device_tree_parsing(tmp_path, raw_bytes: bytes, expected: str):
    dt = tmp_path / "compatible"
    dt.write_bytes(raw_bytes)
    with patch("src.analysis.utils.get_hardware_details.Path") as mock_path:
        mock_p = MagicMock()
        mock_p.read_bytes.return_value = raw_bytes
        mock_path.return_value = mock_p
        result = _chip_from_device_tree()
    assert result == expected


def test_chip_from_device_tree_returns_none_on_oserror():
    with (
        patch("builtins.open", side_effect=OSError),
        patch.object(Path, "read_bytes", side_effect=OSError),
    ):
        assert _chip_from_device_tree() is None


# ── _chip_from_cpuinfo ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "cpuinfo_content, expected",
    [
        # x86_64
        (
            "processor\t: 0\nmodel name\t: Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz\n",
            "Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz",
        ),
        # capitalised variant
        (
            "Model name\t: AMD Ryzen 9 5900X\n",
            "AMD Ryzen 9 5900X",
        ),
        # 32-bit ARM - Hardware field
        (
            "processor\t: 0\nHardware\t: BCM2709\n",
            "BCM2709",
        ),
        # model name takes priority over Hardware when both present
        (
            "model name\t: Cortex-A72\nHardware\t: BCM2711\n",
            "Cortex-A72",
        ),
    ],
)
def test_chip_from_cpuinfo(cpuinfo_content: str, expected: str):
    with (
        patch("builtins.open", mock_open(read_data=cpuinfo_content)),
        patch.object(Path, "read_text", return_value=cpuinfo_content),
    ):
        assert _chip_from_cpuinfo() == expected


def test_chip_from_cpuinfo_returns_none_when_no_field():
    content = "processor\t: 0\nvendor_id\t: GenuineIntel\n"
    with patch.object(Path, "read_text", return_value=content):
        assert _chip_from_cpuinfo() is None


def test_chip_from_cpuinfo_returns_none_on_oserror():
    with patch.object(Path, "read_text", side_effect=OSError):
        assert _chip_from_cpuinfo() is None


# ── _chip_from_lscpu ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "lscpu_output, expected",
    [
        # x86 with Model name
        (
            "Architecture: x86_64\nModel name:  Intel(R) Xeon(R) Platinum 8375C\n",
            "Intel(R) Xeon(R) Platinum 8375C",
        ),
        # ARM server - no Model name, falls back to Vendor ID
        (
            "Architecture: aarch64\nVendor ID:   ARM\n",
            "ARM",
        ),
        # Model name present - takes priority over Vendor ID
        (
            "Model name:  Cortex-A76\nVendor ID:   ARM\n",
            "Cortex-A76",
        ),
    ],
)
def test_chip_from_lscpu(lscpu_output: str, expected: str):
    with (
        patch("shutil.which", return_value="/usr/bin/lscpu"),
        patch("subprocess.check_output", return_value=lscpu_output),
    ):
        assert _chip_from_lscpu() == expected


def test_chip_from_lscpu_returns_none_when_lscpu_missing():
    with patch("shutil.which", return_value=None):
        assert _chip_from_lscpu() is None


def test_chip_from_lscpu_returns_none_on_subprocess_error():
    with (
        patch("shutil.which", return_value="/usr/bin/lscpu"),
        patch("subprocess.check_output", side_effect=OSError),
    ):
        assert _chip_from_lscpu() is None


def test_chip_from_lscpu_returns_none_when_no_matching_field():
    with (
        patch("shutil.which", return_value="/usr/bin/lscpu"),
        patch("subprocess.check_output", return_value="Architecture: aarch64\n"),
    ):
        assert _chip_from_lscpu() is None


# ── _linux_chip (priority chain) ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "dt_result, cpuinfo_result, lscpu_result, expected",
    [
        # device-tree wins
        ("brcm,bcm2837", "Cortex-A53", "ARM", "brcm,bcm2837"),
        # device-tree missing, cpuinfo wins
        (None, "Intel Core i7", "Intel", "Intel Core i7"),
        # both missing, lscpu wins
        (None, None, "ARM", "ARM"),
        # all missing → None
        (None, None, None, None),
    ],
)
def test_linux_chip_priority(dt_result, cpuinfo_result, lscpu_result, expected):
    with (
        patch(
            "src.analysis.utils.get_hardware_details._chip_from_device_tree",
            return_value=dt_result,
        ),
        patch(
            "src.analysis.utils.get_hardware_details._chip_from_cpuinfo",
            return_value=cpuinfo_result,
        ),
        patch(
            "src.analysis.utils.get_hardware_details._chip_from_lscpu",
            return_value=lscpu_result,
        ),
        patch("src.analysis.utils.get_hardware_details.warn"),
    ):
        assert _linux_chip() == expected


def test_linux_chip_warns_when_all_sources_fail():
    with (
        patch(
            "src.analysis.utils.get_hardware_details._chip_from_device_tree",
            return_value=None,
        ),
        patch(
            "src.analysis.utils.get_hardware_details._chip_from_cpuinfo",
            return_value=None,
        ),
        patch(
            "src.analysis.utils.get_hardware_details._chip_from_lscpu",
            return_value=None,
        ),
        patch("src.analysis.utils.get_hardware_details.warn") as mock_warn,
    ):
        _linux_chip()
    mock_warn.assert_called_once()
    assert "chip detection skipped" in mock_warn.call_args[0][0]


# ── _detect_windows ───────────────────────────────────────────────────────────


class TestDetectWindows:
    def test_returns_model_from_wmic(self):
        with (
            patch("shutil.which", return_value="C:\\Windows\\System32\\wmic.exe"),
            patch("subprocess.check_output", return_value="Name=Surface Pro 9\r\n"),
        ):
            model, chip = _detect_windows()
        assert model == "Surface Pro 9"
        assert chip is None

    def test_fallback_when_wmic_missing(self):
        with (
            patch("shutil.which", return_value=None),
            patch("platform.machine", return_value="AMD64"),
            patch("src.analysis.utils.get_hardware_details.warn"),
        ):
            model, chip = _detect_windows()
        assert model == "AMD64"
        assert chip is None

    def test_fallback_on_wmic_error(self):
        with (
            patch("shutil.which", return_value="C:\\wmic.exe"),
            patch("subprocess.check_output", side_effect=OSError),
            patch("platform.machine", return_value="AMD64"),
            patch("src.analysis.utils.get_hardware_details.warn"),
        ):
            model, chip = _detect_windows()
        assert model == "AMD64"
        assert chip is None

    def test_uses_powershell_when_wmic_missing(self):
        def which_side_effect(binary: str) -> str | None:
            if binary == "wmic":
                return None
            if binary == "powershell":
                return "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
            return None

        with (
            patch("shutil.which", side_effect=which_side_effect),
            patch(
                "subprocess.check_output", return_value="Hyper-V Virtual Machine\r\n"
            ),
        ):
            model, chip = _detect_windows()
        assert model == "Hyper-V Virtual Machine"
        assert chip is None

    def test_uses_powershell_when_wmic_fails(self):
        def which_side_effect(binary: str) -> str | None:
            if binary == "wmic":
                return "C:\\Windows\\System32\\wbem\\wmic.exe"
            if binary == "powershell":
                return "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
            return None

        calls = [OSError("wmic failed"), "VMware Virtual Platform\r\n"]

        def check_output_side_effect(*args, **kwargs):
            value = calls.pop(0)
            if isinstance(value, Exception):
                raise value
            return value

        with (
            patch("shutil.which", side_effect=which_side_effect),
            patch("subprocess.check_output", side_effect=check_output_side_effect),
        ):
            model, chip = _detect_windows()
        assert model == "VMware Virtual Platform"
        assert chip is None


# ── get_hardware_details (public API) ─────────────────────────────────────────


@pytest.mark.parametrize(
    "os_name, detector_patch, model, chip",
    [
        ("Darwin", "_detect_darwin", "MacBookPro18,3", "Apple M1 Pro"),
        ("Linux", "_detect_linux", "Raspberry Pi 3 Model B Rev 1.2", "brcm,bcm2837"),
        ("Windows", "_detect_windows", "Surface Pro 9", None),
    ],
)
def test_get_hardware_details_dispatches_by_os(os_name, detector_patch, model, chip):
    with (
        patch("platform.system", return_value=os_name),
        patch("platform.release", return_value="1.0"),
        patch("platform.machine", return_value="arm64"),
        patch("socket.gethostname", return_value="test-host"),
        patch(
            f"src.analysis.utils.get_hardware_details.{detector_patch}",
            return_value=(model, chip),
        ),
    ):
        result = get_hardware_details()

    assert result["hostname"] == "test-host"
    assert result["model"] == model
    assert result["os"] == f"{os_name} 1.0"
    assert result["machine"] == "arm64"
    if chip:
        assert result["chip"] == chip
    else:
        assert "chip" not in result


def test_get_hardware_details_unsupported_os():
    with (
        patch("platform.system", return_value="FreeBSD"),
        patch("platform.release", return_value="13.0"),
        patch("platform.machine", return_value="amd64"),
        patch("socket.gethostname", return_value="bsd-host"),
        patch("src.analysis.utils.get_hardware_details.warn") as mock_warn,
    ):
        result = get_hardware_details()

    assert result["model"] == "amd64"  # fallback to platform.machine()
    assert "chip" not in result
    mock_warn.assert_called_once()
    assert "unsupported OS" in mock_warn.call_args[0][0]


def test_get_hardware_details_result_keys_always_present():
    """The four mandatory keys must always be in the result."""
    with (
        patch("platform.system", return_value="Linux"),
        patch(
            "src.analysis.utils.get_hardware_details._detect_linux",
            return_value=("SomeBoard", None),
        ),
    ):
        result = get_hardware_details()
    assert {"hostname", "model", "os", "machine"} <= result.keys()
