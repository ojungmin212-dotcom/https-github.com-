from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from .settings import NamuQvSettings, load_dotenv_file, python_architecture


def main() -> None:
    load_dotenv_file()
    checks = [
        ("Git installed", _git_installed()),
        ("Git repository", _git_repository()),
        ("GitHub remote", _github_remote()),
        ("STOP_TRADING absent", not Path("STOP_TRADING").exists()),
    ]
    settings = NamuQvSettings.from_env()
    missing = settings.missing_items()
    wmca_arch = settings.wmca_architecture()
    py_arch = python_architecture()
    checks.append(("Namu QV settings", not missing))
    checks.append(("wmca.dll found", settings.wmca_dll_path().exists()))
    checks.append(
        (
            "Direct Python DLL architecture match",
            wmca_arch is None or wmca_arch == py_arch,
        )
    )
    checks.append(("Live trading disabled", not settings.live_trading_enabled))

    print("APIF readiness check")
    print("====================")
    for label, ok in checks:
        marker = "OK" if ok else "CHECK"
        print(f"[{marker}] {label}")

    if missing:
        print("")
        print("Missing or incomplete Namu settings:")
        for item in missing:
            print(f"- {item}")

    print("")
    print(f"Python architecture: {py_arch}")
    print(f"wmca.dll path: {settings.wmca_dll_path()}")
    print(f"wmca.dll architecture: {wmca_arch or 'not found'}")
    if wmca_arch and wmca_arch != py_arch:
        print(
            "Direct DLL loading is not compatible. Use 32-bit Python or a "
            "32-bit helper process for the Namu API bridge."
        )

    print("")
    if settings.live_trading_enabled:
        print("Live trading flag is YES. Use this only after mock trading is verified.")
    else:
        print("Live trading is disabled. This is the recommended state for now.")


def _git_installed() -> bool:
    return shutil.which("git") is not None


def _git_repository() -> bool:
    return _command_ok(["git", "rev-parse", "--is-inside-work-tree"])


def _github_remote() -> bool:
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and "github.com" in result.stdout.lower()


def _command_ok(command: list[str]) -> bool:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return result.returncode == 0


if __name__ == "__main__":
    main()
