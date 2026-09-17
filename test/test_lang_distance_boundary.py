"""The language-distance boundary used to pick a dialog language."""
import unittest

from ovos_transcription_validator import TranscriptionValidatorPlugin

MACROLANGUAGE_PAIRS = [("arz", "ar"), ("wuu", "zh")]
REGIONAL_PAIRS = [("ar-SA", "ar"), ("en-AU", "en-GB"), ("pt-BR", "pt-PT")]
UNRELATED_PAIRS = [("en", "zh"), ("es", "fr"), ("fr-CH", "de-CH"), ("af", "nl")]


def _dialog(requested: str, available: str):
    plugin = TranscriptionValidatorPlugin.__new__(TranscriptionValidatorPlugin)
    plugin.dialogs = {"say_again": {available: ["please repeat"]}}
    return TranscriptionValidatorPlugin.get_dialog(plugin, "say_again", requested)


class TestGetDialogLangBoundary(unittest.TestCase):

    def test_macrolanguage_dialog_is_used(self):
        for member, macro in MACROLANGUAGE_PAIRS:
            with self.subTest(member=member):
                self.assertEqual(_dialog(member, macro), "please repeat")

    def test_regional_dialog_is_used(self):
        for requested, available in REGIONAL_PAIRS:
            with self.subTest(requested=requested):
                self.assertEqual(_dialog(requested, available), "please repeat")

    def test_unrelated_dialog_is_not_used(self):
        for requested, available in UNRELATED_PAIRS:
            with self.subTest(requested=requested):
                self.assertIsNone(_dialog(requested, available))


if __name__ == "__main__":
    unittest.main()
