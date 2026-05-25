from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from apif_bot.settings import NamuQvSettings, pe_architecture


class DoctorSettingsTest(unittest.TestCase):
    def test_wmca_dll_path_uses_module_bin_folder(self) -> None:
        settings = NamuQvSettings(
            module_path=Path("C:/openapi.nm"),
            account_no="123",
            account_product_code="01",
            bridge_command="bridge.exe",
            live_trading_enabled=False,
        )

        self.assertEqual(settings.wmca_dll_path(), Path("C:/openapi.nm/bin/wmca.dll"))

    def test_missing_items_requires_wmca_dll_inside_module_path(self) -> None:
        with TemporaryDirectory() as temp_dir:
            settings = NamuQvSettings(
                module_path=Path(temp_dir),
                account_no="123",
                account_product_code="01",
                bridge_command="bridge.exe",
                live_trading_enabled=False,
            )

            self.assertEqual(
                settings.missing_items(),
                ["APIF_NAMU_QV_PATH does not contain bin/wmca.dll"],
            )

    def test_pe_architecture_detects_x86_header(self) -> None:
        with TemporaryDirectory() as temp_dir:
            dll_path = Path(temp_dir) / "fake.dll"
            data = bytearray(256)
            data[0:2] = b"MZ"
            data[0x3C:0x40] = (0x80).to_bytes(4, "little")
            data[0x80:0x84] = b"PE\0\0"
            data[0x84:0x86] = (0x14C).to_bytes(2, "little")
            dll_path.write_bytes(data)

            self.assertEqual(pe_architecture(dll_path), "x86")


if __name__ == "__main__":
    unittest.main()
