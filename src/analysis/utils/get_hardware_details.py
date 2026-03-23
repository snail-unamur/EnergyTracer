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
        # 1. Board / model detection
        #    Priority: device-tree (Raspberry Pi, most ARM SBCs) > DMI sysfs (x86 / cloud VMs)
        for path in (
            "/proc/device-tree/model",
            "/sys/devices/virtual/dmi/id/product_name",
            "/sys/devices/virtual/dmi/id/board_name",
        ):
            try:
                value = Path(path).read_text(encoding="utf-8").rstrip("\x00").strip()
                if value and value not in ("", "To be filled by O.E.M."):
                    model = value
                    break
            except OSError:
                pass
        else:
            warn(
                "Neither device-tree nor DMI sysfs available - hardware model detection skipped"
            )

        # 2. Chip / CPU detection — ordered from most to least reliable:
        #   a) /proc/device-tree/compatible  — 64-bit ARM (Pi 3/4/5, Jetson, …)
        #      Format: null-separated list, last token is the SoC (e.g. "brcm,bcm2837")
        #   b) /proc/cpuinfo "model name"    — x86 / x86_64
        #   c) /proc/cpuinfo "Hardware"      — older 32-bit ARM kernels
        try:
            raw = Path("/proc/device-tree/compatible").read_bytes()
            tokens = [
                t.decode("utf-8", errors="replace").strip()
                for t in raw.split(b"\0")
                if t.strip()
            ]
            if tokens:
                chip = tokens[-1]  # last entry is the SoC
        except OSError:
            pass

        if not chip:
            try:
                cpuinfo = Path("/proc/cpuinfo").read_text(encoding="utf-8")
                for field in ("model name", "Model name", "Hardware"):
                    for line in cpuinfo.splitlines():
                        if line.startswith(field):
                            chip = line.split(":", 1)[1].strip()
                            break
                    if chip:
                        break
            except OSError:
                pass

        if not chip:
            warn(
                "chip detection skipped - no recognised source found (device-tree, cpuinfo)"
            )

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
