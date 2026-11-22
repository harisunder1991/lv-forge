from pathlib import Path
from subprocess import CompletedProcess
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
            parsed = server.LVKitResult('{"nodes": []}', [], [])
            with patch("server.lvkit", return_value=parsed) as describe:
                result = server.lv_inspect(str(sample))
            describe.assert_called_once_with("describe", "--format", "json", str(sample))
            self.assertEqual(result["diagram"], {"nodes": []})
            self.assertFalse(result["partial_analysis"])
            self.assertEqual(
                result["disk_sha256"],
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            )

    def test_lvkit_preserves_exit_zero_parse_warnings(self):
        notice = "lvkit: auto-detected LabVIEW 20.0.0 vi.lib"
        warning = "Sample.vi: Warning: Block section size does not match parsed size"
        process = CompletedProcess([], 0, "usable output", f"{notice}\n{warning}\n")
        with patch("server.subprocess.run", return_value=process):
            result = server.lvkit("describe", "Sample.vi")
        self.assertEqual(result.stdout, "usable output")
        self.assertEqual(result.warnings, [warning])
        self.assertEqual(result.notices, [notice])
        self.assertTrue(result.diagnostics()["partial_analysis"])

    def test_exit_three_is_partial_even_without_stderr(self):
        with patch("server.subprocess.run", return_value=CompletedProcess([], 3, "usable", "")):
            result = server.lvkit("describe", "Sample.vi")
        self.assertEqual(result.stdout, "usable")
        self.assertTrue(result.diagnostics()["partial_analysis"])

    def test_fatal_lvkit_exit_is_an_error(self):
        with patch("server.subprocess.run", return_value=CompletedProcess([], 1, "", "read failed")):
            with self.assertRaisesRegex(ToolError, "read failed"):
                server.lvkit("describe", "Sample.vi")

    def test_report_embeds_diagram_and_escapes_partial_diagnostics(self):
        with tempfile.TemporaryDirectory() as folder:
            sample = Path(folder) / "sample.vi"
            sample.touch()
            parsed = server.LVKitResult(
                '{"properties":{"lv_version":"20.0.0"},"components":[{"name":"Helper.vi"}]}',
                ["Warning: <unparsed>"],
                [],
            )

            def fake_lvkit(command, *args):
                if command == "describe":
                    return parsed
                Path(args[-1]).write_bytes(b"<svg></svg>")
                return server.LVKitResult("", [], [])

            with patch("server.lvkit", side_effect=fake_lvkit):
                result = server.lv_report(str(sample))
            report = Path(result["report_path"])
            self.addCleanup(report.unlink, missing_ok=True)
            html = report.read_text(encoding="utf-8")
            self.assertTrue(result["partial_analysis"])
            self.assertEqual(result["saved_labview_version"], "20.0.0")
            self.assertIn("Warning: &lt;unparsed&gt;", html)
            self.assertIn("Helper.vi", html)
            self.assertIn("data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=", html)
            self.assertIn(result["disk_sha256"], html)

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
