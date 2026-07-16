#!/usr/bin/env bash

set -u

SCRIPT_PATH="${BASH_SOURCE[0]}"
case "$SCRIPT_PATH" in
    */*) SCRIPT_DIR_PART="${SCRIPT_PATH%/*}" ;;
    *) SCRIPT_DIR_PART="." ;;
esac
SCRIPT_DIR="$(cd "$SCRIPT_DIR_PART" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

TICKER=""
PERIOD="5y"
STATUS_FILE=""
INDUSTRY_RUN_MANIFEST=""
CHILD=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ticker)
            TICKER="${2:-}"
            shift 2
            ;;
        --period)
            PERIOD="${2:-}"
            shift 2
            ;;
        --status-file)
            STATUS_FILE="${2:-}"
            shift 2
            ;;
        --industry-run-manifest)
            INDUSTRY_RUN_MANIFEST="${2:-}"
            shift 2
            ;;
        --child)
            CHILD=1
            shift
            ;;
        *)
            printf 'Unknown argument: %s\n' "$1" >&2
            exit 2
            ;;
    esac
done

case "$TICKER" in
    MU|mu) TICKER="MU" ;;
    SNDK|sndk) TICKER="SNDK" ;;
    WDC|wdc) TICKER="WDC" ;;
    STX|stx) TICKER="STX" ;;
    *)
        printf 'Ticker must be one of: MU, SNDK, WDC, STX.\n' >&2
        exit 2
        ;;
esac

case "$PERIOD" in
    1y|2y|5y|10y|max) ;;
    *)
        printf 'Period must be one of: 1y, 2y, 5y, 10y, max.\n' >&2
        exit 2
        ;;
esac

if [[ -z "$INDUSTRY_RUN_MANIFEST" ]]; then
    printf 'An industry run manifest is required.\n' >&2
    exit 5
fi

write_status() {
    if [[ -n "$STATUS_FILE" ]]; then
        printf '%s' "$1" > "$STATUS_FILE"
    fi
}

if [[ "$CHILD" -eq 0 ]]; then
    if [[ "${OSTYPE:-}" != darwin* ]]; then
        printf 'This launcher requires macOS Terminal.app.\n' >&2
        exit 2
    fi

    STATUS_FILE="$(mktemp "${TMPDIR:-/tmp}/stock-memory-analyzer-status.XXXXXX")"
    CHILD_COMMAND="$(printf 'exec /bin/bash %q --child --ticker %q --period %q --status-file %q --industry-run-manifest %q' \
        "$SCRIPT_DIR/run_with_prompt.sh" "$TICKER" "$PERIOD" "$STATUS_FILE" "$INDUSTRY_RUN_MANIFEST")"

    osascript - "$CHILD_COMMAND" <<'APPLESCRIPT'
on run argv
    set commandText to item 1 of argv
    tell application "Terminal"
        activate
        set loginTab to do script commandText
        set loginWindow to front window
        repeat while busy of loginTab
            delay 1
        end repeat
        try
            close loginWindow
        end try
    end tell
end run
APPLESCRIPT
    APPLESCRIPT_EXIT=$?

    if [[ "$APPLESCRIPT_EXIT" -ne 0 ]]; then
        rm -f "$STATUS_FILE"
        exit "$APPLESCRIPT_EXIT"
    fi

    if [[ -s "$STATUS_FILE" ]]; then
        CHILD_EXIT="$(cat "$STATUS_FILE")"
    else
        CHILD_EXIT=1
    fi
    rm -f "$STATUS_FILE"
    exit "$CHILD_EXIT"
fi

cleanup_credentials() {
    unset PANDA_DATA_USERNAME PANDA_DATA_PASSWORD
    username=""
    password=""
}

abort_run() {
    write_status 130
    exit 130
}

trap cleanup_credentials EXIT
trap abort_run HUP INT TERM

if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    printf 'Python 3 is required. This window will close automatically.\n' >&2
    write_status 4
    sleep 4
    exit 4
fi

cd "$ROOT_DIR" || exit 1

printf 'stock-memory-analyzer\n'
printf 'Credentials are requested locally and are not written to files or logs.\n\n'

"$PYTHON_BIN" utils/industry_refresh.py precheck --manifest "$INDUSTRY_RUN_MANIFEST" --ticker "$TICKER"
if [[ $? -ne 0 ]]; then
    printf 'Industry data is not ready. No credentials were requested.\n' >&2
    write_status 5
    sleep 4
    exit 5
fi

"$PYTHON_BIN" analyze.py --check-deps
if [[ $? -ne 0 ]]; then
    printf 'Dependencies are not ready. Install requirements.txt and retry.\n' >&2
    printf 'This window will close automatically.\n'
    write_status 3
    sleep 4
    exit 3
fi

read -r -p 'panda_data account: ' username
if [[ -z "$username" ]]; then
    printf 'Account is required.\n' >&2
    write_status 2
    sleep 2
    exit 2
fi

read -r -s -p 'panda_data password (hidden): ' password
printf '\n'
if [[ -z "$password" ]]; then
    printf 'Password is required.\n' >&2
    write_status 2
    sleep 2
    exit 2
fi

export PANDA_DATA_USERNAME="$username"
export PANDA_DATA_PASSWORD="$password"

"$PYTHON_BIN" analyze.py --ticker "$TICKER" --period "$PERIOD" --industry-run-manifest "$INDUSTRY_RUN_MANIFEST"
ANALYSIS_EXIT=$?
write_status "$ANALYSIS_EXIT"

exit "$ANALYSIS_EXIT"
