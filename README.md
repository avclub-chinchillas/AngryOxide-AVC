# AngryOxide 😡 AVClub Version

### A 802.11 Attack Tool

**This tool is for research purposes only. I am not responsible for anything you do or damage you cause. Only use against networks you have permission to test.**

### Features

- **Interactive Interface Selection**: Select which wireless interface to use for attacks
- **Automatic Monitor Mode**: Enables monitor mode on the selected interface
- **AngryOxide Integration**: Runs AngryOxide as a background subprocess
- **Hash Exfiltration**: Automatically exfils hashes via Kafka
- **Whitelist Support**: Edit `whitelist.txt` to add BSSIDs to ignore

### Usage

```bash
python3 AVC.py
```

The script will:
1. Display available wireless interfaces
2. Prompt you to select an interface
3. Enable monitor mode on the selected interface
4. Start AngryOxide in the background
5. Scan for hash files every <INTERVAL> seconds
6. Publish these hash pairs to a Kafka topic
7. Press `Ctrl-C` to gracefully shut down

### Quick Compatibility Check

**Linux**: Full support on all distributions with nl80211 drivers (Ubuntu 24.04 tested)

The overall goal of this tool is to provide a single-interface survey capability with advanced automated attacks that result in valid hashlines you can crack with [Hashcat](https://hashcat.net/hashcat/).

## Install Requirementsessid
bssid
hc22000 (bool)

```bash
git clone https://github.com/avclub-chinchillas/AngryOxide-AVC
chmod +x install.sh # Make executable
sudo ./install.sh # Install
```

```bash
sudo apt-get install python3-kafka
```

#### Uninstalling:

```bash
sudo ./install.sh uninstall # Uninstall
```