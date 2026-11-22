# LV Forge Examples

This directory provides sample LabVIEW VIs and a quickstart script demonstrating all 4 LV Forge tools: `lv_inspect`, `lv_check`, `lv_diff`, and `lv_render`.

## Files Included

| File | Description |
| :--- | :--- |
| `Sample_Add.vi` | Simple LabVIEW VI taking a numeric array input and computing its sum with an Add loop. |
| `Sample_Multiply.vi` | Identical structure to `Sample_Add.vi`, but uses a Multiply function instead of Add. Ideal for testing semantic diffs. |
| `quickstart.py` | Python script that executes and displays the results of all 4 tools in sequence. |

---

## Running the Quickstart

Activate your virtual environment and run `quickstart.py`:

```powershell
.\.venv\Scripts\python.exe examples\quickstart.py
```

### Expected Output

```text
============================================================
LV Forge Quickstart Demo
============================================================

[1] Calling lv_inspect on Sample_Add.vi...
  SHA-256: 738b9021bec3aa718e7c3d03336ae742d1f04f6b075fb3ff40dda63971bb7278
  Connector Pane Terminals: ['Array', 'Numeric']

[2] Calling lv_diff between Sample_Add.vi and Sample_Multiply.vi...
  Semantic Diff Summary:
    + for:
    + Multiply(y=loop_108.shift0, x=Array) -> product
    - for:
    - Add(y=loop_43.shift0, x=Array) -> sum

[3] Calling lv_render on Sample_Add.vi...
  Generated SVG: C:\Users\...\AppData\Local\Temp\lv-forge-....svg

[4] Calling lv_check on Sample_Add.vi...
  LabVIEW Version: 20.0
  Execution State: idle
  Is Runnable:     True

============================================================
Quickstart completed successfully!
============================================================
```

---

## Using with an MCP Client (Claude Desktop, Cursor, Antigravity)

Point your MCP client directly to these sample files:
* To inspect: `lv_inspect(vi_path="<path-to-repo>/examples/Sample_Add.vi")`
* To diff: `lv_diff(before_vi="<path-to-repo>/examples/Sample_Add.vi", after_vi="<path-to-repo>/examples/Sample_Multiply.vi")`
* To check runnability: `lv_check(vi_path="<path-to-repo>/examples/Sample_Add.vi")`
* To render SVG: `lv_render(vi_path="<path-to-repo>/examples/Sample_Add.vi")`
