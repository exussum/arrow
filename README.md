# arrow

arrow turns an Elgato Stream Deck into a control panel for
[orc](https://github.com/exussum/orc), a home automation orchestrator. A key
press becomes an HTTP call to orc; the deck dims when idle and wakes on the
next press.

Everything on the deck comes from one config file: which key does what,
which emoji it shows, and which orc action it calls. arrow generates the
icons from that file, so there is nothing to draw.

## What it does

- Uploads an icon to every configured key and listens for presses.
- Calls orc: `/api/room/{room}?state=` for room keys, `/api/run/{id}` for
  routines, and `/api/presence/{name}/checkin` for the check-in key.
- Plays a countdown on the pressed key while the call is in flight, sized
  from orc's own measured average for that action.
- Announces and flags actions orc will delay, through `/api/announce`.
- Toggles label overlays on the help key, so you can see what each key does.
- Starts dim, wakes on the first press, and dims again after an idle
  timeout.

## Install and run

You need:

- Python 3.14 and [uv](https://docs.astral.sh/uv/).
- A Stream Deck on USB. The `streamdeck` library needs hidapi on the host:
  `brew install hidapi` on macOS, or `sudo apt-get install libhidapi-libusb0`
  on Debian and Ubuntu.
- An orc you can reach over HTTP. `arrow package` reads orc's `/api/actions`
  for the countdown lengths.

Install arrow, generate the icons, and start the daemon. The example config
in [`examples/config.arrow`](examples/config.arrow) is complete; copy it and
point `orc_base_url` at your orc.

```sh
git clone https://github.com/exussum/arrow.git && cd arrow
uv sync
uv run arrow package --config /etc/arrow/config.arrow   # writes /etc/arrow/icons.zip
uv run arrow --config /etc/arrow/config.arrow
```

Point arrow at the file with `--config` or `ARROW_CONFIG`. The generated
`icons.zip` lives beside it. On startup the daemon refuses to run if the
zip is missing anything it needs, and reports, without stopping, any room,
routine, or person that orc doesn't know. The fonts it renders with are
bundled, so it needs nothing else installed.

## Configure

Each line of the config is a command:

```
setting orc_base_url  ${ARROW_ORC_URL:-https://orc.exussum.example}
setting presence_name someone

badge on     electric-light-bulb
badge off    electric-light-bulb:dim
badge follow pushpin

room garden Garden fork-and-knife-with-plate

routine single  cat   Cat   cat
routine pair    reset Reset electric-light-bulb:dim speaker-with-cancellation-stroke --orc-id=ROUTINE_RESET

other help     Help       black-question-mark-ornament
other presence 'Check In' happy-person-raising-one-hand

button garden on  8
button cat        29
button presence    7
button help       31
```

- A **`room`** line expands to three keys, one per orc state (`on`, `off`,
  `follow`). The state supplies the badge, the label suffix, and the
  `?state=` value, so a room needs one `button` line per state.
- A **`routine`** line takes a layout word that fixes what follows:
  `single` (one icon), `pair` (two icons, opposite corners), `caption`
  (icon plus text), or `marked` (icon plus badge).
- **`--orc-id`** defaults to `AD_HOC_<SLUG>`. Name it explicitly for
  anything that breaks the convention, including orc plugin names.
- **Icons** are Unicode character names, lowercased and hyphenated. Append
  `:dim` or `:invert` to filter one glyph. `arrow icons search` finds a
  name; `arrow icons name` converts a pasted emoji.
- **`help`** and **`presence`** are reserved: each needs an `other` line
  and a `button` line.

## Commands

| Command                      | Does                                 |
| ---------------------------- | ------------------------------------ |
| `arrow`                      | Run the daemon                       |
| `arrow package [out]`        | Generate the icons into a zip        |
| `arrow icons search WORD...` | Find an emoji name for the config    |
| `arrow icons name EMOJI...`  | Convert pasted emoji to config names |

`--config` and `--icons` work with all of them.

## Developing

Run the tests with `uv run --extra test pytest`, or `pre-commit run
--all-files` for the full lint, type, audit, and test suite.

```
src/arrow/
  runner.py          argv parsing, then the deck loop
  api.py             generation, emoji lookup, dispatch, DeckManager
  config.py          the Config singleton and the zip's member names
  loader.py          the grammar and its parser
  models.py          Button, Routine, Other, Dispatch
  dal/orc.py         HTTP to orc
  dal/streamdeck.py  the USB device
  fonts/             Noto Color Emoji and Liberation Sans, both OFL
examples/
  config.arrow       a complete config
scripts/
  upload.sh             build a wheel and push it to a registry
  install.sh            remote install, run over ssh
  build-and-install.sh  both in sequence
```

## Build and deploy (the author's setup)

`scripts/upload.sh` refuses to run with uncommitted changes, builds a wheel,
and uploads it to a package registry. `scripts/install.sh` installs that
wheel on the target and bounces a `supervisord` job named `arrow`.
`scripts/build-and-install.sh` runs both:

```sh
sh scripts/build-and-install.sh
sh scripts/build-and-install.sh --no-restart
```

Registry and host come from `scripts/deploy.env`; copy `deploy.env.example`
and fill it in. The config and `icons.zip` are not in the wheel; put them
on the host yourself and set `ARROW_CONFIG` in the service environment.

## License

GPL-2.0-or-later. See [LICENSE](LICENSE).
