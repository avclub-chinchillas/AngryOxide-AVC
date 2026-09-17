# AngryOxide 😡 AVClub Version

### A 802.11 Attack Tool

**This tool is for research purposes only. I am not responsible for anything you do or damage you cause. Only use against networks you have permission to test.**

This repo pairs the [AngryOxide](https://github.com/Ragnt/AngryOxide) Rust attack tool with two Python drivers:

| Script | Version | Purpose |
| --- | --- | --- |
| `AVC.py` | 0.7a | Wi-Fi attack orchestrator — monitor mode, AngryOxide, hash collection/exfil |
| `AVC-CC.py` | 0.1a | Crack & Comms — hashcat monitoring, remote hash fetching, auto-cracking |
| `avc-launcher.sh` | 1.0 | TUI launcher — describes both tools and builds their command lines for you |

The overall goal of this tool is to provide a single-interface survey capability with advanced automated attacks that result in valid hashlines you can crack with [Hashcat](https://hashcat.net/hashcat/).

---

## TUI Launcher

If you would rather not remember flags, start here:

```bash
sudo ./avc-launcher.sh
```

A whiptail menu that describes both tools and builds their command lines for you:

- **AVC** — walks through interface selection, output mode (local / Kafka / both), broker address and scan interval
- **AVC-CC** — working directory, outfile, cracking mode, credentials file, remote fetching (JSON or typed-in host + SSH credentials), check interval, notification count and process name
- **About** — full description of what each tool does, what it needs, and what it writes
- **Status** — angryoxide and hashcat presence, venv health, wireless interfaces, whitelist entries, hash file counts

Every input is validated as you type, and the exact command is shown for confirmation before anything runs. The launcher re-runs itself under `sudo`, runs the tools from the project directory inside `avc-venv`, and returns to the menu when a tool exits.

It runs the selected tool in the current terminal by default, so it works over SSH. When a desktop session and a terminal emulator are available (gnome-terminal, xfce4-terminal, mate-terminal, lxterminal, konsole or xterm) it offers to open a separate window instead.

Requires `whiptail` (`sudo apt-get install whiptail`) and a completed `sudo ./install.sh`.

---

## AVC.py — Attack Orchestrator

### Features

- **Interactive or Auto Interface Selection**: Manually select from detected interfaces or auto-select the first match from a JSON config
- **Automatic Monitor Mode**: Enables monitor mode on the selected interface via `ip`/`iw`
- **AngryOxide Integration**: Runs `angryoxide` headless as a background subprocess
- **Flexible Output Modes**:
  - Archive hash files to a `hashes` folder (default)
  - Publish to a Kafka topic
  - Both local and Kafka simultaneously
- **Hash Exfiltration**: Polls for `.hc22000` files and reports each hashline once, including handshakes appended to a file it has already seen
- **Whitelist Support**: Edit `whitelist.txt` to list BSSIDs or SSIDs to leave alone
- **Configurable Intervals**: Set the hash-scan interval via command-line argument
- **Startup Cleanup**: Runs `cleanup.sh` to clear stale capture artifacts before each run

### Usage

```bash
source avc-venv/bin/activate
python3 AVC.py [OPTIONS]
```

Run it **from the project root as your normal user**. The script shells out to `sudo` for the privileged steps (`ip link`, `iw`, `angryoxide`), so you will be prompted for a password. It also resolves `cleanup.sh`, `whitelist.txt`, and `interfaces.json` relative to the working directory.

The script will:
1. Run `./cleanup.sh` to delete stale artifacts from the working directory (see warning below)
2. Select an interface (auto from JSON or interactive prompt)
3. Enable monitor mode on the selected interface
4. Create a `hashes` folder if using local output mode
5. Start AngryOxide in the background (headless), loading `whitelist.txt` if present
6. Scan the working directory for `.hc22000` hash files every `<INTERVAL>` seconds
7. Extract ESSID and BSSID from each hash filename (`essid_BSSID.hc22000`)
8. Print each new hashline, publish it to Kafka if a broker was configured, and copy the file into `hashes/` in local mode
9. Press `Ctrl-C` to terminate AngryOxide and shut down gracefully

> **⚠️ `cleanup.sh` is destructive.** On every startup it runs `sudo rm` against `oxide-*`, `scan-*`, `*.kismet`, `*.kismet-journal`, and `*.hc22000` in the current directory. Move any captures you want to keep out of the project root before starting a new run. Files already inside `hashes/` are not touched.

### Output Modes

AngryOxide writes `.hc22000` files into the working directory, so that is always where AVC.py looks. The flags decide what happens to each hashline it finds:

| Mode | Flags | Archived to `hashes/` | Published to Kafka |
| --- | --- | --- | --- |
| Local Only (default) | none or `-lo` | Yes | No — hashlines are printed only |
| Kafka Only | `-b <broker>` | No | Yes |
| Local + Kafka | `-b <broker> -lo` | Yes | Yes |

Archiving copies the file, so AngryOxide keeps appending to the original and the copy in `hashes/` survives the next `cleanup.sh` run.

Each hashline is reported once per run — de-duplication is by hashline rather than by filename, so extra handshakes appended to a file already on disk are still picked up. Restarting re-processes whatever hash files remain in the working directory.

### Command-Line Options

```
-b, --broker BROKER       Kafka broker address (ip:port), e.g., 192.168.1.100:9092
-i, --interval SECONDS    Scan interval in seconds (default: 5)
-a, --auto [CONFIG.JSON]  Auto-select interface from JSON config file (default: interfaces.json)
-lo, --local              Save hashes to local "hashes" folder (default if no -b)
-h, --help                Show help message
```

### Examples

```bash
# Interactive mode with default local output
python3 AVC.py

# Auto-select interface from default interfaces.json
python3 AVC.py -a

# Auto-select interface from custom config
python3 AVC.py -a myconfig.json

# Publish to Kafka
python3 AVC.py -b 192.168.1.100:9092

# Custom scan interval
python3 AVC.py -i 10

# Auto-select and publish to Kafka
python3 AVC.py -a -b 192.168.1.100:9092

# Local output only (explicit)
python3 AVC.py -lo

# Local output + Kafka publishing
python3 AVC.py -b 192.168.1.100:9092 -lo
```

### Interface Configuration

Edit `interfaces.json` to configure which interfaces to use with auto-select mode:

```json
{
  "interfaces": ["wlan0", "wlan1", "wlan2"]
}
```

Or use a simple array:

```json
["wlan0", "wlan1", "wlan2"]
```

The program lists wireless interfaces with `iwconfig` and selects the first configured interface that is actually present. If none match, it prints the available interfaces and exits.

**Using custom config files:** You can create additional config files and specify them with `-a myconfig.json`. The program will use the format from `interfaces.json` for any custom config file.

### Whitelist

`whitelist.txt` holds one MAC or SSID per line to exclude from attacks; `#` starts a comment.

```
# example
AA:BB:CC:DD:EE:FF
```

The file is passed to AngryOxide with `--whitelist`. If it is missing, AVC.py says so and starts without a whitelist rather than letting AngryOxide abort. Change the path with the `WHITELIST_FILE` constant in `AVC.py`.

### Fixed AngryOxide Settings

AVC.py launches AngryOxide with a fixed argument set. To change any of these, edit the `angryoxide_cmd` list in `AVC.py`:

- Channels: `-c 1,2,3,4,5,6,7,8,10,11,12,13` (2.4 GHz only; note channel 9 is omitted)
- Attack rate: `-r 3` (most aggressive)
- Mode: `--headless --notar` (no TUI, no tarball of output files)
- Whitelist: `--whitelist whitelist.txt` (when the file exists)

No `-o` prefix is passed, so captures use AngryOxide's default `oxide` prefix — which is what `cleanup.sh` expects to find.

The Kafka `sysId` value is the `sysId` constant near the top of `AVC.py` (default: `Attack1`), and the archive folder is the `ARCHIVE_DIR` constant (default: `hashes`).

### Kafka Output Format

Hashes are published to the `wifi-hash` topic (see `kafka_fields.txt`) with the following fields:

- `sysId`: System identifier (hardcoded constant in `AVC.py`)
- `timestamp`: Time the hash was read, `YYYY-MM-DD HH:MM:SS`
- `essid`: Network SSID, parsed from the hash filename — sanitized by AngryOxide, so spaces and `:/\|?*<>"+` become `_`
- `bssid`: Access point MAC, parsed from the hash filename — 12 lowercase hex characters with no separators (e.g. `aabbccddeeff`), or `unknown` if the filename has no `_`
- `hash`: WPA/WPA2 hashline (Hashcat 22000 format)

Filenames are `<essid>_<bssid>.hc22000` and are split on the **last** underscore, so SSIDs containing underscores still parse correctly.

One message is published per hashline in the file. Kafka failures are logged and skipped — they do not stop the scan loop.

### Quick Compatibility Check

**Linux**: Full support on all distributions with nl80211 drivers (Ubuntu 24.04 tested)

---

## Known Issues

| Issue | Effect | Workaround |
| --- | --- | --- |
| `cleanup.sh` runs on every AVC.py startup | Deletes `*.hc22000`, `*.kismet`, `*.kismet-journal`, `scan-*`, and `oxide-*` from the project root | Files already archived in `hashes/` are safe; otherwise move captures elsewhere before restarting, or comment out the `cleanup.sh` call in `AVC.py` |

---

## Install Requirements

```bash
git clone https://github.com/avclub-chinchillas/AngryOxide-AVC
cd AngryOxide-AVC
chmod +x install.sh # Make executable
sudo ./install.sh # Full end-to-end installation
```

One command does everything: apt packages, the Rust toolchain, the build, the binary, completions, and the Python environment. **The install is idempotent** — re-run it any time to update or repair, and it only does the work that is still missing (skipped steps are reported with `[=]`).

`sudo ./install.sh help` lists the commands; `sudo ./install.sh uninstall` removes just the binary and completions.

### What the installer does

**1. System dependencies** (via apt, skipping what is already installed)

| Group | Packages | On failure |
| --- | --- | --- |
| Runtime | `python3`, `python3-venv`, `python3-pip`, `sshpass`, `wireless-tools`, `iw`, `curl`, `whiptail` | Install aborts |
| Build | `build-essential`, `pkg-config`, `libssl-dev`, `git` | Install aborts |
| Optional | `hashcat`, `wordlists` (for `AVC-CC.py` cracking) | Warns and continues |

**2. Rust toolchain** — reuses any cargo already on the system (including one installed under the invoking user's `~/.cargo`) as long as it meets the `rust-version = 1.87` floor from `Cargo.toml`. The build needs **Rust 1.87 or newer** (the code uses `u32::is_multiple_of`, stabilized in 1.87, plus `Option::is_none_or` and `std::iter::repeat_n` from 1.82). Distro packages are almost always older than that, so unless the apt candidate already satisfies the floor the installer skips apt and installs a current toolchain via rustup — system-wide under `/usr/local/rustup`, symlinked into `/usr/local/bin`, with `RUSTUP_HOME` exported from `/etc/profile.d/rust-avc.sh`. To build by hand you need the same: `rustup update stable`, or any toolchain ≥ 1.87.

**3. Build** — `cargo build --release`. The first build takes several minutes; later runs are incremental no-ops. When the build runs as root, `target/` is handed back to the invoking user afterwards so you can run cargo yourself later.

**4. Binary and completions** — installs `target/release/angryoxide` to `/usr/bin/` (skipped when the installed copy is already identical) plus bash and zsh completions. If no toolchain could be installed but a prebuilt binary exists in the project root or `target/`, that is used instead; with neither, the install fails loudly rather than finishing without a binary.

**5. Python environment** — creates the `avc-venv` virtual environment as root and installs `requirements.txt` (pandas, kafka-python-ng) into it.

It finishes by verifying that `angryoxide --version` runs and that `pandas` and `kafka` import from the venv, reporting any problems in the summary.

No manual apt, cargo, or pip commands needed.

> `sudo make install` remains as an alternative that installs an already-built binary from `target/release/` plus completions, but it does not install dependencies, build, or set up the venv.

### Running the Program

After installation, activate the virtual environment and run the program:

```bash
source avc-venv/bin/activate
python3 AVC.py [OPTIONS]
```

Or run it directly with the venv's Python:

```bash
./avc-venv/bin/python3 AVC.py [OPTIONS]
```

`avc-venv` is owned by root. Any user can activate it and run the scripts, but adding packages to it needs `sudo` — or re-run `sudo ./install.sh` after editing `requirements.txt`.

### Uninstalling

Use the dedicated uninstall script for a complete cleanup:

```bash
sudo ./uninstall.sh
```

It prompts for confirmation, then removes:
- `angryoxide` binary from `/usr/bin/`
- Bash and Zsh shell completions
- Python virtual environment (`avc-venv`)
- Python cache files (`__pycache__`, `.pyc`, `.pyo`)
- Hashes folder and captured hash files
- `.egg-info` directories

To also remove config files and the entire project directory:

```bash
rm -rf /path/to/AngryOxide-AVC
```

**Alternative (deprecated):** You can also use `sudo ./install.sh uninstall` or `sudo make uninstall`, but these only remove the binary and completions, not the venv and Python cache files.

---

## AVC-CC.py — Cracking Checker

Monitor hashcat cracking progress locally or fetch results from remote hosts:

```bash
python3 AVC-CC.py -o <hashcat_outfile> [OPTIONS]
```

### Prerequisites

- `-o/--outfile` is **required in every mode**, including the cracking modes.
- `.hc22000` files are discovered in the **current working directory**, not in `hashes/`. Run AVC-CC from wherever the hashes live (e.g. `cd hashes`) or pass an explicit path to `-sc`.
- `sshpass` must be installed for remote fetching, and `hashcat` plus a wordlist for cracking.

An already-running hashcat is **not** required. On startup AVC-CC runs `pidof` against `hashcat`, `hashcat64.bin`, and `hashcat32.bin` (override with `-p`, repeatable) and behaves as follows:

| Situation | Behavior |
| --- | --- |
| A hashcat process is found | Monitors it, and exits once every PID it started with is gone |
| None found, `-ac`/`-sc` given | Starts its own cracking processes and exits when they all finish |
| None found, monitoring only | Warns, then keeps watching the outfile (which may not exist yet) |

Cracking processes AVC-CC starts itself never count as the "original" hashcat run, so they cannot trigger the stopped-process exit.

### Local Monitoring

Monitor hashcat results on the local machine:

```bash
python3 AVC-CC.py -o results.txt
python3 AVC-CC.py -o results.txt -i 10 -n 5
```

Each interval it reports whether the outfile grew, and stops after `-n` notifications.

### Remote Monitoring

Fetch cracked passwords from remote hosts via SCP and append them to the monitored outfile:

**Option 1: Direct remote address**
```bash
python3 AVC-CC.py -r 192.168.1.100:/path/to/results.txt user:password -o results.txt
```

**Option 2: JSON configuration file**
```bash
python3 AVC-CC.py -r hash-targets.json -o results.txt
```

### Options

- `-o, --outfile` — Hashcat output file to monitor (required)
- `-i, --interval` — Check interval in minutes, accepts fractions (default: 15)
- `-n, --notification-count` — Number of notifications before exit (default: 5)
- `-p, --process-name` — hashcat process name to monitor, repeatable (default: `hashcat`, `hashcat64.bin`, `hashcat32.bin`)
- `-r, --remote` — Remote target(s) for SCP transfer:
  - Direct format: `-r IP:filepath username:password` (both arguments required)
  - JSON format: `-r hash-targets.json` (credentials come from the file)
- `-ac, --autocrack` — Auto-crack all `.hc22000` files in the current directory (optional: credentials filename, default: `creds.txt`)
- `-sc, --singlecrack` — Crack a single `.hc22000` file (required: hashfile, optional: credentials file, default: `creds.txt`)

### Auto-Cracking Feature

Enable automatic WPA2 password cracking with the `-ac/--autocrack` flag to crack all available hashes:

```bash
# Crack all .hc22000 files, save results to creds.txt (default)
python3 AVC-CC.py -o results.txt -ac

# Save cracked credentials to custom file
python3 AVC-CC.py -o results.txt -ac passwords.txt

# Combine with remote fetching and auto-cracking
python3 AVC-CC.py -r hash-targets.json -o results.txt -ac
```

### Single File Cracking

Crack a specific `.hc22000` file with the `-sc/--singlecrack` flag:

```bash
# Crack single file, save to default creds.txt
python3 AVC-CC.py -o results.txt -sc network.hc22000

# Crack single file, save to custom output
python3 AVC-CC.py -o results.txt -sc network.hc22000 cracked.txt

# Combine with remote fetch and single crack
python3 AVC-CC.py -r hash-targets.json -o results.txt -sc network.hc22000 passwords.txt
```

### Cracking Behavior

When auto-cracking (`-ac`) or single-cracking (`-sc`) is enabled, AVC-CC will:
1. Find or verify the `.hc22000` file(s) in the current directory
2. Start hashcat subprocess(es): `hashcat -a 0 -m 22000 <hashfile> <wordlist> -o cracked_<name>.txt`
3. Poll the subprocesses once per `-i` interval while monitoring the main outfile
4. Extract ESSID (from the filename) and cracked password when a process exits
5. Append results to the credentials file in the format `ESSID:password`
6. Skip files that already have a `cracked_*.txt` output (for `-sc`, read the existing result instead)

**Output file format (creds.txt):**
```
NetworkName:MyPassword123
GuestNetwork:SecurePass456
Corporate:P@ssw0rd!
```

**Requirements for cracking:**
- `hashcat` must be installed
- Wordlist file (hardcoded default: `/usr/share/wordlists/rockyou.txt` — edit the `wordlist` default in `AVC-CC.py` to change it)
- Sufficient GPU/CPU resources for cracking

### Remote Configuration (hash-targets.json)

Edit `hash-targets.json` to configure remote targets:

```json
[
  {
    "ip": "192.168.1.100",
    "filepath": "/path/to/hashcat/results.txt",
    "username": "user",
    "password": "password"
  },
  {
    "ip": "192.168.1.101",
    "filepath": "/path/to/hashcat/results.txt",
    "username": "user",
    "password": "password"
  }
]
```

A `{"targets": [...]}` wrapper object is also accepted. Fetched files are written locally as `remote_<ip>_<filename>` before their contents are appended to the monitored outfile.

**Requirements for remote functionality:**
- `sshpass` must be installed: `sudo apt-get install sshpass`
- SSH credentials must be valid
- Remote hosts must have SSH server running
- SCP runs with `StrictHostKeyChecking=no` and a 30-second timeout
