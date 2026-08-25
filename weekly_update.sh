#!/bin/bash
# Weekly run: pull the latest AP rankings and refresh the current-week graphs.

convert_path() {
    local input_path="$1"

    if [ -n "$WSL_DISTRO_NAME" ]; then
        wslpath -w "$input_path"
    elif [ -n "$MSYSTEM" ] && [ "$MSYSTEM" == "MINGW64" ]; then
        cygpath -w "$input_path"
    else
        echo "$input_path"
    fi
}

echo "---------------"
echo "AP CFB XC weekly update"
echo

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Locate the project's venv relative to the repo root - no hardcoded machine paths.
# Checks for a native Linux/macOS venv first, then a Windows venv (accessed via
# WSL or Git Bash / MINGW64). The interpreter path itself is left POSIX-style so
# this shell can find and exec it directly; only the script path handed to that
# (Windows) interpreter as an argument needs converting, since it's the Windows
# python.exe process - not this shell - that has to resolve it.
if [[ -f "$REPO_DIR/venv/bin/python" ]]; then
    PYTHON_PATH="$REPO_DIR/venv/bin/python"
    SCRIPT_PATH="$REPO_DIR/weekly_update.py"
elif [[ -f "$REPO_DIR/venv/Scripts/python.exe" ]]; then
    PYTHON_PATH="$REPO_DIR/venv/Scripts/python.exe"
    SCRIPT_PATH="$(convert_path "$REPO_DIR/weekly_update.py")"
else
    echo "Error: no venv found under $REPO_DIR/venv"
    echo "Create one with: python -m venv venv && venv/bin/pip install -r requirements.in"
    exit 1
fi

echo "Using Python: $PYTHON_PATH"
echo

"$PYTHON_PATH" "$SCRIPT_PATH"

echo "----------------"
# Uncomment the line below if you want the terminal to wait on manual runs.
# This should stay commented out for unattended cron/schtasks runs.
# read -rp "Press Enter to continue . . ."
