# LV Forge examples

These two saved VIs show how LV Forge reviews a small change in LabVIEW dataflow.

| File | Diagram |
| --- | --- |
| `Sample_Add.vi` | Sums a numeric array with an Add node and a shift register initialized to `0.0`. |
| `Sample_Multiply.vi` | Multiplies the array elements with a Multiply node and a shift register initialized to `1.0`. |

## Case and SubVI fixtures

These saved VIs are from the [LabVIEW Open Source Project's LV-MQTT-Broker](https://github.com/LabVIEW-Open-Source/LV-MQTT-Broker/tree/01aa7848b707cb5ac609e8d27fc6ae94b51d65d0/source/TopicFilter) at commit `01aa7848b707cb5ac609e8d27fc6ae94b51d65d0`. The binary examples are unchanged and retain their [0BSD license](mqtt-topic-filter/LICENSE). They are intended for offline inspection, SVG rendering, and report reproduction. For IDE execution or dependency resolution, use the full upstream project.

| File | What to check with `lv_inspect` or `lv_report` |
| --- | --- |
| [Create TopicFilter.vi](mqtt-topic-filter/Create%20TopicFilter.vi) | The diagram includes a Case Structure with `No Error` and `Error` frames, plus nested cases. |
| [Evaluate.vi](mqtt-topic-filter/Evaluate.vi) | The detected SubVI list includes `Read Topic Filter.vi`. The wildcard Case Structure includes `#`, `+`, and the default frame. |
| [Read Topic Filter.vi](mqtt-topic-filter/Read%20Topic%20Filter.vi) | The accessor called by `Evaluate.vi`, included for separate inspection. |

## Run the demo

From the repository root, after installing the [Python dependencies](../README.md#install):

```powershell
.\.venv\Scripts\python.exe examples\quickstart.py
```

The script calls the same Python functions used by the MCP tools. It prints the Add VI's SHA-256 hash and connector pane terminals, shows the semantic diff, and prints the path to a temporary SVG. Look for the removed `Add` node and added `Multiply` node in the diff. The default demo reads the saved files and generates the SVG without opening LabVIEW.

LVKit can report partial extraction on these examples, including a warning about the `VITS` block. The demo displays that warning alongside the diagram data LVKit was able to extract.

### Optional live check

On Windows, start LabVIEW and add `--live` to check the Add VI's runnability. Use the second command only if you want COM to be able to launch the registered LabVIEW version when attachment fails.

```powershell
.\.venv\Scripts\python.exe examples\quickstart.py --live
.\.venv\Scripts\python.exe examples\quickstart.py --live --allow-com-activation
```

The live check can load the VI into the IDE without executing it. The demo exits with status `3` for partial offline analysis, or status `1` if a requested check fails or runnability cannot be confirmed.

## Try the same files through MCP

After [connecting an MCP client](../README.md#connect-your-mcp-client), give the client the absolute paths of the two sample VIs. For example, ask it to compare the saved diagrams and render the Add VI to SVG. The client can use `lv_diff` and `lv_render` for those requests.
