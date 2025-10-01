#!/bin/sh

echo "[Backend BOOT] Removeing old git pull, if it exists"
rm -fr /pocketManager

echo "[Backend BOOT] Cloning repo..."
gix clone https://github.com/MagicBOTAlex/PocketManager.git /pocketManager/

echo "[Backend BOOT] Entered repo"
cd /pocketManager/

# echo "[BOOT] Loading ssh private key"
# ssh-add ${SSH_PRIV_KEY}

echo "[Backend BOOT] Starting using nix flake..."
nix run --extra-experimental-features nix-command --extra-experimental-features flakes
