# arrow

A small daemon that turns an Elgato Stream Deck into a physical control panel
for a home automation orchestrator. Button presses are mapped to HTTP calls
against an internal orchestrator host; the deck dims itself when idle and
brightens on the next press.

## What it does

- Enumerates the first attached Stream Deck and uploads icons to its keys.
- Maps keys to two kinds of action:
  - **Room buttons** — `{slug}_{action}` routine calls to `/api/run/{routine}`.
  - **Routine buttons** — named routines via `/api/run/{routine}`.
- While a call is in flight, blanks the other keys and plays a per-action
  countdown GIF on the pressed key; restores the icon set when the call
  returns.
- Reserves key 7 as a presence check-in button and key 31 as a
  help/labels toggle: pressing it swaps the plain icons for label-overlay
  versions (and back).
- Starts dim. The first press of any key wakes the deck to full brightness
  and schedules a re-dim after 15 seconds of inactivity.
- Runs forever until interrupted, then closes the device.

## Layout

```
src/arrow/
  __init__.py   constants: button map, routine map, icon paths, orchestrator URL
  runner.py     entry point (`arrow` console script) — opens deck, starts loop
  api.py        key callback, brightness state, icon upload
  dal.py        HTTP calls to the orchestrator
  img.py        image helpers (icon rendering, label overlays)
  models.py     Button, Routine, Other dataclasses
  icons/        PNGs and GIFs uploaded to the deck keys
scripts/
  make_icons.py       icon generation helper
  make_countdowns.py  countdown GIF generation helper
  upload.sh           build wheel and push to internal registry
  install.sh          remote install script (run via ssh)
  build-and-install.sh  upload + ssh deploy in one step
  run-tests.sh        run pytest
```

Key map and routine map live in `src/arrow/__init__.py`. The orchestrator base
URL (`ORC_BASE_URL`) is configured there too.

## Install / run

Requires Python ≥ 3.11 and a Stream Deck attached via USB. The `streamdeck`
library needs hidapi available on the host.

```sh
pip install .
arrow
```

## Build and deploy

`scripts/upload.sh` checks for uncommitted changes, builds a wheel with `uv`,
and uploads it to an internal package registry.

`scripts/install.sh` is the remote-side install script: it swaps the wheel
via `pip` and restarts the supervised `arrow` service.

`scripts/build-and-install.sh` runs both in sequence — upload then ssh deploy.

```sh
sh scripts/build-and-install.sh
```

These scripts hard-code internal hostnames (`registry.int.exussum.org`,
`arrow.int.exussum.org`) and assume a `uv`-managed virtualenv at
`/root/.venv-arrow` and a `supervisord` job named `arrow` on the target.

## License

GPL-2.0-or-later. See [LICENSE](LICENSE).
