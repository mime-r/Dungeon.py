"""Cross-platform, turn-based single-key input.

Replaces the old ``keyboard`` global-hook library. Reads one logical keypress at a
time from the controlling terminal:

* Windows  -> ``msvcrt``
* Unix/mac -> ``termios`` + ``tty`` raw mode

Arrow keys, Enter, Escape and friends are normalised to stable logical tokens
("up", "down", "left", "right", "enter", "esc", "space", "tab", "backspace").
Everything else is returned as the literal character.

A scripted-input hook (:func:`feed_keys`) lets tests and headless smoke runs drive
the game without a real terminal.
"""

import sys

# Logical key tokens
UP, DOWN, LEFT, RIGHT = "up", "down", "left", "right"
ENTER, ESC, SPACE, TAB, BACKSPACE = "enter", "esc", "space", "tab", "backspace"

# Direction tokens players can produce (arrows + vi-keys), mapped to compass dirs.
MOVE_KEYS: dict[str, str] = {
    UP: "n", "k": "n", "w": "n",
    DOWN: "s", "j": "s",
    LEFT: "w", "h": "w", "a": "w",
    RIGHT: "e", "l": "e",
    "y": "nw", "u": "ne", "b": "sw", "n": "se",
}

_scripted = None  # optional iterator of keys for tests / headless runs


def feed_keys(keys) -> None:
    """Queue a sequence of logical keys to be returned by :func:`read_key`.

    Intended for tests and headless smoke runs. When the queue is exhausted,
    :func:`read_key` returns ``"esc"`` so loops terminate cleanly.
    """
    global _scripted
    _scripted = iter(keys)


def clear_scripted() -> None:
    global _scripted
    _scripted = None


def _read_key_windows() -> str:
    import msvcrt

    ch = msvcrt.getwch()
    if ch in ("\x00", "\xe0"):  # special key prefix; read the scan code
        code = msvcrt.getwch()
        return {
            "H": UP, "P": DOWN, "K": LEFT, "M": RIGHT,
            "G": "home", "O": "end", "I": "pageup", "Q": "pagedown",
            "S": "delete",
        }.get(code, ch)
    return _normalise(ch)


def _read_key_unix() -> str:
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":  # escape sequence (arrow keys) or a bare Escape
            seq = sys.stdin.read(2)
            return {
                "[A": UP, "[B": DOWN, "[C": RIGHT, "[D": LEFT,
                "[H": "home", "[F": "end",
            }.get(seq, ESC)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return _normalise(ch)


def _normalise(ch: str) -> str:
    return {
        "\r": ENTER, "\n": ENTER,
        "\x1b": ESC,
        " ": SPACE,
        "\t": TAB,
        "\x7f": BACKSPACE, "\x08": BACKSPACE,
        "\x03": ESC,  # Ctrl-C -> treat as escape so loops can exit gracefully
    }.get(ch, ch)


def read_key() -> str:
    """Block until a single logical keypress and return its token."""
    if _scripted is not None:
        try:
            return next(_scripted)
        except StopIteration:
            return ESC
    if sys.platform == "win32":
        return _read_key_windows()
    return _read_key_unix()


def key_pressed() -> bool:
    """Return True if a keypress is available without blocking.

    Lets long-running loops (e.g. auto-explore) abort as soon as the player
    taps a key. Drains nothing; the next :func:`read_key` will still return it.
    """
    if _scripted is not None:
        # Peek the scripted iterator without consuming.
        from itertools import chain
        if isinstance(_scripted, chain):
            return True  # may be empty; harmless if caller still reads
        try:
            peek = _scripted.__next__
        except AttributeError:
            return False
        # Can't peek generators without consuming - just return True and
        # accept the cost of one false positive on exhaustion.
        return True
    if sys.platform == "win32":
        try:
            import msvcrt
            return msvcrt.kbhit()
        except Exception:
            return False
    try:
        import select
        rlist, _, _ = select.select([sys.stdin], [], [], 0)
        return bool(rlist)
    except Exception:
        return False


def read_direction(key: str) -> str | None:
    """Return the compass direction (e.g. "n"/"se") for a movement key, else None."""
    return MOVE_KEYS.get(key)
