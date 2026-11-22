from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from mcp.server.mcpserver.exceptions import ToolError

import server


class ReviewTests(unittest.TestCase):
    def test_rejects_missing_vi(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ToolError, "Expected a saved .vi file"):
                server.lv_inspect(str(Path(folder) / "missing.vi"))

    def test_inspect_reports_saved_file_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            sample = Path(folder) / "sample.vi"
            sample.write_bytes(b"abc")
            with patch("server.lvkit", return_value='{"nodes": []}') as describe:
                result = server.lv_inspect(str(sample))
            describe.assert_called_once_with("describe", "--format", "json", str(sample))
            self.assertEqual(result["diagram"], {"nodes": []})
            self.assertEqual(
                result["disk_sha256"],
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            )

    @unittest.skipUnless(sys.platform == "win32", "LabVIEW COM is Windows-only")
    def test_live_states(self):
        with tempfile.TemporaryDirectory() as folder:
            sample = Path(folder) / "sample.vi"
            sample.touch()
            with patch("win32com.client.GetActiveObject") as active:
                app = active.return_value
                app.Version = "20.0"
                vi = app.GetVIReference.return_value
                for state, expected in [(0, False), (1, True), (99, None)]:
                    with self.subTest(state=state):
                        vi.ExecState = state
                        result = server.lv_check(str(sample))
                        self.assertIs(result["is_runnable"], expected)
                        self.assertIsNone(result["broken_wire_count"])
                        self.assertIsNone(result["has_unsaved_changes"])
                vi.Run.assert_not_called()

    @unittest.skipUnless(sys.platform == "win32", "LabVIEW COM is Windows-only")
    def test_activation_requires_opt_in(self):
        import pythoncom

        with tempfile.TemporaryDirectory() as folder:
            sample = Path(folder) / "sample.vi"
            sample.touch()
            with (
                patch("win32com.client.GetActiveObject", side_effect=pythoncom.com_error),
                patch("win32com.client.Dispatch") as dispatch,
            ):
                with self.assertRaisesRegex(ToolError, "Could not attach"):
                    server.lv_check(str(sample))
                dispatch.assert_not_called()
                app = dispatch.return_value
                app.Version = "20.0"
                app.GetVIReference.return_value.ExecState = 1
                self.assertTrue(server.lv_check(str(sample), allow_com_activation=True)["is_runnable"])
                dispatch.assert_called_once_with("LabVIEW.Application")


if __name__ == "__main__":
    unittest.main()
