# arrow

A daemon that turns an Elgato Stream Deck into a control panel for
[orc](https://github.com/exussum/orc), a home automation orchestrator. Key
presses become HTTP calls against orc; the deck dims when idle and wakes on the
next press.

Everything on the deck — which key does what, which emoji it shows, which orc
action it calls — comes from one config file. The icons are generated from that
config, not drawn by hand.

## What it does

- Uploads an icon to every configured key and listens for presses.
- Calls orc: `/api/room/{room}?state=` for room keys, `/api/run/{id}` for
  routines, `/api/presence/{name}/checkin` for the check-in key.
- Plays a countdown GIF on the pressed key while the call is in flight, sized
  from orc's own measured average for that action.
- Announces and flags actions orc will delay, through `/api/announce`.
- Toggles label overlays on the help key, so you can see what each key does.
- Starts dim, wakes on the first press, and re-dims after an idle timeout.

## Configure

A config file declares the deck. Each line is a command; see
[`examples/config.arrow`](examples/config.arrow) for a complete one.

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

- **`room`** expands to three keys. The orc state supplies the badge, the label
  suffix and the `?state=` value, so a room needs one `button` line per state.
- **`routine`** takes a layout word that fixes what follows: `single` (one
  icon), `pair` (two icons, opposite corners), `caption` (icon plus text),
  `marked` (icon plus badge).
- **`--orc-id`** defaults to `AD_HOC_<SLUG>`. Name it explicitly for anything
  that breaks the convention, including orc plugin names.
- **Icons** are Unicode character names, lowercased and hyphenated. Append
  `:dim` or `:invert` to filter one glyph.
- **`help` and `presence`** are reserved: both need an `other` line and a
  `button` line.

Point arrow at the file with `--config` or `ARROW_CONFIG`. The generated
`icons.zip` lives beside it.

## Install and run

Requires Python 3.14 and a Stream Deck on USB. The `streamdeck` library needs
hidapi on the host.

```sh
pip install .
arrow package --config /etc/arrow/config.arrow   # writes /etc/arrow/icons.zip
arrow --config /etc/arrow/config.arrow
```

On startup the daemon refuses to run if the zip is missing anything it needs,
and reports — without stopping — any room, routine or person orc doesn't know.

`arrow package` reads orc's `/api/actions` for countdown lengths, so run it
somewhere orc is reachable. The fonts it renders with are bundled, so it needs
nothing else installed.

## Commands

| Command | Does |
| --- | --- |
| `arrow` | Run the daemon |
| `arrow package [out]` | Generate the icons into a zip |
| `arrow icons search WORD...` | Find an emoji name for the config |
| `arrow icons name EMOJI...` | Convert pasted emoji to config names |

`--config` and `--icons` work with all of them.

## Layout

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

Run the checks with `uv run --extra test pytest`, or `pre-commit run
--all-files` for the full lint, type, audit and test suite.

## Build and deploy

`scripts/upload.sh` refuses to run with uncommitted changes, builds a wheel and
uploads it to a package registry. `scripts/install.sh` installs that wheel on
the target and bounces a `supervisord` job named `arrow`.
`scripts/build-and-install.sh` runs both:

```sh
sh scripts/build-and-install.sh
sh scripts/build-and-install.sh --no-restart
```

Registry and host come from `scripts/deploy.env`; copy `deploy.env.example` and
fill it in. The config and `icons.zip` are not in the wheel — put them on the
host yourself and set `ARROW_CONFIG` in the service environment.

## License

GPL-2.0-or-later. See [LICENSE](LICENSE).
