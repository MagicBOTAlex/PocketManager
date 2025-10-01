#!/bin/sh

echo "[Backend BOOT] Removeing old git pull, if it exists"
rm -fr /backend

echo "[Backend BOOT] Cloning repo..."
gix clone https://BOTAlex:${GITKEY}@git.deprived.dev/botalex/DeprivedBackend.git /backend/

echo "[Backend BOOT] Entered repo"
cd /backend/

echo "[Backend BOOT] Starting using nix flake..."
nix run --extra-experimental-features nix-command --extra-experimental-features flakes
