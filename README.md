# LV Forge

LV Forge brings LabVIEW VI review into an MCP client. Use it to trace the wiring in a saved block diagram, compare two revisions of a VI, or ask the LabVIEW IDE whether a VI is runnable.

## Capabilities

| Tool | Use it to | Source |
| --- | --- | --- |
| `lv_inspect` | Inspect nodes, wiring, and connector pane terminals. The result includes the saved file's SHA-256 hash. | Saved VI |
| `lv_diff` | Compare two saved VIs for changes in diagram structure and dataflow. | Two saved VIs |
| `lv_render` | Generate a temporary SVG of a block diagram. | Saved VI |
| `lv_check` | Read the execution state and runnability reported by the IDE. | Live LabVIEW IDE |
| `lv_report` | Generate a self-contained HTML inspection report with the VI hash, saved version, diagram, and diagnostics. | Saved VI, with an optional live IDE check |

The offline tools use [LVKit](https://github.com/pragmatest-dev/lvkit) and can work without a running IDE. The live check uses Windows ActiveX and has been verified with **LabVIEW 2020 32-bit**. It may load the VI into the IDE. It never executes or saves the VI. Exact broken-wire counts and unsaved-edit status are reported as unknown.

Offline results include `warnings`, `notices`, and a `partial_analysis` flag. LV Forge uses a fresh temporary LVKit cache for each call so cached results do not suppress parser warnings. It preserves usable partial output and surfaces warnings even when LVKit exits successfully. Inspect the warnings before relying on a diagram or diff. The `lv_diff` result contains its text in the `diff` field.

## Install

Use Python 3.11 or newer. Run these commands in PowerShell:

```powershell
git clone https://github.com/harisunder1991/lv-forge.git
cd lv-forge
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Try the bundled examples

Run this from the repository root:

```powershell
.\.venv\Scripts\python.exe examples\quickstart.py
```

The demo inspects the array-sum VI, compares it with the array-product VI, and prints the path to an SVG. It runs offline by default. To try the live check, start LabVIEW and add `--live`. See the [example guide](examples/README.md) for the opt-in COM activation option and expected results.

## Connect your MCP client

For clients that accept an `mcpServers` JSON configuration, replace `C:/path/to/lv-forge` with the full path to your checkout. The client launches LV Forge over stdio.

```json
{
  "mcpServers": {
    "lv-forge": {
      "command": "C:/path/to/lv-forge/.venv/Scripts/python.exe",
      "args": ["C:/path/to/lv-forge/server.py"]
    }
  }
}
```

Give your client the absolute paths to the VIs you want to review. For example, ask it to compare `examples/Sample_Add.vi` and `examples/Sample_Multiply.vi`, then explain the change inside the loop.

If the offline diagram differs from what you see in LabVIEW, check whether your edits have been saved. If `lv_check` cannot attach, open LabVIEW and retry. You can pass `allow_com_activation: true` when COM may launch the registered LabVIEW version.

## Save a VI inspection report

Ask the MCP client to call `lv_report` with the absolute path to a saved VI. Open the returned `report_path` in a browser and copy the HTML out of the temporary folder if you want to retain it. It includes a UTC timestamp, the saved LabVIEW version when available, detected inputs and outputs, named SubVI calls, the embedded SVG, and any analysis warnings.

Set `include_live_check: true` to add the IDE's runnability result in a separate section. The report records inspection evidence. Keep functional test results with it when documenting validation.

## Contributing

Useful first contributions include testing the live check across LabVIEW versions and adding reproducible fixture cases for diagram inspection. In bug reports, include Windows and Python versions, LabVIEW version and bitness, the tool and arguments used, and a minimal example you have permission to share.

Run the unit tests from the checkout with `.\.venv\Scripts\python.exe -m unittest discover -s tests`. The tests mock the LabVIEW connection. They do not require opening or running a VI.

## Credits

Harisunder Chidambaram created LV Forge's standalone MCP integration. LV Forge provides the tool interface, input validation, result reporting, and the live Windows LabVIEW check.

OpenAI Codex (ChatGPT's coding agent) helped implement, test, and package the standalone release. Google Antigravity helped investigate and verify LabVIEW 2020 VI Scripting and compatibility in the earlier internal prototype.

- [PragmaTest and the LVKit contributors](https://github.com/pragmatest-dev/lvkit) provide the offline VI analysis, diff, and renderer through the LVKit dependency.
- The [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) provides the MCP server interface. [pywin32](https://github.com/mhammond/pywin32) provides access to Windows COM automation.
- [Jan Göbel (CalmyJane)](https://github.com/CalmyJane/labview_assistant) created LabVIEW Assistant, which was evaluated during earlier development. The standalone server does not include its code or VIs.
- [National Instruments](https://www.ni.com/) provides LabVIEW, its ActiveX interface, and the installed examples used for verification.

LV Forge is distributed under the [MIT License](LICENSE).
