from pathlib import Path
from tempfile import TemporaryDirectory
import os
import unittest

from apif_bot.settings import NamuQvSettings, load_dotenv_file


class SettingsTest(unittest.TestCase):
    def test_loads_dotenv_without_overwriting_existing_env(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "APIF_NAMU_ACCOUNT_NO=11111111\n"
                "APIF_NAMU_ACCOUNT_PRODUCT_CODE=01\n",
                encoding="utf-8",
            )
            old_value = os.environ.get("APIF_NAMU_ACCOUNT_NO")
            os.environ["APIF_NAMU_ACCOUNT_NO"] = "already-set"
            try:
                load_dotenv_file(env_file)
                self.assertEqual(os.environ["APIF_NAMU_ACCOUNT_NO"], "already-set")
                self.assertEqual(os.environ["APIF_NAMU_ACCOUNT_PRODUCT_CODE"], "01")
            finally:
                if old_value is None:
                    os.environ.pop("APIF_NAMU_ACCOUNT_NO", None)
                else:
                    os.environ["APIF_NAMU_ACCOUNT_NO"] = old_value
                os.environ.pop("APIF_NAMU_ACCOUNT_PRODUCT_CODE", None)

    def test_missing_items_reports_required_namu_values(self) -> None:
        settings = NamuQvSettings(
            module_path=None,
            account_no="",
            account_product_code="",
            live_trading_enabled=False,
        )

        self.assertEqual(
            settings.missing_items(),
            [
                "APIF_NAMU_QV_PATH",
                "APIF_NAMU_ACCOUNT_NO",
                "APIF_NAMU_ACCOUNT_PRODUCT_CODE",
            ],
        )


if __name__ == "__main__":
    unittest.main()
