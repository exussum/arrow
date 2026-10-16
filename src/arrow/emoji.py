import sys
import unicodedata

RANGES = ((0x2190, 0x33FF), (0x1F000, 0x1FAFF))


def _named() -> list[tuple[str, str]]:
    out = []
    for lo, hi in RANGES:
        for cp in range(lo, hi + 1):
            try:
                out.append((chr(cp), unicodedata.name(chr(cp))))
            except ValueError:
                pass
    return out


def to_name(char: str) -> str:
    return unicodedata.name(char.replace("️", "")).lower().replace(" ", "-")


def to_char(name: str) -> str:
    return unicodedata.lookup(name.replace("-", " ").upper())


def search(query: str) -> list[tuple[str, str]]:
    return [(c, to_name(c)) for c, n in _named() if query.upper() in n]


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "search":
        for char, name in search(" ".join(argv[1:])):
            print(f"{char}\t--icon={name}")
        return 0
    if len(argv) >= 2 and argv[0] == "name":
        print(" ".join(f"--icon={to_name(c)}" for c in argv[1:]))
        return 0
    print("usage: arrow icons search <word> | arrow icons name <emoji>...", file=sys.stderr)
    return 2
