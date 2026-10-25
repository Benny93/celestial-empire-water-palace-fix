# Celestial Empire — Water Palace save repair

A small, offline Python tool for one specific problem: a Water Palace stuck at **Advanced Tools 0/20**, with its delivery button unable to resume, because its linked altar is missing the resource entry.

**Delivery recovery was confirmed in-game on one player's save.** A more recent save from that same city also passed structural validation. Broader compatibility and completed-monument progression have not been confirmed. This is an unofficial community tool, not a general save editor.

## What it changes

The tool locates the Water Palace by its building tag and finds the altar whose monument address matches the palace's first occupied cell. It adds only:

| Map | Key | Added value |
|---|---|---|
| Altar `GatheringResource` | `AdvancedTool` | `true` |
| Altar inventory `OwnedResources` | `AdvancedTool` | `0.0` |

The spelling is **`AdvancedTool`, singular**. `AdvancedTools` appears elsewhere in quest/UI data but is not this inventory identifier. An initial private patch used the plural spelling and failed; the corrected singular key restored deliveries.

Existing resources (including `Duck`), city stock, other buildings, and construction/progression flags are preserved. It does not grant tools or force monument completion. The game handles deliveries and subsequent construction.

## Requirements and supported scope

- Python **3.9 or newer**, standard library only. No downloads or network requests at runtime.
- The observed chunked zlib save format, with exactly one identifiable Water Palace and one linked altar.
- `MonumentStage = 0`, construction state `CollectingResoures`, and `AdvancedTool` missing from **both** altar maps.
- The real singular key must already exist in the resource manager's inventory.

The game build used for the successful test was not recorded. Compatibility is checked from file structure and state, not a claimed game-version range. Unsupported states are refused, including already-patched saves, entries missing from only one map, and altar maps containing the obsolete plural-key patch. Use an untouched original in those cases; do not remove keys manually.

The historical cause is not proven. Missing saved entries were observed in an older city and restoring them resolved delivery; that does not prove a particular update caused the problem.

## Usage on Windows

Download or clone this repository, open PowerShell in its folder, and **exit the game**. Work on a copy of the relevant save. Keep a separate backup of the entire slot, including `Player.sav` and `Slot.sav`.

Inspect without writing any files:

```powershell
py -3 -m water_palace "C:\path\to\Level.sav"
```

Create a separate repaired save:

```powershell
py -3 -m water_palace "C:\path\to\Level.sav" --output "C:\path\to\Level_WaterPalace_Fixed.sav"
```

If your installation uses `python` instead of `py -3`, substitute that command. Run from this repository's root directory; installation with pip is unnecessary.

The command writes the repaired file, an exact input backup named `Level_WaterPalace_Fixed.sav.original.bak`, and a `.sav.report.json` validation report beside it. It refuses existing output/backup/report paths. It never edits the input or installs the result into the game. Checks remain active even with Python optimization enabled. A failed run may leave partial output artifacts; never install an output from a failed run.

### Install and test

1. With the game closed, back up the entire matching slot under `%LOCALAPPDATA%\CelestialEmpire\Saved\SaveGames\Users`.
2. Replace only that slot's `Level.sav` with the successfully generated file, renaming it to `Level.sav`. Retain its matching Player/Slot files.
3. Relaunch, load the correct slot, and resume simulation. Confirm the previous resource counts remain intact and Advanced Tools deliveries resume. Try its delivery toggle if necessary.
4. Let the game finish construction, then save into a separate slot and reload to check progression. If loading or behavior fails, close the game and restore your slot backup.

## Validation

Before returning output, the tool checks decompression/recompression, parses the target maps again, and compares all unchanged byte ranges. Other actors, existing map entries, other altar properties/components and trailing level data must remain byte-for-byte unchanged. A report includes hashes and an exact edit list.

Static checks establish structure and edit scope, **not game acceptance or successful progression**. Parsing is deliberately limited to the observed format; opaque unrelated bytes are preserved.

Run the self-contained tests (no game files needed):

```powershell
py -3 -m unittest discover -s tests -v
```

## Reporting a problem

See [CONTRIBUTING.md](CONTRIBUTING.md). Do not post your city save or an entire user-directory archive publicly by default. Saves and reports are ignored by Git. Review reports before sharing; they contain object identifiers, hashes and resource values, though the tool does not add your local input path to them.

Technical details are in [docs/format.md](docs/format.md). Released under the [MIT license](LICENSE). No game assets or private saves are included. This project is not affiliated with the game developers.
