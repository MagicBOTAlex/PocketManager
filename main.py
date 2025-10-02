# main.py was completly ChatGPT, but highly modified now
import os
import time
import logging
import asyncio
import threading
import uvicorn
import signal
import sys
from typing import Any, Dict, Optional
from fastapi import FastAPI, Header, HTTPException
from fastapi import BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
import subprocess
from dotenv import load_dotenv, find_dotenv
from backup import startBackup

env_path = find_dotenv(usecwd=True)
loaded = load_dotenv(env_path, override=True)

# --- manager logger ---
log = logging.getLogger("pb_mgr")
h = logging.StreamHandler()
h.setFormatter(logging.Formatter("[PB_MGR] %(message)s"))
log.addHandler(h)
log.setLevel(logging.INFO)


def get_env(key: str, *default: str) -> str:
    val = os.getenv(key)
    if val is None or val == "":               # treat empty as missing
        if default:                            # default provided -> use it
            return default[0]
        raise RuntimeError(f"You forgor...💀 the environment var: {key}")
    return val


def startPB():
    port = 8080
    cmd = ["stdbuf", "-oL", "-eL", "pocketbase",
           "serve", "--http", f"0.0.0.0:{port}"]
    pbDir = get_env("INTERNAL_PB_DIR", "/pb_data/")
    if pbDir != "":
        cmd.append("--dir")
        cmd.append(pbDir)
    log.info(f"Starting pocketbase backend with data: {
             os.path.normpath(os.path.join(os.getcwd(), pbDir))}")
    global p
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )

    def pump(src):
        for line in src:
            print(f"[PB] {line}", end="")   # tag every PB line

    t = threading.Thread(target=pump, args=(p.stdout,), daemon=True)
    t.start()
    log.info(f"Pocketbase started on port: {port}")


def stopPB():
    log.info("Force killing PocketBase (SIGKILL)...")
    global p
    os.killpg(p.pid, signal.SIGKILL)


app = FastAPI()


class WebhookPayload(BaseModel):
    event_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@app.get("/ping", response_class=PlainTextResponse)
def ping():
    return "pong"


def doBackupSequence():
    stopPB()
    time.sleep(1)
    startBackup()
    time.sleep(1)
    startPB()


@app.post("/backup")
async def backup():
    asyncio.create_task(asyncio.to_thread(doBackupSequence))
    return JSONResponse({"ok": True, "message": "Starting backup..."})


def KeyboardInterruptHandler(sig, frame):
    stopPB()


signal.signal(signal.SIGINT, KeyboardInterruptHandler)

if __name__ == "__main__":
    startPB()
    uvicorn.run(app, host="0.0.0.0", port=8000)
