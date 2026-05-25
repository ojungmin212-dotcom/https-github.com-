from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import threading
import tkinter as tk
import tkinter.font as tkfont
from time import sleep
from tkinter import messagebox, ttk

from .broker import DryRunBroker
from .engine import TradingEngine
from .models import TradingPlan
from .namu_qv import NamuQvQuoteProvider, NamuQvSession
from .settings import NamuQvSettings, load_dotenv_file


ROOT = Path(__file__).resolve().parents[1]
BRIDGE_EXE = ROOT / "native" / "namu_bridge" / "bin" / "Win32" / "Release" / "namu_bridge.exe"
BUILD_SCRIPT = ROOT / "native" / "namu_bridge" / "build.ps1"
APP_TITLE = "오박사의 주식자동매매 대박 컨트롤러"
STOP_FILE = ROOT / "STOP_TRADING"


class DesktopApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        load_dotenv_file(ROOT / ".env")

        self.title(APP_TITLE)
        self.geometry("900x740")
        self.minsize(840, 660)
        self.configure(bg="#171717")
        self.title_font_family = self._pick_font(
            ["휴먼둥근헤드라인", "Arial Rounded MT Bold", "Malgun Gothic"]
        )

        settings = NamuQvSettings.from_env()
        self.qv_path = tk.StringVar(value=str(settings.module_path or ""))
        self.user_id = tk.StringVar(value=os.getenv("APIF_NAMU_USER_ID", ""))
        self.user_password = tk.StringVar()
        self.cert_password = tk.StringVar()
        self.symbol = tk.StringVar(value="005930")
        self.buy_price = tk.StringVar(value="70000")
        self.stop_loss_price = tk.StringVar(value="68000")
        self.sell_price = tk.StringVar(value="75000")
        self.quantity = tk.StringVar(value="1")
        self.poll_seconds = tk.StringVar(value="3")
        self.status_text = tk.StringVar(value="대기 중")
        self.dll_state = tk.StringVar(value="DLL: 미확인")
        self.login_state = tk.StringVar(value="로그인: 미확인")
        self.quote_state = tk.StringVar(value="현재가: 미조회")
        self.monitor_stop_event = threading.Event()

        self._configure_style()
        self._build_ui()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        self.option_add("*Font", ("Malgun Gothic", 10))

        style.configure(
            "Dark.TEntry",
            fieldbackground="#202020",
            background="#202020",
            foreground="#d9ffe7",
            insertcolor="#9cffbd",
            bordercolor="#3a3a3a",
            lightcolor="#4b4b4b",
            darkcolor="#101010",
            padding=(8, 7),
        )
        style.map(
            "Dark.TEntry",
            fieldbackground=[("focus", "#262626")],
            bordercolor=[("focus", "#6ee78a")],
        )
        style.configure(
            "Primary.TButton",
            font=("Malgun Gothic", 10, "bold"),
            padding=(16, 10),
            foreground="#07130b",
            background="#7cff9b",
            bordercolor="#2fbf62",
            lightcolor="#a7ffbc",
            darkcolor="#178c44",
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#a7ffbc"), ("pressed", "#2fbf62")],
        )
        style.configure(
            "Secondary.TButton",
            font=("Malgun Gothic", 10, "bold"),
            padding=(16, 10),
            foreground="#bdf7ca",
            background="#2a2a2a",
            bordercolor="#3f3f3f",
            lightcolor="#555555",
            darkcolor="#111111",
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#363636"), ("pressed", "#1f1f1f")],
        )

    def _build_ui(self) -> None:
        self._build_header()

        shell = tk.Frame(self, bg="#171717")
        shell.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(shell, bg="#171717", highlightthickness=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        page_scroll = ttk.Scrollbar(shell, orient=tk.VERTICAL, command=canvas.yview)
        page_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=page_scroll.set)

        main = tk.Frame(canvas, bg="#171717", padx=18, pady=16)
        main_window = canvas.create_window((0, 0), window=main, anchor="nw")
        main.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(main_window, width=event.width),
        )
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-event.delta / 120), "units"))
        main.columnconfigure(0, weight=1)
        main.rowconfigure(5, weight=1)

        connection_card = self._card(main)
        connection_card.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        connection_card.inner.columnconfigure(1, weight=1)
        self._card_title(connection_card.inner, "연결 정보", "나무 OpenAPI 로그인과 DLL 연결을 확인합니다.")
        self._row(connection_card.inner, 1, "OpenAPI 폴더", self.qv_path, show=None)
        self._row(connection_card.inner, 2, "HTS/OpenAPI 아이디", self.user_id, show=None)
        self._row(connection_card.inner, 3, "HTS/OpenAPI 비밀번호", self.user_password, show="*")
        self._row(connection_card.inner, 4, "인증서 비밀번호", self.cert_password, show="*")

        action_card = self._card(main)
        action_card.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        self._card_title(action_card.inner, "제어 버튼", "실제 주문은 아직 막아두고, 연결과 현재가만 테스트합니다.")
        actions = tk.Frame(action_card.inner, bg="#242424")
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 6))
        ttk.Button(actions, text="보조 프로그램 빌드", style="Secondary.TButton", command=self.build_helper).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(actions, text="DLL 확인", style="Secondary.TButton", command=self.check_dll).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(actions, text="로그인 확인", style="Secondary.TButton", command=self.check_login).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(actions, text="현재가 조회", style="Primary.TButton", command=self.get_quote).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(actions, text="감시 1회 점검", style="Primary.TButton", command=self.run_dry_monitor).pack(side=tk.LEFT)
        safety_actions = tk.Frame(action_card.inner, bg="#242424")
        safety_actions.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 2))
        ttk.Button(safety_actions, text="감시 시작", style="Primary.TButton", command=self.start_monitor).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(safety_actions, text="감시 중지", style="Secondary.TButton", command=self.stop_monitor).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(safety_actions, text="비상정지", style="Secondary.TButton", command=self.emergency_stop).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(safety_actions, text="비상정지 해제", style="Secondary.TButton", command=self.clear_emergency_stop).pack(side=tk.LEFT)

        status_card = self._card(main)
        status_card.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        status_card.inner.columnconfigure(0, weight=1)
        status_card.inner.columnconfigure(1, weight=1)
        status_card.inner.columnconfigure(2, weight=1)
        self._card_title(status_card.inner, "상태 표시", "로그인 성공 여부와 현재가를 바로 확인합니다.")
        self._status_value(status_card.inner, 1, 0, self.dll_state)
        self._status_value(status_card.inner, 1, 1, self.login_state)
        self._status_value(status_card.inner, 1, 2, self.quote_state)

        trading_card = self._card(main)
        trading_card.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        trading_card.inner.columnconfigure(1, weight=1)
        trading_card.inner.columnconfigure(3, weight=1)
        self._card_title(trading_card.inner, "매매 테스트", "정해둔 가격 조건으로 모의 주문만 기록합니다.")
        self._small_row(trading_card.inner, 1, 0, "종목코드", self.symbol)
        self._small_row(trading_card.inner, 1, 2, "수량", self.quantity)
        self._small_row(trading_card.inner, 2, 0, "매수가", self.buy_price)
        self._small_row(trading_card.inner, 2, 2, "손절가", self.stop_loss_price)
        self._small_row(trading_card.inner, 3, 0, "매도가", self.sell_price)
        self._small_row(trading_card.inner, 3, 2, "조회 간격(초)", self.poll_seconds)

        status_bar = tk.Frame(main, bg="#202020", highlightthickness=1, highlightbackground="#3a3a3a")
        status_bar.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        tk.Label(
            status_bar,
            textvariable=self.status_text,
            bg="#202020",
            fg="#8dffa8",
            font=("Malgun Gothic", 10, "bold"),
            padx=12,
            pady=9,
        ).pack(side=tk.LEFT)

        log_card = self._card(main)
        log_card.grid(row=5, column=0, sticky="nsew")
        log_card.inner.rowconfigure(1, weight=1)
        log_card.inner.columnconfigure(0, weight=1)
        self._card_title(log_card.inner, "실행 기록", "조회 결과와 오류 메시지가 여기에 표시됩니다.")
        log_body = tk.Frame(log_card.inner, bg="#111111")
        log_body.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        log_body.rowconfigure(0, weight=1)
        log_body.columnconfigure(0, weight=1)
        self.output = tk.Text(
            log_body,
            height=10,
            wrap=tk.WORD,
            borderwidth=0,
            relief=tk.FLAT,
            bg="#111111",
            fg="#c8ffd6",
            insertbackground="#c8ffd6",
            font=("Cascadia Mono", 10),
            padx=14,
            pady=12,
        )
        self.output.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_body, orient=tk.VERTICAL, command=self.output.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.output.configure(yscrollcommand=log_scroll.set)
        self._log("컨트롤러가 열렸습니다. 비밀번호는 저장하지 않습니다.")

    def _build_header(self) -> None:
        header = tk.Canvas(self, height=122, bg="#111111", highlightthickness=0)
        header.pack(fill=tk.X)
        header.create_rectangle(0, 0, 1200, 122, fill="#111111", outline="")
        header.create_rectangle(0, 86, 1200, 122, fill="#1b1b1b", outline="")
        header.create_rectangle(0, 0, 10, 122, fill="#7cff9b", outline="")
        header.create_text(
            36,
            36,
            anchor="w",
            text=APP_TITLE,
            fill="#9cffbd",
            font=(self.title_font_family, 22, "bold"),
        )
        header.create_text(
            38,
            74,
            anchor="w",
            text="현재가 조회와 모의 감시를 안전하게 제어합니다",
            fill="#74d68b",
            font=("Malgun Gothic", 10),
        )

    def _card(self, parent: tk.Widget) -> tk.Frame:
        outer = tk.Frame(parent, bg="#0f0f0f")
        inner = tk.Frame(
            outer,
            bg="#242424",
            padx=18,
            pady=16,
            highlightthickness=1,
            highlightbackground="#3a3a3a",
            highlightcolor="#3a3a3a",
        )
        inner.pack(fill=tk.BOTH, expand=True, padx=(0, 4), pady=(0, 4))
        outer.inner = inner  # type: ignore[attr-defined]
        return outer

    def _card_title(self, parent: tk.Frame, title: str, subtitle: str) -> None:
        tk.Label(
            parent,
            text=title,
            bg="#242424",
            fg="#b9ffca",
            font=("Malgun Gothic", 13, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            parent,
            text=subtitle,
            bg="#242424",
            fg="#7fdc94",
            font=("Malgun Gothic", 9),
        ).grid(row=0, column=1, sticky="e", padx=(16, 0))

    def _row(
        self,
        parent: tk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        show: str | None,
    ) -> None:
        tk.Label(
            parent,
            text=label,
            bg="#242424",
            fg="#d7ffe0",
            font=("Malgun Gothic", 10, "bold"),
        ).grid(row=row, column=0, sticky="w", pady=7)
        ttk.Entry(parent, textvariable=variable, show=show, style="Dark.TEntry").grid(
            row=row, column=1, sticky="ew", pady=7, padx=(14, 0)
        )

    def _small_row(
        self,
        parent: tk.Frame,
        row: int,
        column: int,
        label: str,
        variable: tk.StringVar,
    ) -> None:
        tk.Label(
            parent,
            text=label,
            bg="#242424",
            fg="#d7ffe0",
            font=("Malgun Gothic", 10, "bold"),
        ).grid(row=row, column=column, sticky="w", pady=7)
        ttk.Entry(parent, textvariable=variable, style="Dark.TEntry").grid(
            row=row, column=column + 1, sticky="ew", pady=7, padx=(12, 22)
        )

    def _status_value(self, parent: tk.Frame, row: int, column: int, variable: tk.StringVar) -> None:
        tk.Label(
            parent,
            textvariable=variable,
            bg="#1f2a22",
            fg="#a7ffbc",
            font=("Malgun Gothic", 11, "bold"),
            padx=12,
            pady=12,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#355c3d",
        ).grid(row=row, column=column, sticky="ew", pady=(12, 0), padx=(0 if column == 0 else 10, 0))

    def build_helper(self) -> None:
        self._run_background("보조 프로그램 빌드", self._build_helper)

    def check_dll(self) -> None:
        self._run_background("DLL 확인", self._check_dll)

    def check_login(self) -> None:
        self._run_background("로그인 확인", self._check_login)

    def get_quote(self) -> None:
        self._run_background("현재가 조회", self._get_quote)

    def run_dry_monitor(self) -> None:
        self._run_background("감시 1회 점검", self._run_dry_monitor)

    def start_monitor(self) -> None:
        if self.monitor_stop_event.is_set():
            self.monitor_stop_event.clear()
        self._run_background("실전 감시 시작", self._run_monitor_loop)

    def stop_monitor(self) -> None:
        self.monitor_stop_event.set()
        self.status_text.set("감시 중지 요청됨")
        self._log("감시 중지를 요청했습니다.")

    def emergency_stop(self) -> None:
        STOP_FILE.write_text("STOP", encoding="utf-8")
        self.monitor_stop_event.set()
        self.status_text.set("비상정지 활성화")
        self._log("비상정지 파일을 만들었습니다. 새 주문은 차단됩니다.")

    def clear_emergency_stop(self) -> None:
        STOP_FILE.unlink(missing_ok=True)
        self.status_text.set("비상정지 해제")
        self._log("비상정지를 해제했습니다.")

    def _build_helper(self) -> str:
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(BUILD_SCRIPT)],
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
        return json.dumps(self._bridge_request_dict(payload), ensure_ascii=False)

    def _bridge_request_dict(self, payload: dict) -> dict:
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
        return decoded

    def _check_dll(self) -> str:
        decoded = self._bridge_request_dict({"command": "ping"})
        status = decoded.get("data", {}).get("status", "")
        if status == "dll_loaded":
            self.after(0, lambda: self.dll_state.set("DLL: 정상 연결"))
            return "DLL 연결 확인 성공"
        raise RuntimeError(f"알 수 없는 DLL 상태: {decoded}")

    def _check_login(self) -> str:
        decoded = self._bridge_request_dict({"command": "login"})
        status = decoded.get("data", {}).get("status", "")
        if status == "login_ok":
            self.after(0, lambda: self.login_state.set("로그인: 성공"))
            return "로그인 확인 성공"
        raise RuntimeError(f"알 수 없는 로그인 상태: {decoded}")

    def _get_quote(self) -> str:
        symbol = self.symbol.get().strip()
        decoded = self._bridge_request_dict({"command": "quote", "symbol": symbol})
        data = decoded.get("data", {})
        price = int(data["price"])
        returned_symbol = str(data.get("symbol", symbol))
        self.after(0, lambda: self.login_state.set("로그인: 성공"))
        self.after(0, lambda: self.quote_state.set(f"현재가: {returned_symbol} / {price:,}원"))
        return f"현재가 조회 성공: {returned_symbol} {price:,}원"

    def _run_dry_monitor(self) -> str:
        engine = self._build_engine()
        return engine.evaluate_once()

    def _run_monitor_loop(self) -> str:
        self.monitor_stop_event.clear()
        engine = self._build_engine()
        tick_count = 0
        while not self.monitor_stop_event.is_set():
            tick_count += 1
            message = engine.evaluate_once()
            self.after(0, lambda msg=message: self._log(msg))
            if engine.status.state.value == "FINISHED":
                return "매수와 매도 조건 처리가 완료되어 감시를 멈췄습니다."
            sleep(max(float(self.poll_seconds.get()), 1.0))
        return f"감시를 중지했습니다. 확인 횟수: {tick_count}"

    def _build_engine(self) -> TradingEngine:
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
            stop_loss_price=(
                int(self.stop_loss_price.get())
                if self.stop_loss_price.get().strip()
                else None
            ),
            sell_price=int(self.sell_price.get()),
            quantity=int(self.quantity.get()),
            poll_seconds=float(self.poll_seconds.get()),
        )
        engine = TradingEngine(
            plan=plan,
            price_provider=provider,
            broker=DryRunBroker(ROOT / "logs" / "desktop_orders.csv"),
        )
        return engine

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

    @staticmethod
    def _pick_font(candidates: list[str]) -> str:
        available = set(tkfont.families())
        for candidate in candidates:
            if candidate in available:
                return candidate
        return "Malgun Gothic"


def main() -> None:
    app = DesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()
