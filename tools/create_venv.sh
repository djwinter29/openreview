#!/usr/bin/env bash
set -euo pipefail

# create_venv.sh
# Removes existing .venv directory, creates a new Python virtualenv at .venv,
# upgrades pip, wheel, setuptools, then installs a list of packages.
# Usage:
#   ./create_venv.sh                # installs default packages (platformio)
#   ./create_venv.sh pkg1 pkg2 ...  # installs specified packages

ROOT_DIR="$(pwd)"
VENV_DIR="$ROOT_DIR/.venv"

if [ "$EUID" -eq 0 ]; then
  echo "Don't run this script as root. Exiting." >&2
  exit 1
fi

echo "This will remove '$VENV_DIR' if it exists, then create a new venv." 
echo "Proceeding without prompt (non-interactive mode)."

if [ -d "$VENV_DIR" ]; then
  echo "Removing existing venv at $VENV_DIR"
  rm -rf "$VENV_DIR"
fi

echo "Creating venv at $VENV_DIR"
python3 -m venv "$VENV_DIR"

echo "Activating venv"
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

echo "Installing packages from requirements.txt"
pip install -r "$ROOT_DIR/requirements.txt"

echo "Installation complete. To activate the venv, run:"
echo "  source $VENV_DIR/bin/activate"

exit 0