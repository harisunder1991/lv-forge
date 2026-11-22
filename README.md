# LV Forge

LV Forge is a standalone MCP server for reviewing LabVIEW VIs. It pairs offline diagram analysis through LVKit with a Windows ActiveX check for live IDE runnability. The first release targets LabVIEW 2020 32-bit on Windows.

| Tool | Result |
| --- | --- |
| `lv_inspect` | Saved diagram structure and file hash |
| `lv_check` | Live IDE execution state and runnability |
| `lv_diff` | Semantic differences between two saved VIs |
| `lv_render` | Path to a generated temporary SVG |

The server exposes inspection only. The live check may load a VI into the running IDE. If ActiveX attachment fails, the optional `allow_com_activation` argument lets COM connect to or start the registered LabVIEW version. Broken-wire counts and live unsaved-edit status are reported as unknown. Windows is required for the live check. The offline tools use [LVKit](https://github.com/pragmatest-dev/lvkit).

## Install locally

Use Python 3.11 or newer. In PowerShell, from this directory:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

For an MCP client that uses an `mcpServers` JSON configuration, replace `C:/path/to/lv-forge` with your checkout directory:

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

For a first check, ask your client to call `lv_inspect` on a saved sample VI, such as NI's `Creating New VI From Scratch.vi`. Pass its full path. Then start LabVIEW and ask for `lv_check` on the same file. If the IDE is already open but attach-only mode fails, try `allow_com_activation: true` if COM may open the registered LabVIEW version.

To review a wiring change, give `lv_diff` the paths of the two saved VIs as `before_vi` and `after_vi`. Use `lv_render` for an SVG view of either saved diagram.

## Quickstart & Examples

The repository includes ready-to-use sample VIs in the [`examples/`](examples/README.md) directory (`Sample_Add.vi` and `Sample_Multiply.vi`).

To run the automated demo that exercises all 4 tools in sequence:

```powershell
.\.venv\Scripts\python.exe examples\quickstart.py
```

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
