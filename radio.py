#!/usr/bin/env -S uv run --script
# /// script
# dependencies = []
# ///
import itertools
import subprocess
import sys
import threading
import time

MPC = ["mpc"]

# station schema: key -> {name, url} — direct ICY/HTTP streams
STATIONS = {
    "lofi": {
        "name": "Nightride FM: Chillsynth",
        "url": "https://stream.nightride.fm/chillsynth.mp3",
    },
    "synthwave": {
        "name": "Nightride FM",
        "url": "https://stream.nightride.fm/nightride.mp3",
    },
}


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


# CLI
COMMANDS = {
    "--play": None,  # handled separately below, needs an argument
    "--stop": stop,
    "--pause": lambda: mpc_print("pause"),
    "--toggle": lambda: mpc_print("toggle"),
    "--current": lambda: mpc_print("current"),
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
