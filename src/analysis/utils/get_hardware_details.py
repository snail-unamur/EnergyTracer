from pathlib import Path
import platform
import shutil
import socket
import subprocess

from src.utilities.log import warn


def get_hardware_details() -> dict[str, str]:
    """
    Collect hardware model and chip info using OS-specific sources.

    - macOS  : sysctl (hw.model + hw.chip_model) - fast, no sudo required.
    - Linux  : DMI sysfs files - works on bare-metal and most cloud VMs.
    - Windows: wmic csproduct.
    Falls back to platform.machine() when nothing else is available.

    Authors: Florian Stormacq, with the help of Claude Sonnet 4.6
    """

    model: str = platform.machine()  # fallback
    chip: str | None = None
    system = platform.system()

    if system == "Darwin":
        sysctl_path = shutil.which("sysctl")
        if not sysctl_path:
            warn("sysctl not found - hardware model detection skipped")
        else:
            try:
                model = subprocess.check_output(  # noqa: S603
                    [sysctl_path, "-n", "hw.model"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
            except Exception:
                warn("hw.model unavailable - hardware model detection skipped")

        # Chip detection - ordered from fastest to most compatible:
        #   1. machdep.cpu.brand_string  → Intel Macs
        #   2. system_profiler           → Apple Silicon (universal, slightly slower)
        try:
            if sysctl_path:
                chip = (
                    subprocess.check_output(  # noqa: S603
                        [sysctl_path, "-n", "machdep.cpu.brand_string"],
                        text=True,
                        stderr=subprocess.DEVNULL,
                    ).strip()
                    or None
                )
        except Exception:
            chip = None

        if not chip:
            warn(
                "machdep.cpu.brand_string unavailable - falling back to system_profiler"
            )
            try:
                sp_path = shutil.which("system_profiler")
                if not sp_path:
                    warn("system_profiler not found - chip detection skipped")
                else:
                    sp_out = subprocess.check_output(  # noqa: S603
                        [sp_path, "SPHardwareDataType"], text=True
                    )
                    for line in sp_out.splitlines():
                        if "Chip" in line or "Processor Name" in line:
                            chip = line.split(":", 1)[-1].strip()
                            break
            except Exception:
                warn("system_profiler failed - chip detection skipped")

    elif system == "Linux":
        for path in (
            "/sys/devices/virtual/dmi/id/product_name",
            "/sys/devices/virtual/dmi/id/board_name",
        ):
            try:
                with Path.open(path) as fh:
                    value = fh.read().strip()
                if value and value not in ("", "To be filled by O.E.M."):
                    model = value
                    break
            except OSError:
                pass
        else:
            warn("DMI sysfs unavailable - hardware model detection skipped")

        try:
            with Path.open("/proc/cpuinfo") as fh:
                for line in fh:
                    if line.startswith("Model name") or line.startswith("model name"):
                        chip = line.split(":", 1)[1].strip()
                        break
        except OSError:
            warn("/proc/cpuinfo unavailable - chip detection skipped")

    elif system == "Windows":
        try:
            wmic_path = shutil.which("wmic")
            if not wmic_path:
                warn("wmic not found - hardware model detection skipped")
            else:
                model = (
                    subprocess.check_output(  # noqa: S603
                        [wmic_path, "csproduct", "get", "name", "/value"],
                        text=True,
                        stderr=subprocess.DEVNULL,
                    )
                    .strip()
                    .split("=", 1)[-1]
                )
        except Exception:
            warn("wmic failed - hardware model detection skipped")

    result = {
        "hostname": socket.gethostname(),
        "model": model,
        "os": f"{system} {platform.release()}",
        "machine": platform.machine(),
    }
    if chip:
        result["chip"] = chip

    return result
