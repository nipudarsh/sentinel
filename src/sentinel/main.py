from __future__ import annotations

from sentinel import __version__


def main() -> int:
    print(f"SENTINEL v{__version__} — boot OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
