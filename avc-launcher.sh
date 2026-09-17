#!/usr/bin/env bash
# ============================================================================
# avc-launcher.sh — AngryOxide-AVClub TUI Launcher
#
# Whiptail front-end for the two tools in this repo. Describes what each one
# does, builds its command line through menus instead of flags, previews the
# command, then runs it either in this terminal or in its own window.
#
# Everything runs as root inside the project's avc-venv, from the project
# directory (AVC.py resolves cleanup.sh / whitelist.txt / interfaces.json
# relative to the working directory).
#
# Prerequisites: whiptail, avc-venv + the angryoxide binary (sudo ./install.sh),
#                sudo privileges. A terminal emulator is optional — without one
#                the tools run in the current terminal, so SSH sessions work.
# ============================================================================

set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$PROJECT_DIR/avc-venv/bin/python3"
WORKDIR="$PROJECT_DIR"

# ── Colour helpers (for pre-TUI messages) ────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Whiptail colour scheme (black + green) ───────────────────────────────────
export NEWT_COLORS='
root=green,black
roottext=green,black
window=green,black
border=green,black
title=brightgreen,black
label=green,black
textbox=green,black
listbox=green,black
actlistbox=black,brightgreen
sellistbox=black,green
actsellistbox=black,brightgreen
checkbox=green,black
actcheckbox=black,brightgreen
button=black,green
actbutton=black,brightgreen
entry=brightgreen,black
compactbutton=black,green
'

TITLE=" AngryOxide-AVClub Launcher v1.0 by @dr0pp1n "

# ── Escalate to root once (the tools need it, and so do spawned terminals) ────

if [[ $EUID -ne 0 ]]; then
    exec sudo -- "$0" "$@"
fi

# ── Dependency checks ────────────────────────────────────────────────────────

if ! command -v whiptail &> /dev/null; then
    echo -e "${RED}Error:${NC} whiptail is required but not installed."
    echo "       Install it with:  sudo apt-get install whiptail"
    exit 1
fi

if [[ ! -x "$VENV_PY" ]]; then
    echo -e "${RED}Error:${NC} virtual environment not found at ${BOLD}avc-venv${NC}."
    echo "       Build the environment first:  sudo ./install.sh"
    exit 1
fi

# Detect a terminal emulator for spawning visible windows (optional).
detect_terminal() {
    [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]] || return 1
    local term
    for term in gnome-terminal xfce4-terminal mate-terminal lxterminal konsole xterm; do
        if command -v "$term" &> /dev/null; then
            echo "$term"
            return 0
        fi
    done
    return 1
}

TERM_EMU="$(detect_terminal)" || TERM_EMU=""

# ── Dialog sizing ────────────────────────────────────────────────────────────

H=$(tput lines 2>/dev/null || echo 24)
W=$(tput cols 2>/dev/null || echo 80)
(( H > 22 )) || H=22
(( W > 76 )) || W=76
(( W < 100 )) || W=100

# ── Dialog helpers ───────────────────────────────────────────────────────────
# UI is sent to stderr so these stay usable inside $( ) captures.

msg() {   # title, text, [height]
    whiptail --title "$1" --msgbox "$2" "${3:-14}" "$W" 1>&2
}

confirm() {   # title, text, [height]
    whiptail --title "$1" --yesno "$2" "${3:-14}" "$W" 1>&2
}

textfile() {   # title, path
    whiptail --title "$1" --scrolltext --textbox "$2" "$H" "$W" 1>&2
}

# ask_input <title> <prompt> <default> [regex] [error text]
# Re-prompts until the value matches; empty return means the user cancelled.
ask_input() {
    local title="$1" prompt="$2" default="$3" regex="${4:-}" err="${5:-That value is not valid.}"
    local value
    while true; do
        value=$(whiptail --title "$title" --inputbox "$prompt" 12 "$W" "$default" 3>&1 1>&2 2>&3) || return 1
        if [[ -z "$regex" || "$value" =~ $regex ]]; then
            printf '%s' "$value"
            return 0
        fi
        msg "Invalid input" "\n$err\n\nYou entered: $value" 12
    done
}

ask_password() {   # title, prompt
    whiptail --title "$1" --passwordbox "$2" 12 "$W" 3>&1 1>&2 2>&3
}

# ── Persistent configuration (avc.conf) ──────────────────────────────────────
# AVC.py reads avc.conf at startup; these helpers view and edit it. The
# effective config (built-ins overridden by the file) comes from
# 'AVC.py --print-config' so the launcher never duplicates the defaults.

CONFIG_FILE="$PROJECT_DIR/avc.conf"
CFG_JSON="{}"

cfg_refresh() {   # cache the effective config once per menu render
    CFG_JSON="$(cd "$PROJECT_DIR" && "$VENV_PY" AVC.py --print-config 2>/dev/null)"
    [[ -n "$CFG_JSON" ]] || CFG_JSON="{}"
}

cfg_get() {   # key -> scalar value from the cached config
    printf '%s' "$CFG_JSON" | "$VENV_PY" -c \
        'import sys,json;print(json.load(sys.stdin).get(sys.argv[1],""))' "$1" 2>/dev/null
}

cfg_get_list() {   # key -> list value as space-separated items
    printf '%s' "$CFG_JSON" | "$VENV_PY" -c \
        'import sys,json;print(" ".join(str(x) for x in json.load(sys.stdin).get(sys.argv[1],[])))' "$1" 2>/dev/null
}

cfg_set() {   # key  type(str|int|list)  [values...] -> merge one key into avc.conf
    local key="$1" type="$2"; shift 2
    "$VENV_PY" - "$CONFIG_FILE" "$key" "$type" "$@" <<'PY'
import json, os, sys
path, key, typ = sys.argv[1], sys.argv[2], sys.argv[3]
vals = sys.argv[4:]
cfg = {}
if os.path.isfile(path):
    try:
        with open(path) as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict):
            cfg = {}
    except Exception:
        cfg = {}
if typ == 'int':
    cfg[key] = int(vals[0])
elif typ == 'list':
    cfg[key] = list(vals)
else:
    cfg[key] = vals[0] if vals else ""
with open(path, 'w') as f:
    json.dump(cfg, f, indent=2)
    f.write('\n')
PY
}

# ── Tool descriptions ────────────────────────────────────────────────────────

AVC_SUMMARY="AVC — attack + hash exfil (monitor mode, AngryOxide)"
AVC_CC_SUMMARY="AVC-CC — hashcat monitoring, remote fetch, cracking"

AVC_DESC="\
AVC.py  —  Automatic Wi-Fi Pwner   (v0.7a)

  Clears stale captures with cleanup.sh, puts a wireless interface into
  monitor mode, and runs AngryOxide headless at attack rate 3 across
  every channel the interface supports in the 2.4, 5 and 6 GHz bands.

  Collected WPA/WPA2 handshakes land in the working directory as
  <essid>_<bssid>.hc22000 files. AVC.py reads each new hashline and,
  depending on the output mode, archives the file to hashes/ and/or
  publishes it to the Kafka topic 'wifi-hash' with sysId, timestamp,
  essid and bssid.

  Needs: a monitor-mode capable NIC, root, the angryoxide binary.
  Respects: whitelist.txt (MACs or SSIDs to leave alone).
  Stop it with Ctrl-C — AngryOxide is terminated with it.

  WARNING: cleanup.sh deletes *.hc22000, *.kismet, scan-* and oxide-*
  from the project root at every start. Files already in hashes/ are safe."

AVC_CC_DESC="\
AVC-CC.py  —  Crack & Comms   (v0.1a)

  Watches a hashcat outfile and reports each time new passwords fall,
  stopping after N notifications or when the hashcat run it is watching
  exits.

  It can also do the cracking itself:
    - autocrack  cracks every .hc22000 file in the working directory
    - singlecrack  cracks one file you pick
  Results are appended to a credentials file as ESSID:password, and
  files that already have a cracked_*.txt output are skipped.

  Remote mode pulls result files from other hosts over SCP, either from
  hash-targets.json or from an address plus credentials you type in,
  and appends them to the monitored outfile.

  Needs: hashcat and a wordlist (default /usr/share/wordlists/rockyou.txt)
  for cracking, sshpass for remote fetching.
  A hashcat process does not have to be running first."

show_about() {
    local tmp
    tmp="$(mktemp)"
    {
        echo "$AVC_DESC"
        echo ""
        echo "----------------------------------------------------------------"
        echo ""
        echo "$AVC_CC_DESC"
        echo ""
        echo "----------------------------------------------------------------"
        echo ""
        echo "Both tools run as root from $PROJECT_DIR, using avc-venv."
    } > "$tmp"
    textfile " About the AVClub tools " "$tmp"
    rm -f "$tmp"
}

# ── Environment status ───────────────────────────────────────────────────────

show_status() {
    local tmp interfaces
    tmp="$(mktemp)"
    {
        echo "Project directory : $PROJECT_DIR"
        echo ""

        if command -v angryoxide &> /dev/null; then
            echo "angryoxide        : $(command -v angryoxide)  [$(timeout 10 angryoxide --version 2>/dev/null | head -n1)]"
        else
            echo "angryoxide        : NOT INSTALLED  (run: sudo ./install.sh)"
        fi

        echo "venv python       : $("$VENV_PY" --version 2>&1)"
        if "$VENV_PY" -c 'import pandas, kafka' &> /dev/null; then
            echo "python deps       : pandas + kafka OK"
        else
            echo "python deps       : MISSING  (run: sudo ./install.sh)"
        fi

        if command -v hashcat &> /dev/null; then
            echo "hashcat           : $(command -v hashcat)"
        else
            echo "hashcat           : not installed (needed for AVC-CC cracking)"
        fi
        if command -v sshpass &> /dev/null; then
            echo "sshpass           : $(command -v sshpass)"
        else
            echo "sshpass           : not installed (needed for AVC-CC remote fetch)"
        fi

        echo ""
        echo "Wireless interfaces:"
        # Skip the unnamed non-netdev entries (P2P devices) that have no interface name.
        interfaces="$(iw dev 2>/dev/null | awk '/Interface/{iface=$2} /type/{if (iface != "") printf "  %-12s type %s\n", iface, $2; iface=""}')"
        if [[ -n "$interfaces" ]]; then
            echo "$interfaces"
        else
            echo "  none detected"
        fi

        echo ""
        if [[ -f "$PROJECT_DIR/interfaces.json" ]]; then
            echo "interfaces.json   : $(tr -d '\n ' < "$PROJECT_DIR/interfaces.json")"
        else
            echo "interfaces.json   : missing"
        fi
        if [[ -f "$PROJECT_DIR/whitelist.txt" ]]; then
            echo "whitelist.txt     : $(grep -cvE '^\s*(#|$)' "$PROJECT_DIR/whitelist.txt") entr(ies)"
        else
            echo "whitelist.txt     : missing (nothing will be excluded)"
        fi

        echo ""
        echo "Hash files:"
        echo "  project root    : $(find "$PROJECT_DIR" -maxdepth 1 -name '*.hc22000' 2>/dev/null | wc -l)"
        echo "  hashes/         : $(find "$PROJECT_DIR/hashes" -maxdepth 1 -name '*.hc22000' 2>/dev/null | wc -l)"
    } > "$tmp"
    textfile " Environment status " "$tmp"
    rm -f "$tmp"
}

# ── Launching ────────────────────────────────────────────────────────────────

# Spawn one visible terminal window. $1 emulator, $2 title, $3 command string.
spawn_with() {
    local term="$1" title="$2" cmd="$3"

    case "$term" in
        gnome-terminal)
            gnome-terminal --title="$title" -- bash -c "$cmd; echo; read -rp '[Process exited — press Enter to close] '" 2>/dev/null
            ;;
        xfce4-terminal)
            xfce4-terminal --title="$title" -e "bash -c \"$cmd; echo; read -rp '[Process exited — press Enter to close] '\"" &
            ;;
        mate-terminal)
            mate-terminal --title="$title" -e "bash -c \"$cmd; echo; read -rp '[Process exited — press Enter to close] '\"" &
            ;;
        lxterminal)
            lxterminal --title="$title" -e "bash -c \"$cmd; echo; read -rp '[Process exited — press Enter to close] '\"" &
            ;;
        konsole)
            konsole --new-tab -p tabtitle="$title" -e bash -c "$cmd; echo; read -rp '[Process exited — press Enter to close] '" &
            ;;
        xterm)
            xterm -T "$title" -e bash -c "$cmd; echo; read -rp '[Process exited — press Enter to close] '" &
            ;;
        *)
            return 1
            ;;
    esac
}

launch_in_terminal() {   # title, command string
    local title="$1" cmd="$2"

    if spawn_with "$TERM_EMU" "$title" "$cmd"; then
        return 0
    fi
    if [[ "$TERM_EMU" != "xterm" ]] && command -v xterm &> /dev/null; then
        echo -e "  ${CYAN}↳ ${TERM_EMU} could not start — falling back to xterm${NC}"
        spawn_with xterm "$title" "$cmd"
        return 0
    fi
    echo -e "  ${RED}Error:${NC} could not open a terminal window for '${title}'."
    return 1
}

# launch <title> <command...>  — previews, then runs here or in a new window.
launch() {
    local title="$1"; shift
    local -a cmd=("$@")
    local pretty
    pretty="$(printf '%q ' "${cmd[@]}")"

    confirm " Ready to launch " \
"\n$title\n\nCommand:\n  ${pretty}\n\nWorking directory:\n  ${WORKDIR}\n\nStart it now?" 18 || return 0

    if [[ -n "$TERM_EMU" ]] && \
       confirm " Where to run " "\nOpen ${title} in a new terminal window?\n\nNo  =  run here, in this terminal." 12; then
        launch_in_terminal "$title" "cd $(printf '%q' "$WORKDIR") && $pretty"
        echo -e "  ${GREEN}▶${NC} ${BOLD}${title}${NC} launched in a new window."
        sleep 1
        return 0
    fi

    clear
    echo -e "${GREEN}▶ ${BOLD}${title}${NC}"
    echo -e "${CYAN}  ${pretty}${NC}"
    echo ""
    # Keep the launcher alive when the tool is stopped with Ctrl-C. The trap is
    # reset to default in the child, so the tool still sees the signal.
    trap ':' INT
    ( cd "$WORKDIR" && "${cmd[@]}" )
    trap - INT
    echo ""
    read -rp "[Process exited — press Enter to return to the launcher] " _
}

# ── AVC.py configuration ─────────────────────────────────────────────────────

configure_avc() {
    local -a cmd=("$VENV_PY" "AVC.py")
    local choice value
    cfg_refresh   # so broker/interval/topic dialogs default to the saved config

    if ! command -v angryoxide &> /dev/null; then
        confirm " angryoxide missing " \
"\nThe angryoxide binary is not installed, so AVC.py cannot start it.\n\nRun 'sudo ./install.sh' to build and install it.\n\nContinue anyway?" 14 || return 0
    fi

    # 1. Interface selection
    choice=$(whiptail --title " AVC — interface " --menu \
"\nHow should the wireless interface be chosen?\n" "$H" "$W" 3 \
        "interactive"  "Prompt me to pick from detected interfaces" \
        "auto"         "Auto-select from interfaces.json" \
        "auto-custom"  "Auto-select from another JSON config file" \
        3>&1 1>&2 2>&3) || return 0

    case "$choice" in
        auto)
            cmd+=("-a" "interfaces.json")
            ;;
        auto-custom)
            value=$(ask_input " AVC — config file " \
"\nPath to the JSON config listing interfaces to try,\nin interfaces.json format:" "interfaces.json") || return 0
            [[ -n "$value" ]] || return 0
            if [[ ! -f "$WORKDIR/$value" && ! -f "$value" ]]; then
                confirm " File not found " "\n'$value' does not exist yet.\n\nUse it anyway?" 11 || return 0
            fi
            cmd+=("-a" "$value")
            ;;
    esac

    # 2. Output mode
    choice=$(whiptail --title " AVC — output " --menu \
"\nWhere should captured hashlines go?\n" "$H" "$W" 3 \
        "local"  "Local only — archive hash files to hashes/" \
        "kafka"  "Kafka only — publish to a broker" \
        "both"   "Local + Kafka — archive and publish" \
        3>&1 1>&2 2>&3) || return 0

    case "$choice" in
        local)
            cmd+=("-lo")
            ;;
        kafka|both)
            value=$(ask_input " AVC — Kafka broker " \
"\nKafka broker address as ip:port\n(publishing to topic '$(cfg_get topic)'):" "$(cfg_get broker)" \
                '^[A-Za-z0-9._-]+:[0-9]+$' "Enter an address in ip:port form, e.g. 192.168.1.100:9092") || return 0
            cmd+=("-b" "$value")
            [[ "$choice" == "both" ]] && cmd+=("-lo")
            ;;
    esac

    # 3. Scan interval (defaults to the configured interval)
    local def_interval; def_interval="$(cfg_get interval)"
    value=$(ask_input " AVC — scan interval " \
"\nHow often to check for new .hc22000 files, in seconds:" "$def_interval" \
        '^[1-9][0-9]*$' "The interval must be a whole number of seconds, 1 or more.") || return 0
    [[ "$value" == "$def_interval" ]] || cmd+=("-i" "$value")

    launch "AVC — Wi-Fi attack" "${cmd[@]}"
}

# ── AVC-CC.py configuration ──────────────────────────────────────────────────

configure_avc_cc() {
    local -a cmd=("$VENV_PY" "AVC-CC.py")
    local choice value creds ip_path user pass
    local saved_workdir="$WORKDIR"

    # 1. Working directory — .hc22000 files are found relative to it
    if [[ -d "$PROJECT_DIR/hashes" ]]; then
        choice=$(whiptail --title " AVC-CC — working directory " --menu \
"\nCracking looks for .hc22000 files in the working directory.\n" "$H" "$W" 2 \
            "root"    "Project root ($(find "$PROJECT_DIR" -maxdepth 1 -name '*.hc22000' | wc -l) hash files)" \
            "hashes"  "hashes/ folder ($(find "$PROJECT_DIR/hashes" -maxdepth 1 -name '*.hc22000' | wc -l) hash files)" \
            3>&1 1>&2 2>&3) || return 0
        [[ "$choice" == "hashes" ]] && WORKDIR="$PROJECT_DIR/hashes"
    fi

    # 2. Monitored outfile (required in every mode)
    value=$(ask_input " AVC-CC — hashcat outfile " \
"\nHashcat outfile to monitor for newly cracked passwords.\nIt does not have to exist yet:" "results.txt" \
        '^[^[:space:]]+$' "Enter a filename with no spaces.") || { WORKDIR="$saved_workdir"; return 0; }
    cmd+=("-o" "$value")

    # 3. Cracking mode
    choice=$(whiptail --title " AVC-CC — cracking " --menu \
"\nShould AVC-CC run hashcat itself?\n" "$H" "$W" 3 \
        "none"    "No — only watch the outfile" \
        "auto"    "Autocrack — every .hc22000 in the working directory" \
        "single"  "Single — crack one .hc22000 file" \
        3>&1 1>&2 2>&3) || { WORKDIR="$saved_workdir"; return 0; }

    case "$choice" in
        auto|single)
            if ! command -v hashcat &> /dev/null; then
                confirm " hashcat missing " \
"\nhashcat is not installed, so cracking cannot start.\n\nContinue anyway?" 12 || { WORKDIR="$saved_workdir"; return 0; }
            fi
            creds=$(ask_input " AVC-CC — credentials file " \
"\nWhere to append cracked results as ESSID:password :" "creds.txt" \
                '^[^[:space:]]+$' "Enter a filename with no spaces.") || { WORKDIR="$saved_workdir"; return 0; }
            ;;
    esac

    case "$choice" in
        auto)
            cmd+=("-ac" "$creds")
            ;;
        single)
            value=$(ask_input " AVC-CC — hash file " \
"\nThe .hc22000 file to crack (relative to the working\ndirectory, or an absolute path):" "" \
                '^[^[:space:]]+\.hc22000$' "The file name must end in .hc22000") || { WORKDIR="$saved_workdir"; return 0; }
            if [[ ! -f "$WORKDIR/$value" && ! -f "$value" ]]; then
                confirm " File not found " "\n'$value' was not found in $WORKDIR.\n\nUse it anyway?" 12 || { WORKDIR="$saved_workdir"; return 0; }
            fi
            cmd+=("-sc" "$value" "$creds")
            ;;
    esac

    # 4. Remote fetching
    choice=$(whiptail --title " AVC-CC — remote hosts " --menu \
"\nFetch result files from other hosts over SCP?\n" "$H" "$W" 3 \
        "none"    "No remote fetching" \
        "json"    "Use hash-targets.json" \
        "direct"  "Type one host, path and credentials" \
        3>&1 1>&2 2>&3) || { WORKDIR="$saved_workdir"; return 0; }

    case "$choice" in
        json)
            if [[ ! -f "$PROJECT_DIR/hash-targets.json" ]]; then
                msg " Missing config " "\nhash-targets.json was not found in the project root.\nEdit it first, then try again." 11
                WORKDIR="$saved_workdir"
                return 0
            fi
            cmd+=("-r" "$PROJECT_DIR/hash-targets.json")
            ;;
        direct)
            ip_path=$(ask_input " AVC-CC — remote target " \
"\nRemote host and file, as ip:/path/to/results.txt :" "" \
                '^[A-Za-z0-9._-]+:/.+$' "Use the form  ip:/path/to/file") || { WORKDIR="$saved_workdir"; return 0; }
            user=$(ask_input " AVC-CC — SSH user " "\nSSH username for $ip_path :" "" \
                '^[^[:space:]:]+$' "Enter a username with no spaces or colons.") || { WORKDIR="$saved_workdir"; return 0; }
            pass=$(ask_password " AVC-CC — SSH password " "\nSSH password for ${user}:") || { WORKDIR="$saved_workdir"; return 0; }
            cmd+=("-r" "$ip_path" "${user}:${pass}")
            ;;
    esac

    # 5. Monitoring cadence
    value=$(ask_input " AVC-CC — check interval " \
"\nMinutes between checks (decimals allowed):" "15" \
        '^[0-9]+(\.[0-9]+)?$' "Enter a number of minutes, e.g. 15 or 0.5") || { WORKDIR="$saved_workdir"; return 0; }
    [[ "$value" == "15" ]] || cmd+=("-i" "$value")

    value=$(ask_input " AVC-CC — notifications " \
"\nStop after this many 'new hashes cracked' notifications:" "5" \
        '^[1-9][0-9]*$' "Enter a whole number, 1 or more.") || { WORKDIR="$saved_workdir"; return 0; }
    [[ "$value" == "5" ]] || cmd+=("-n" "$value")

    # 6. Optional process name override
    if confirm " AVC-CC — hashcat process " \
"\nAVC-CC watches processes named hashcat, hashcat64.bin and\nhashcat32.bin.\n\nWatch a differently named binary instead?" 13; then
        value=$(ask_input " AVC-CC — process name " "\nProcess name to watch with pidof:" "hashcat" \
            '^[^[:space:]]+$' "Enter a process name with no spaces.") || { WORKDIR="$saved_workdir"; return 0; }
        cmd+=("-p" "$value")
    fi

    launch "AVC-CC — crack & comms" "${cmd[@]}"
    WORKDIR="$saved_workdir"
}

# ── Configuration menu ───────────────────────────────────────────────────────

configure_settings() {
    while true; do
        cfg_refresh
        local choice
        choice=$(whiptail --title " AVC — configuration (avc.conf) " --menu \
"\nPersistent defaults AVC.py reads at startup. Command-line flags still\noverride these per run. Current value shown in [brackets].\n" \
            "$H" "$W" 9 \
            "broker"    "Kafka broker address:port   [$(cfg_get broker)]" \
            "topic"     "Kafka topic                 [$(cfg_get topic)]" \
            "bands"     "Band targeting              [$(cfg_get_list bands)]" \
            "channels"  "Explicit channels           [$(cfg_get_list channels)]" \
            "sysid"     "System ID (Kafka sysId)     [$(cfg_get sysId)]" \
            "interval"  "Default scan interval (s)   [$(cfg_get interval)]" \
            "advanced"  "Advanced Kafka tunables ..." \
            "view"      "View full configuration" \
            "reset"     "Reset all settings to defaults" \
            3>&1 1>&2 2>&3) || return 0
        case "$choice" in
            broker)   cfg_edit_broker ;;
            topic)    cfg_edit_topic ;;
            bands)    cfg_edit_bands ;;
            channels) cfg_edit_channels ;;
            sysid)    cfg_edit_sysid ;;
            interval) cfg_edit_interval ;;
            advanced) cfg_edit_advanced ;;
            view)     cfg_view ;;
            reset)    cfg_reset ;;
        esac
    done
}

cfg_edit_broker() {
    local value
    value=$(ask_input " Config — Kafka broker " \
"\nDefault Kafka broker as ip:port, used when AVC.py publishes to Kafka:\n" "$(cfg_get broker)" \
        '^[A-Za-z0-9._-]+:[0-9]+$' "Enter an address in ip:port form, e.g. 192.168.1.100:9092") || return 0
    cfg_set broker str "$value"
}

cfg_edit_topic() {
    local value
    value=$(ask_input " Config — Kafka topic " \
"\nKafka topic hashes are published to:\n" "$(cfg_get topic)" \
        '^[A-Za-z0-9._-]+$' "Topic names may use letters, digits, dot, dash and underscore.") || return 0
    cfg_set topic str "$value"
}

cfg_edit_bands() {
    local current on2 on5 on6 on60 sel
    current=" $(cfg_get_list bands) "
    [[ "$current" == *" 2 "*  ]] && on2=ON  || on2=OFF
    [[ "$current" == *" 5 "*  ]] && on5=ON  || on5=OFF
    [[ "$current" == *" 6 "*  ]] && on6=ON  || on6=OFF
    [[ "$current" == *" 60 "* ]] && on60=ON || on60=OFF
    sel=$(whiptail --title " Config — band targeting " --checklist \
"\nScan every channel the interface supports in the selected bands.\nSPACE toggles, ENTER confirms. (Ignored while explicit channels are set.)\n" \
        "$H" "$W" 4 \
        "2"  "2.4 GHz" "$on2" \
        "5"  "5 GHz"   "$on5" \
        "6"  "6 GHz"   "$on6" \
        "60" "60 GHz"  "$on60" \
        3>&1 1>&2 2>&3) || return 0
    local -a arr
    read -ra arr <<< "$(echo "$sel" | tr -d '"')"
    if [[ ${#arr[@]} -eq 0 ]]; then
        msg " Band targeting " "\nSelect at least one band — leaving the bands unchanged." 10
        return 0
    fi
    cfg_set bands list "${arr[@]}"
}

cfg_edit_channels() {
    local current value
    current="$(cfg_get_list channels | tr ' ' ',')"
    value=$(ask_input " Config — explicit channels " \
"\nComma-separated channels to scan INSTEAD of whole bands,\ne.g. 1,6,11,36,149. Leave empty to scan by band.\n" "$current" \
        '^[0-9A-Za-z.,]*$' "Channel numbers separated by commas (band suffixes like 36.6e allowed).") || return 0
    if [[ -z "$value" ]]; then
        cfg_set channels list          # empty -> []  (back to band scanning)
    else
        local -a arr
        IFS=',' read -ra arr <<< "$value"
        cfg_set channels list "${arr[@]}"
    fi
}

cfg_edit_sysid() {
    local value
    value=$(ask_input " Config — system ID " \
"\nIdentifier sent in every Kafka message as 'sysId'\n(useful to tell capture rigs apart):\n" "$(cfg_get sysId)" \
        '^[^[:space:]]+$' "Enter an ID with no spaces.") || return 0
    cfg_set sysId str "$value"
}

cfg_edit_interval() {
    local value
    value=$(ask_input " Config — scan interval " \
"\nDefault seconds between hash-file scans (the -i flag overrides it):\n" "$(cfg_get interval)" \
        '^[1-9][0-9]*$' "Enter a whole number of seconds, 1 or more.") || return 0
    cfg_set interval int "$value"
}

cfg_edit_advanced() {
    while true; do
        cfg_refresh
        local choice value
        choice=$(whiptail --title " Config — advanced Kafka " --menu \
"\nResilience tunables for the offline queue.\n" "$H" "$W" 4 \
            "spool"   "Spool file (offline queue)  [$(cfg_get spool_file)]" \
            "connect" "Connect timeout ms          [$(cfg_get connect_timeout_ms)]" \
            "send"    "Send ack timeout s          [$(cfg_get send_timeout)]" \
            "back"    "Back" \
            3>&1 1>&2 2>&3) || return 0
        case "$choice" in
            spool)
                value=$(ask_input " Config — spool file " \
"\nFile that holds un-sent Kafka messages while the broker is down:\n" "$(cfg_get spool_file)" \
                    '^[^[:space:]]+$' "Enter a filename with no spaces.") || continue
                cfg_set spool_file str "$value" ;;
            connect)
                value=$(ask_input " Config — connect timeout " \
"\nMax milliseconds to block establishing/using the producer:\n" "$(cfg_get connect_timeout_ms)" \
                    '^[1-9][0-9]*$' "Enter a whole number of milliseconds.") || continue
                cfg_set connect_timeout_ms int "$value" ;;
            send)
                value=$(ask_input " Config — send timeout " \
"\nSeconds to wait for each message's broker acknowledgement:\n" "$(cfg_get send_timeout)" \
                    '^[1-9][0-9]*$' "Enter a whole number of seconds.") || continue
                cfg_set send_timeout int "$value" ;;
            back|"") return 0 ;;
        esac
    done
}

cfg_view() {
    local tmp; tmp="$(mktemp)"
    {
        if [[ -f "$CONFIG_FILE" ]]; then
            echo "Config file : $CONFIG_FILE"
        else
            echo "Config file : (none yet — built-in defaults; saving any"
            echo "              setting creates avc.conf)"
        fi
        echo ""
        echo "Effective settings AVC.py will use:"
        echo ""
        printf '%s\n' "$CFG_JSON"
    } > "$tmp"
    textfile " Current configuration " "$tmp"
    rm -f "$tmp"
}

cfg_reset() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        msg " Reset " "\nNo avc.conf present — already at built-in defaults." 9
        return 0
    fi
    confirm " Reset configuration " \
"\nDelete '$CONFIG_FILE' and return to built-in defaults?\n\nThis cannot be undone." 12 || return 0
    rm -f "$CONFIG_FILE"
    msg " Reset " "\nConfiguration reset to built-in defaults." 9
}

# ── Main menu ────────────────────────────────────────────────────────────────

main_menu() {
    whiptail --title "$TITLE" --menu \
"\nSelect a tool to configure and launch.\nArrow keys to move, ENTER to select, ESC to quit.\n" \
        "$H" "$W" 6 \
        "avc"     "$AVC_SUMMARY" \
        "avc-cc"  "$AVC_CC_SUMMARY" \
        "config"  "Configuration — broker, bands/channels, sysId ..." \
        "about"   "About — what each tool does and what it needs" \
        "status"  "Status — interfaces, binaries and hash files" \
        "quit"    "Quit the launcher" \
        3>&1 1>&2 2>&3
}

while true; do
    CHOICE="$(main_menu)" || break
    case "$CHOICE" in
        avc)     configure_avc ;;
        avc-cc)  configure_avc_cc ;;
        config)  configure_settings ;;
        about)   show_about ;;
        status)  show_status ;;
        quit)    break ;;
    esac
done

echo -e "${GREEN}Happy hunting.${NC}"
