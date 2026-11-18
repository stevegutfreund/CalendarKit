import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from calendarkit import env


class DotenvParsing(unittest.TestCase):
    def test_parse(self):
        text = """
        # comment
        A=1
        export B = two
        C="quoted # not a comment"
        D=value # trailing comment
        E=
        not a pair
        """
        self.assertEqual(env.parse_dotenv(text), {
            "A": "1", "B": "two", "C": "quoted # not a comment", "D": "value", "E": "",
        })

    def test_load_does_not_override_real_env(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"HL_X": "real"}, clear=False):
            p = Path(d) / ".env"
            p.write_text("HL_X=file\nHL_Y=file\n", encoding="utf-8")
            env.load_dotenv(p)
            self.assertEqual(os.environ["HL_X"], "real")
            self.assertEqual(os.environ["HL_Y"], "file")
            os.environ.pop("HL_Y")

    def test_missing_file_is_fine(self):
        self.assertEqual(env.load_dotenv("definitely/not/here/.env"), {})


class TypedGetters(unittest.TestCase):
    def test_getters(self):
        with mock.patch.dict(os.environ, {"HL_I": "42", "HL_B": "yes", "HL_E": "", "HL_P": "sub/t.json"}):
            self.assertEqual(env.get_int("HL_I", 1), 42)
            self.assertTrue(env.get_bool("HL_B"))
            self.assertEqual(env.get("HL_E", "dflt"), "dflt")
            self.assertEqual(env.get_path("HL_P", "x", base_dir="/base"), Path("/base/sub/t.json"))
            self.assertEqual(env.get_path("HL_NONE", "x.json", base_dir="/base"), Path("/base/x.json"))
            with self.assertRaises(env.MissingSettingError):
                env.require("HL_NONE")

    def test_bad_values(self):
        with mock.patch.dict(os.environ, {"HL_I": "x", "HL_B": "maybe"}):
            with self.assertRaises(ValueError):
                env.get_int("HL_I", 1)
            with self.assertRaises(ValueError):
                env.get_bool("HL_B")


if __name__ == "__main__":
    unittest.main()
