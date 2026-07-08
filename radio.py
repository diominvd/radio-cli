#!/usr/bin/env -S uv run --script
# /// script
# dependencies = []
# ///
import itertools
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

MPC = ["mpc"]
STATIONS_FILE = Path.home() / ".config" / "scripts" / "radio" / "stations.json"
STATIONS = json.loads(STATIONS_FILE.read_text())


# Helpers
def mpc(*args) -> subprocess.CompletedProcess:
    return subprocess.run(MPC + list(args), capture_output=True, text=True)


def mpc_print(*args) -> None:
    result = mpc(*args)
    if result.stdout.strip():
        print("[*] " + result.stdout.split("\n")[0].strip())


def spinner(msg: str, stop_event: threading.Event) -> None:
    for frame in itertools.cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]):
        if stop_event.is_set():
            print(f"\r{' ' * (len(msg) + 5)}", end="", flush=True)
            break
        print(f"\r[{frame}] {msg}", end="", flush=True)
        time.sleep(0.08)


def run_with_spinner(msg: str, fn) -> None:
    stop = threading.Event()
    t = threading.Thread(target=spinner, args=(msg, stop))
    t.start()
    try:
        fn()
    finally:
        stop.set()
        t.join()


def _playback_state() -> str | None:
    """Returns 'playing', 'paused', or None (stopped/no mpd)."""
    result = mpc()
    lines = result.stdout.splitlines()
    if len(lines) < 2:
        return None
    if lines[1].startswith("[playing]"):
        return "playing"
    if lines[1].startswith("[paused]"):
        return "paused"
    return None


def _current_station_name() -> str | None:
    result = mpc("current", "-f", "%file%")
    url = result.stdout.strip()
    for station in STATIONS.values():
        if station["url"] == url:
            return station["name"]
    return None


# Commands
def play(key: str | None) -> None:
    if not key:
        print(f"usage: radio --play [ {' | '.join(STATIONS)} ]")
        sys.exit(1)
    if key not in STATIONS:
        print(f"[!] Unknown station '{key}'. Options: {', '.join(STATIONS)}")
        sys.exit(1)

    station = STATIONS[key]
    run_with_spinner(
        f"Tuning in to {station['name']}...",
        lambda: (mpc("stop"), mpc("clear"), mpc("add", station["url"]), mpc("play")),
    )
    print(f"\r[*] Streaming: {station['name']}")


def stop() -> None:
    mpc("stop")
    mpc("clear")
    print("[*] Stopped")


def list_stations() -> None:
    print("[*] Available stations:")
    for key, s in STATIONS.items():
        print(f"    {key:<10} {s['name']}")


def current_json() -> None:
    state = _playback_state()
    name = _current_station_name()

    if not name or state is None:
        text = "No radio"
        css_class = "off"
    elif state == "playing":
        text = f"Station: {name}"
        css_class = "playing"
    else:
        text = f"Station: {name}"
        css_class = "paused"

    print(json.dumps({"text": text, "class": css_class}))


# CLI
COMMANDS = {
    "--play": None,
    "--stop": stop,
    "--pause": lambda: mpc_print("pause"),
    "--toggle": lambda: mpc_print("toggle"),
    "--current": lambda: mpc_print("current"),
    "--current-json": current_json,
    "--list": list_stations,
}


def main() -> None:
    if len(sys.argv) < 2:
        print(f"usage: radio [ {' | '.join(COMMANDS)} ]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "--play":
        play(sys.argv[2] if len(sys.argv) > 2 else None)
        return
    if cmd not in COMMANDS:
        print(f"usage: radio [ {' | '.join(COMMANDS)} ]")
        sys.exit(1)
    COMMANDS[cmd]()


if __name__ == "__main__":
    main()
