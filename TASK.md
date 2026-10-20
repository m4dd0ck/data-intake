# Tasks

Single-repo status. Last reviewed **2026-10-20**. Cross-repo items are in
`~/developer/hq/OPEN_ITEMS.md`.

## Needs the owner

Nothing.

## Queue

- [ ] The audit summary line prints "1 notes" and "1 warnings"; pluralise in
      `src/data_intake/cli.py` (hq inventory, 2026-10-07).
- [ ] `UnsupportedFileError` is reachable only through a direct `load_file` call, since
      `load_folder` filters by suffix first and the CLI does not catch it; either wire it up or
      drop it (hq inventory, 2026-10-07).
