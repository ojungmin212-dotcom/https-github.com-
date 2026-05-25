from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import platform
import struct


@dataclass(frozen=True)
class NamuQvSettings:
    module_path: Path | None
    account_no: str
    account_product_code: str
    bridge_command: str
    live_trading_enabled: bool

    @classmethod
    def from_env(cls) -> "NamuQvSettings":
        module_path = os.getenv("APIF_NAMU_QV_PATH", "").strip()
        return cls(
            module_path=Path(module_path) if module_path else None,
            account_no=os.getenv("APIF_NAMU_ACCOUNT_NO", "").strip(),
            account_product_code=os.getenv(
                "APIF_NAMU_ACCOUNT_PRODUCT_CODE", ""
            ).strip(),
            bridge_command=os.getenv("APIF_NAMU_BRIDGE_COMMAND", "").strip(),
            live_trading_enabled=os.getenv(
                "APIF_ENABLE_LIVE_TRADING", "NO"
            ).strip().upper()
            == "YES",
        )

    def missing_items(self) -> list[str]:
        return self.missing_connection_items() + self.missing_account_items()

    def missing_connection_items(self) -> list[str]:
        missing = []
        if self.module_path is None:
            missing.append("APIF_NAMU_QV_PATH")
        elif not self.module_path.exists():
            missing.append("APIF_NAMU_QV_PATH points to a missing path")
        elif not self.wmca_dll_path().exists():
            missing.append("APIF_NAMU_QV_PATH does not contain bin/wmca.dll")
        if not self.bridge_command:
            missing.append("APIF_NAMU_BRIDGE_COMMAND")
        return missing

    def missing_account_items(self) -> list[str]:
        missing = []
        if not self.account_no:
            missing.append("APIF_NAMU_ACCOUNT_NO")
        if not self.account_product_code:
            missing.append("APIF_NAMU_ACCOUNT_PRODUCT_CODE")
        return missing

    def wmca_dll_path(self) -> Path:
        if self.module_path is None:
            return Path("bin") / "wmca.dll"
        return self.module_path / "bin" / "wmca.dll"

    def wmca_architecture(self) -> str | None:
        dll_path = self.wmca_dll_path()
        if not dll_path.exists():
            return None
        return pe_architecture(dll_path)


def pe_architecture(path: Path) -> str:
    data = path.read_bytes()
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    machine = struct.unpack_from("<H", data, pe_offset + 4)[0]
    if machine == 0x14C:
        return "x86"
    if machine == 0x8664:
        return "x64"
    return f"unknown:0x{machine:X}"


def python_architecture() -> str:
    return "x64" if platform.architecture()[0] == "64bit" else "x86"


def load_dotenv_file(path: Path = Path(".env")) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
