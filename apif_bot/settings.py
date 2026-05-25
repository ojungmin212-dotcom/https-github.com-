from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class NamuQvSettings:
    module_path: Path | None
    account_no: str
    account_product_code: str
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
            live_trading_enabled=os.getenv(
                "APIF_ENABLE_LIVE_TRADING", "NO"
            ).strip().upper()
            == "YES",
        )

    def missing_items(self) -> list[str]:
        missing = []
        if self.module_path is None:
            missing.append("APIF_NAMU_QV_PATH")
        elif not self.module_path.exists():
            missing.append("APIF_NAMU_QV_PATH points to a missing path")
        if not self.account_no:
            missing.append("APIF_NAMU_ACCOUNT_NO")
        if not self.account_product_code:
            missing.append("APIF_NAMU_ACCOUNT_PRODUCT_CODE")
        return missing


def load_dotenv_file(path: Path = Path(".env")) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
