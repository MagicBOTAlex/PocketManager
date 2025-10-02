# ChatGPT'd
#!/usr/bin/env python3
import os
import logging
import shlex
import subprocess
import sys
import re
import time
from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv(usecwd=True)
loaded = load_dotenv(env_path, override=True)

logging.basicConfig(format='[BB] %(message)s', level=logging.INFO)
log = logging.getLogger(__name__)

size_re = re.compile(r"""
    (?P<o_val>\d+(?:\.\d+)?)\s*(?P<o_unit>[KMGTP]?B)\s+O\s+
    (?P<c_val>\d+(?:\.\d+)?)\s*(?P<c_unit>[KMGTP]?B)\s+C\s+
    (?P<d_val>\d+(?:\.\d+)?)\s*(?P<d_unit>[KMGTP]?B)\s+D\s+
    (?P<n>\d+)\s+N
""", re.VERBOSE)

pct_re = re.compile(r"\b(\d{1,3})%\b")

UNIT = {"B": 1, "KB": 1024, "MB": 1024**2,
        "GB": 1024**3, "TB": 1024**4, "PB": 1024**5}


def to_bytes(val, unit):
    u = unit.upper().replace(" ", "")
    return float(val) * UNIT[u]


def fmt_bytes(b):
    for u in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if b < 1024 or u == "PB":
            return f"{b:.0f} {u}" if u == "B" else f"{b:.2f} {u}"
        b /= 1024


def get_env(key: str, *default: str) -> str:
    val = os.getenv(key)
    if val is None or val == "":               # treat empty as missing
        if default:                            # default provided -> use it
            return default[0]
        raise RuntimeError(f"You forgor...💀 the environment var: {key}")
    return val


def startBackup():
    cmd = [
        "borg", "create",
        f"{get_env('REMOTE_HOST')}{get_env(
            'REMOTE_BACKUP_PATH')}/pocketBackup::{{now}}",
        get_env("INTERNAL_PB_DIR", "/pb_data"),
    ]
    tokens = cmd[:]

    # Ensure progress + list so we can parse O/C/D/N lines
    for flag in ("--progress", "--list"):
        if flag not in tokens:
            try:
                i = tokens.index("create")
                tokens.insert(i + 1, flag)
            except ValueError:
                tokens.append(flag)

    log.info("Sending: " + " ".join(tokens))

    env = {
        **os.environ,
        "BORG_RSH": "ssh -i /SSH_PRIV_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new",
        "BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK": "yes",
    }
    proc = subprocess.Popen(
        tokens,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        text=True,
        bufsize=1,
        errors="replace",
    )

    t0 = time.time()
    last_o = last_c = last_d = last_n = 0
    percent = None

    try:
        for line in proc.stdout:
            # Try percentage first
            m = pct_re.search(line)
            if m:
                percent = int(m.group(1))

            # Parse O/C/D/N status lines
            s = size_re.search(line)
            if s:
                o = to_bytes(s["o_val"], s["o_unit"])
                c = to_bytes(s["c_val"], s["c_unit"])
                d = to_bytes(s["d_val"], s["d_unit"])
                n = int(s["n"])
                dt = max(time.time() - t0, 1e-6)
                o_rate = fmt_bytes((o - last_o) / dt) + \
                    "/s" if o >= last_o else "—"
                c_rate = fmt_bytes((c - last_c) / dt) + \
                    "/s" if c >= last_c else "—"
                t0, last_o, last_c, last_d, last_n = time.time(), o, c, d, n

                status = [
                    f"O {fmt_bytes(o)} ({o_rate})",
                    f"C {fmt_bytes(c)} ({c_rate})",
                    f"D {fmt_bytes(d)}",
                    f"N {n}",
                ]
                if percent is not None:
                    status.insert(0, f"{percent}%")

                sys.stdout.write("\r" + " | ".join(status) + " " * 10)
                sys.stdout.flush()
            else:
                # pass through regular log lines immediately
                log.info(line.rstrip())
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        log.info("\nInterrupted.")

    log.info("")
    if proc.returncode == 0:
        log.info("Backup finished ✔")
    else:
        log.error(f"Backup failed (exit {proc.returncode})")
        sys.exit(proc.returncode or 1)


if __name__ == "__main__":
    startBackup()
