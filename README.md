# arrow

A small daemon that turns an Elgato Stream Deck into a physical control panel
for a home automation orchestrator. Button presses are mapped to HTTP calls
against an internal orchestrator host; the deck dims itself when idle and
brightens on the next press.

## What it does

- Enumerates the first attached Stream Deck and uploads icons to its keys.
- Maps keys to two kinds of action:
  - **Room buttons** — `(room, on|off|follow)` calls to `/api/room/{room}?state={state}`.
  - **Routine buttons** — named routines via `/api/console/{routine}`.
- While a call is in flight, blanks the other keys and plays a per-action
  countdown GIF on the pressed key; restores the icon set when the call
  returns.
- Reserves key position 31 as a help/labels toggle: pressing it swaps the
  plain icons for label-overlay versions (and back).
- Starts dim. The first press of any key wakes the deck to full brightness
  and schedules a re-dim after 15 seconds of inactivity (replaces any
  pending re-dim job, so activity keeps the deck awake).
- Runs forever until interrupted, then shuts the scheduler down and closes the
  device.

## Layout

```
src/arrow/
  __init__.py   constants: button map, routine map, icon paths, orchestrator URL
  runner.py     entry point (`arrow` console script) — opens deck, starts scheduler
  api.py        key callback, brightness state, icon upload
  dal.py        HTTP calls to the orchestrator
  icons/        PNGs uploaded to the deck keys
scripts/
  make_icons.py icon generation helper
```

Key map and routine map live in `src/arrow/__init__.py`. The orchestrator base
URL (`ORC_BASE_URL`) is configured there too.

## Install / run

Requires Python and a Stream Deck attached via USB. The `streamdeck` library
needs hidapi available on the host.

```sh
pip install .
arrow
```

## Build and deploy

`make.sh` builds a wheel and uploads it to an internal package registry.
`install.sh` is shipped to the deploy host over ssh by `build-and-deploy.sh`,
which stops the supervised `arrow` service, reinstalls the wheel, and starts
it again.

```sh
./build-and-deploy.sh
```

These scripts hard-code internal hostnames (`registry.int.exussum.org`,
`arrow.int.exussum.org`) and assume a `.venv-arrow` virtualenv plus a
`supervisord` job named `arrow` on the target.

## License

GPL-2.0-or-later. See [LICENSE](LICENSE).
