"""Quickstart demo exercising all 4 LV Forge tools on sample VIs."""

import json
from pathlib import Path
import sys

# Ensure parent directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server

EXAMPLES_DIR = Path(__file__).resolve().parent
VI_ADD = EXAMPLES_DIR / "Sample_Add.vi"
VI_MULT = EXAMPLES_DIR / "Sample_Multiply.vi"


def main():
    print("=" * 60)
    print("LV Forge Quickstart Demo")
    print("=" * 60)

    # 1. lv_inspect
    print("\n[1] Calling lv_inspect on Sample_Add.vi...")
    inspect_res = server.lv_inspect(str(VI_ADD))
    print(f"  SHA-256: {inspect_res['disk_sha256']}")
    terminals = inspect_res["diagram"].get("connector_pane", {}).get("terminals", [])
    print(f"  Connector Pane Terminals: {[t.get('name') for t in terminals]}")

    # 2. lv_diff
    print("\n[2] Calling lv_diff between Sample_Add.vi and Sample_Multiply.vi...")
    diff_res = server.lv_diff(str(VI_ADD), str(VI_MULT))
    print("  Semantic Diff Summary:")
    diff_lines = [line for line in diff_res.splitlines() if line.strip()][:8]
    for line in diff_lines:
        print(f"    {line}")

    # 3. lv_render
    print("\n[3] Calling lv_render on Sample_Add.vi...")
    render_res = server.lv_render(str(VI_ADD))
    print(f"  Generated SVG: {render_res['svg_path']}")

    # 4. lv_check (requires running LabVIEW on Windows)
    if sys.platform == "win32":
        print("\n[4] Calling lv_check on Sample_Add.vi...")
        try:
            check_res = server.lv_check(str(VI_ADD), allow_com_activation=True)
            print(f"  LabVIEW Version: {check_res['labview_version']}")
            print(f"  Execution State: {check_res['execution_state']}")
            print(f"  Is Runnable:     {check_res['is_runnable']}")
        except Exception as exc:
            print(f"  ActiveX check skipped: {exc}")
    else:
        print("\n[4] lv_check skipped (Windows only).")

    print("\n" + "=" * 60)
    print("Quickstart completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
