from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .broker import DryRunBroker
from .engine import TradingEngine
from .models import TradingPlan
from .namu_qv import NamuQvQuoteProvider, NamuQvSession
from .settings import NamuQvSettings, load_dotenv_file


ROOT = Path(__file__).resolve().parents[1]
BRIDGE_EXE = ROOT / "native" / "namu_bridge" / "bin" / "Win32" / "Release" / "namu_bridge.exe"
BUILD_SCRIPT = ROOT / "native" / "namu_bridge" / "build.ps1"


class DesktopApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        load_dotenv_file(ROOT / ".env")
        self.title("APIF 나무 자동매매 컨트롤러")
        self.geometry("760x640")
        self.minsize(720, 560)
        self.configure(bg="#f3f5f7")

        settings = NamuQvSettings.from_env()
        self.qv_path = tk.StringVar(value=str(settings.module_path or ""))
        self.user_id = tk.StringVar(value=os.getenv("APIF_NAMU_USER_ID", ""))
        self.user_password = tk.StringVar()
        self.cert_password = tk.StringVar()
        self.symbol = tk.StringVar(value="005930")
        self.buy_price = tk.StringVar(value="70000")
        self.sell_price = tk.StringVar(value="75000")
        self.quantity = tk.StringVar(value="1")
        self.poll_seconds = tk.StringVar(value="3")
        self.status_text = tk.StringVar(value="준비됨")

        self._build_ui()

    def _build_ui(self) -> None:
        main = ttk.Frame(self, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        style = ttk.Style(self)
        style.configure("TButton", padding=(10, 6))
        style.configure("Status.TLabel", font=("Segoe UI", 10, "bold"))

        self._section(main, "연결 정보").grid(row=0, column=0, sticky="ew")
        connection = ttk.Frame(main)
        connection.grid(row=1, column=0, sticky="ew", pady=(6, 14))
        connection.columnconfigure(1, weight=1)

        self._row(connection, 0, "OpenAPI 폴더", self.qv_path, show=None)
        self._row(connection, 1, "HTS/OpenAPI 아이디", self.user_id, show=None)
        self._row(connection, 2, "HTS/OpenAPI 비밀번호", self.user_password, show="*")
        self._row(connection, 3, "인증서 비밀번호", self.cert_password, show="*")

        actions = ttk.Frame(main)
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        ttk.Button(actions, text="보조 프로그램 빌드", command=self.build_helper).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="DLL 확인", command=self.check_dll).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="현재가 조회", command=self.get_quote).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="모의 감시 실행", command=self.run_dry_monitor).pack(side=tk.LEFT)

        self._section(main, "매매 테스트").grid(row=3, column=0, sticky="ew")
        trading = ttk.Frame(main)
        trading.grid(row=4, column=0, sticky="ew", pady=(6, 14))
        trading.columnconfigure(1, weight=1)
        trading.columnconfigure(3, weight=1)

        self._small_row(trading, 0, 0, "종목코드", self.symbol)
        self._small_row(trading, 0, 2, "수량", self.quantity)
        self._small_row(trading, 1, 0, "매수가", self.buy_price)
        self._small_row(trading, 1, 2, "매도가", self.sell_price)
        self._small_row(trading, 2, 0, "조회 간격(초)", self.poll_seconds)

        status = ttk.Label(main, textvariable=self.status_text, style="Status.TLabel")
        status.grid(row=5, column=0, sticky="ew", pady=(0, 8))

        self.output = tk.Text(main, height=16, wrap=tk.WORD, borderwidth=1, relief=tk.SOLID)
        self.output.grid(row=6, column=0, sticky="nsew")
        main.rowconfigure(6, weight=1)
        main.columnconfigure(0, weight=1)

        self._log("컨트롤러가 열렸습니다. 비밀번호는 저장하지 않습니다.")

    def _section(self, parent: ttk.Frame, text: str) -> ttk.Label:
        return ttk.Label(parent, text=text, font=("Segoe UI", 12, "bold"))

    def _row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        show: str | None,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        entry = ttk.Entry(parent, textvariable=variable, show=show)
        entry.grid(row=row, column=1, sticky="ew", pady=4, padx=(10, 0))

    def _small_row(
        self,
        parent: ttk.Frame,
        row: int,
        column: int,
        label: str,
        variable: tk.StringVar,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=variable).grid(
            row=row, column=column + 1, sticky="ew", pady=4, padx=(10, 18)
        )

    def build_helper(self) -> None:
        self._run_background("보조 프로그램 빌드", self._build_helper)

    def check_dll(self) -> None:
        self._run_background("DLL 확인", lambda: self._bridge_request({"command": "ping"}))

    def get_quote(self) -> None:
        self._run_background(
            "현재가 조회",
            lambda: self._bridge_request(
                {"command": "quote", "symbol": self.symbol.get().strip()}
            ),
        )

    def run_dry_monitor(self) -> None:
        self._run_background("모의 감시 실행", self._run_dry_monitor)

    def _build_helper(self) -> str:
        result = subprocess.run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(BUILD_SCRIPT),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=self._env(),
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "빌드에 실패했습니다.")
        return "보조 프로그램 빌드가 완료되었습니다."

    def _bridge_request(self, payload: dict) -> str:
        if not BRIDGE_EXE.exists():
            self._build_helper()
        result = subprocess.run(
            [str(BRIDGE_EXE)],
            input=json.dumps(payload) + "\n",
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=self._env(),
            timeout=45,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or "보조 프로그램 실행에 실패했습니다.")
        line = result.stdout.strip()
        decoded = json.loads(line)
        if not decoded.get("ok"):
            raise RuntimeError(decoded.get("error", line))
        return line

    def _run_dry_monitor(self) -> str:
        settings = NamuQvSettings(
            module_path=Path(self.qv_path.get().strip()),
            account_no="",
            account_product_code="",
            bridge_command=str(BRIDGE_EXE),
            live_trading_enabled=False,
        )
        provider = NamuQvQuoteProvider(NamuQvSession(settings))
        plan = TradingPlan(
            symbol=self.symbol.get().strip(),
            name="",
            buy_price=int(self.buy_price.get()),
            sell_price=int(self.sell_price.get()),
            quantity=int(self.quantity.get()),
            poll_seconds=float(self.poll_seconds.get()),
        )
        engine = TradingEngine(
            plan=plan,
            price_provider=provider,
            broker=DryRunBroker(ROOT / "logs" / "desktop_orders.csv"),
        )
        messages = [engine.evaluate_once()]
        return "\n".join(messages)

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["APIF_NAMU_QV_PATH"] = self.qv_path.get().strip()
        env["APIF_NAMU_USER_ID"] = self.user_id.get().strip()
        env["APIF_NAMU_USER_PASSWORD"] = self.user_password.get()
        env["APIF_NAMU_CERT_PASSWORD"] = self.cert_password.get()
        env["APIF_ENABLE_LIVE_TRADING"] = "NO"
        return env

    def _run_background(self, label: str, action) -> None:
        self.status_text.set(f"{label} 중...")
        self._log(f"> {label}")

        def worker() -> None:
            try:
                result = action()
                self.after(0, lambda: self._complete(label, result))
            except Exception as exc:
                self.after(0, lambda: self._fail(label, exc))

        threading.Thread(target=worker, daemon=True).start()

    def _complete(self, label: str, result: str) -> None:
        self.status_text.set(f"{label} 완료")
        self._log(result)

    def _fail(self, label: str, exc: Exception) -> None:
        self.status_text.set(f"{label} 실패")
        self._log(f"오류: {exc}")
        messagebox.showerror(label, str(exc))

    def _log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.output.insert(tk.END, f"[{timestamp}] {message}\n")
        self.output.see(tk.END)


def main() -> None:
    app = DesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()
