from pathlib import Path
import platform
import shutil
import socket
import subprocess

from src.utilities.log import warn

# Values that DMI sysfs may return on unconfigured or virtual machines.
_DMI_JUNK = {"", "To be filled by O.E.M.", "Default string"}


# ── Shared helpers ────────────────────────────────────────────────────────────


def _read_text(path: str) -> str | None:
    """Read a sysfs / procfs text file, stripping null bytes and whitespace.
    Returns None on any OS error."""
    try:
        return Path(path).read_text(encoding="utf-8").rstrip("\x00").strip()
    except OSError:
        return None


def _sysctl(key: str, sysctl_path: str) -> str | None:
    """Run ``sysctl -n <key>`` and return the stripped output, or None."""
    try:
        return (
            subprocess.check_output(  # noqa: S603
                [sysctl_path, "-n", key],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            or None
        )
    except Exception:
        return None


def _first_nonempty(paths: tuple[str, ...], junk: set[str] = frozenset()) -> str | None:
    """Return the content of the first readable path whose value is not junk."""
    for path in paths:
        value = _read_text(path)
        if value and value not in junk:
            return value
    return None


# ── macOS ─────────────────────────────────────────────────────────────────────


def _darwin_model(sysctl_path: str) -> str:
    """hw.model → e.g. 'MacBookPro18,3'."""
    model = _sysctl("hw.model", sysctl_path)
    if not model:
        warn("hw.model unavailable - hardware model detection skipped")
    return model or platform.machine()


def _darwin_chip(sysctl_path: str) -> str | None:
    """
    Chip detection for macOS.
      1. machdep.cpu.brand_string - Intel Macs (fast).
      2. system_profiler SPHardwareDataType - Apple Silicon (universal, slower).
    """
    chip = _sysctl("machdep.cpu.brand_string", sysctl_path)
    if chip:
        return chip

    warn("machdep.cpu.brand_string unavailable - falling back to system_profiler")
    sp_path = shutil.which("system_profiler")
    if not sp_path:
        warn("system_profiler not found - chip detection skipped")
        return None
    try:
        sp_out = subprocess.check_output(  # noqa: S603
            [sp_path, "SPHardwareDataType"], text=True
        )
        for line in sp_out.splitlines():
            if "Chip" in line or "Processor Name" in line:
                return line.split(":", 1)[-1].strip()
    except Exception:
        warn("system_profiler failed - chip detection skipped")
    return None


def _detect_darwin() -> tuple[str, str | None]:
    """Return (model, chip) for macOS."""
    sysctl_path = shutil.which("sysctl")
    if not sysctl_path:
        warn("sysctl not found - hardware detection skipped")
        return platform.machine(), None
    return _darwin_model(sysctl_path), _darwin_chip(sysctl_path)


# ── Linux - model ─────────────────────────────────────────────────────────────


def _linux_model() -> str:
    """
    Board / product name for Linux.
    Priority: device-tree (ARM SBCs, Graviton) > DMI sysfs (x86, cloud VMs).
    """
    model = _first_nonempty(
        (
            "/proc/device-tree/model",  # ARM: Pi, Jetson, Graviton...
            "/sys/firmware/devicetree/base/model",  # alternate DT mount point
            "/sys/class/dmi/id/product_name",  # x86 canonical DMI
            "/sys/devices/virtual/dmi/id/product_name",  # x86 legacy alias
            "/sys/class/dmi/id/board_name",
            "/sys/devices/virtual/dmi/id/board_name",
        ),
        junk=_DMI_JUNK,
    )
    if not model:
        warn("hardware model detection skipped - no recognised source found")
    return model or platform.machine()


# ── Linux - chip (one function per source) ────────────────────────────────────


def _chip_from_device_tree() -> str | None:
    """
    Read /proc/device-tree/compatible (null-separated list).
    The last non-empty token is the SoC identifier, e.g. 'brcm,bcm2837'.
    Works on all ARM Linux kernels that expose a device-tree.
    """
    try:
        raw = Path("/proc/device-tree/compatible").read_bytes()
        tokens = [
            t.decode("utf-8", errors="replace").strip()
            for t in raw.split(b"\0")
            if t.strip()
        ]
        return tokens[-1] if tokens else None
    except OSError:
        return None


def _chip_from_cpuinfo() -> str | None:
    """
    Parse /proc/cpuinfo for a human-readable CPU name.
      - 'model name' -> x86 / x86_64 and some ARM kernels
      - 'Hardware'   -> 32-bit ARM (older kernels)
    """
    try:
        cpuinfo = Path("/proc/cpuinfo").read_text(encoding="utf-8")
        for field in ("model name", "Model name", "Hardware"):
            for line in cpuinfo.splitlines():
                if line.startswith(field):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return None


def _chip_from_lscpu() -> str | None:
    """
    Last-resort: parse lscpu output.
    Covers ARM servers (Graviton, Ampere Altra) where device-tree is
    inaccessible and cpuinfo fields are sparse.
    """
    lscpu_path = shutil.which("lscpu")
    if not lscpu_path:
        return None
    try:
        out = subprocess.check_output(  # noqa: S603
            [lscpu_path], text=True, stderr=subprocess.DEVNULL
        )
        for field in ("Model name", "Vendor ID"):
            for line in out.splitlines():
                if line.startswith(field):
                    return line.split(":", 1)[1].strip()
    except Exception:
        warn("lscpu failed - chip detection skipped")
    return None


def _linux_chip() -> str | None:
    """
    Chip detection for Linux - tries sources in order of reliability:
      1. device-tree/compatible  (all ARM with DT: Pi, Jetson, Graviton...)
      2. /proc/cpuinfo           (x86, 32-bit ARM)
      3. lscpu                   (ARM servers fallback)
    """
    chip = _chip_from_device_tree() or _chip_from_cpuinfo() or _chip_from_lscpu()
    if not chip:
        warn("chip detection skipped - no recognised source found")
    return chip


def _detect_linux() -> tuple[str, str | None]:
    """Return (model, chip) for Linux."""
    return _linux_model(), _linux_chip()


# ── Windows ───────────────────────────────────────────────────────────────────


def _detect_windows() -> tuple[str, str | None]:
    """Return (model, chip) for Windows via wmic."""
    wmic_path = shutil.which("wmic")
    if not wmic_path:
        warn("wmic not found - hardware model detection skipped")
        return platform.machine(), None
    try:
        model = (
            subprocess.check_output(  # noqa: S603
                [wmic_path, "csproduct", "get", "name", "/value"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            .strip()
            .split("=", 1)[-1]
        )
        return model, None  # wmic doesn't expose chip info easily
    except Exception:
        warn("wmic failed - hardware model detection skipped")
        return platform.machine(), None


# ── Public API ────────────────────────────────────────────────────────────────


def get_hardware_details() -> dict[str, str]:
    """
    Collect hardware model and chip info using OS-specific sources.

    - macOS  : sysctl (hw.model + brand_string) -> system_profiler fallback.
    - Linux  : device-tree > DMI sysfs > cpuinfo > lscpu - covers ARM SBCs,
               x86 bare-metal, cloud VMs, and ARM servers (Graviton, Ampere).
    - Windows: wmic csproduct.
    Falls back to platform.machine() when nothing else is available.

    Authors: Florian Stormacq, with the help of Claude Sonnet 4.6
    """
    system = platform.system()
    detectors = {
        "Darwin": _detect_darwin,
        "Linux": _detect_linux,
        "Windows": _detect_windows,
    }
    detect = detectors.get(system)
    if detect is None:
        warn(f"unsupported OS '{system}' - hardware detection skipped")
        model, chip = platform.machine(), None
    else:
        model, chip = detect()

    result = {
        "hostname": socket.gethostname(),
        "model": model,
        "os": f"{system} {platform.release()}",
        "machine": platform.machine(),
    }
    if chip:
        result["chip"] = chip
    return result
