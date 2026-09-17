# AngryOxide 😡 AVClub Version

### A 802.11 Attack Tool

**This tool is for research purposes only. I am not responsible for anything you do or damage you cause. Only use against networks you have permission to test.**

This repo pairs the [AngryOxide](https://github.com/Ragnt/AngryOxide) Rust attack tool with two Python drivers:

| Script | Version | Purpose |
| --- | --- | --- |
| `AVC.py` | 0.7a | Wi-Fi attack orchestrator — monitor mode, AngryOxide, hash collection/exfil |
| `AVC-CC.py` | 0.1a | Crack & Comms — hashcat monitoring, remote hash fetching, auto-cracking |

The overall goal of this tool is to provide a single-interface survey capability with advanced automated attacks that result in valid hashlines you can crack with [Hashcat](https://hashcat.net/hashcat/).

---

## AVC.py — Attack Orchestrator

### Features

- **Interactive or Auto Interface Selection**: Manually select from detected interfaces or auto-select the first match from a JSON config
- **Automatic Monitor Mode**: Enables monitor mode on the selected interface via `ip`/`iw`
- **AngryOxide Integration**: Runs `angryoxide` headless as a background subprocess
- **Flexible Output Modes**:
  - Print hashlines locally, with AngryOxide's capture files kept on disk (default)
  - Publish to a Kafka topic
  - Both local and Kafka simultaneously
- **Hash Exfiltration**: Polls for new `.hc22000` files and publishes each hashline with metadata
- **Configurable Intervals**: Set the hash-scan interval via command-line argument
- **Startup Cleanup**: Runs `cleanup.sh` to clear stale capture artifacts before each run

See [Known Issues](#known-issues) before relying on the local-output or whitelist behavior.

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
5. Start AngryOxide in the background (headless)
6. Scan for `.hc22000` hash files every `<INTERVAL>` seconds
7. Extract ESSID and BSSID from each hash filename (`essid_BSSID.hc22000`)
8. Print each hashline and publish it to Kafka if a broker was configured
9. Press `Ctrl-C` to terminate AngryOxide and shut down gracefully

> **⚠️ `cleanup.sh` is destructive.** On every startup it runs `sudo rm` against `oxide-*`, `scan-*`, `*.kismet`, `*.kismet-journal`, and `*.hc22000` in the current directory. Move any captures you want to keep out of the project root before starting a new run. Files already inside `hashes/` are not touched.

### Output Modes

The flags select which directory AVC.py polls and whether it publishes to Kafka:

| Mode | Flags | Polled directory | Publishes to Kafka |
| --- | --- | --- | --- |
| Local Only (default) | none or `-lo` | `hashes/` | No — hashlines are printed only |
| Kafka Only | `-b <broker>` | project root | Yes |
| Local + Kafka | `-b <broker> -lo` | `hashes/` | Yes |

Each file is processed once per run; already-seen filenames are tracked in memory (restarting re-processes everything still on disk).

> **⚠️ AngryOxide always writes `.hc22000` files to the working directory, never into `hashes/`.** Its `-o` flag is an output *filename prefix*, not an output directory — it only renames the `.pcapng`/`.kismet` files. So in the two local modes AVC.py polls a `hashes/` folder that never receives anything. Only **Kafka Only** mode (`-b` with no `-lo`) polls the directory the hashes actually land in. See [Known Issues](#known-issues).

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

> **⚠️ The file is not currently loaded.** AVC.py passes it as `-w whitelist.txt`, but in AngryOxide `-w` is the short form of `--whitelist-entry`, which takes a literal MAC or SSID — so this whitelists a network *named* "whitelist.txt". Loading a file requires the long-only `--whitelist` flag. See [Known Issues](#known-issues).

### Fixed AngryOxide Settings

AVC.py launches AngryOxide with a fixed argument set. To change any of these, edit the `angryoxide_cmd` list in `AVC.py`:

- Channels: `-c 1,2,3,4,5,6,7,8,10,11,12,13` (2.4 GHz only; note channel 9 is omitted)
- Attack rate: `-r 3` (most aggressive)
- Mode: `--headless --notar` (no TUI, no tarball of output files)
- Whitelist entry: `-w whitelist.txt`
- Output prefix: `-o hashes` (local modes only — names the capture files `hashes.kismet` / `hashes-<timestamp>.pcapng`)

The Kafka `sysId` value is the `sysId` constant near the top of `AVC.py` (default: `Attack1`).

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

These are current behaviors of the code as committed, not configuration mistakes. Documented here so runs are not misread as "no networks found".

| # | Issue | Effect | Workaround |
| --- | --- | --- | --- |
| 1 | AVC.py polls `hashes/` in local modes, but AngryOxide writes `.hc22000` files to the working directory | Default (local) and `-lo -b` modes never see any hashes — nothing is printed or published | Use Kafka-only mode (`-b <broker>` without `-lo`), or move/symlink hashes into `hashes/`, or change `hash_dir` to `'.'` in `AVC.py` |
| 2 | `-w whitelist.txt` uses AngryOxide's `--whitelist-entry` short flag, which expects a literal MAC/SSID | `whitelist.txt` is never read; every network is in scope | Change the flag in `AVC.py` from `-w` to `--whitelist`, or pass each entry individually with repeated `-w` |
| 3 | `cleanup.sh` runs on every AVC.py startup | Deletes `*.hc22000`, `*.kismet`, `*.kismet-journal`, `scan-*`, and `oxide-*` from the project root | Archive captures elsewhere before restarting, or comment out the `cleanup.sh` call |
| 4 | `install.sh` copies `./angryoxide`, which is not in the repo | Install reports success while leaving no binary in `/usr/bin/` | Build first (see [Install Requirements](#install-requirements)) and verify with `which angryoxide` |
| 5 | AVC-CC.py exits immediately unless a process named `hashcat64.bin` is running | The script quits before monitoring or `-ac`/`-sc` cracking ever starts | Edit the `PROCESS_NAME` constant to match your hashcat binary name (e.g. `hashcat`) |

---

## Install Requirements

```bash
git clone https://github.com/avclub-chinchillas/AngryOxide-AVC
cd AngryOxide-AVC
```

### 1. Build the `angryoxide` binary

The repo ships the Rust source, not a prebuilt binary. `install.sh` copies `./angryoxide` from the project root, so build it and put it there first:

```bash
cargo build --release          # or: make build
cp target/release/angryoxide .
```

> If `./angryoxide` is missing, `install.sh` still reports success but the binary step silently fails and `AVC.py` will not be able to start AngryOxide. Verify with `which angryoxide` after installing.

Alternatively, `sudo make install` installs the binary straight from `target/release/` along with the shell completions (but does not set up the Python venv).

### 2. Run the installer

```bash
chmod +x install.sh # Make executable
sudo ./install.sh # Full automated installation
```

The install script will automatically:
- Install required system dependencies via apt (skipping already-installed ones):
  - `python3`, `python3-venv`, `python3-pip`
  - `sshpass` (for remote SCP functionality)
  - `wireless-tools`, `iw` (interface control)
  - `curl`
- Install optional packages for the cracking features, continuing if they are unavailable:
  - `hashcat`, `wordlists`
- Create a Python virtual environment (`avc-venv`)
- Install the `angryoxide` binary to `/usr/bin/`
- Install shell completions (bash and zsh)
- Install Python dependencies from `requirements.txt` (pandas, kafka-python-ng) into the venv

No manual apt or pip commands needed.

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

- **A hashcat process named `hashcat64.bin` must already be running.** On startup AVC-CC runs `pidof hashcat64.bin`; if nothing is found it prints `[-] hashcat is not running. Exiting.` and quits — including when you only wanted `-ac`/`-sc`. The monitored process name is the `PROCESS_NAME` constant at the top of `AVC-CC.py`; change it to match your hashcat binary (e.g. `hashcat`). The loop also exits as soon as that original PID goes away.
- `-o/--outfile` is **required in every mode**, including the cracking modes.
- `.hc22000` files are discovered in the **current working directory**, not in `hashes/`. Run AVC-CC from wherever the hashes live (e.g. `cd hashes`) or pass an explicit path to `-sc`.
- `sshpass` must be installed for remote fetching, and `hashcat` plus a wordlist for cracking.

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
