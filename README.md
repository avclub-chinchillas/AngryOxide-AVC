# AngryOxide 😡 AVClub Version

### A 802.11 Attack Tool

**This tool is for research purposes only. I am not responsible for anything you do or damage you cause. Only use against networks you have permission to test.**

### Usage

```bash
python3 AVC.py
```
Edit `whitelist.txt` to add BSSIDs to ignore.

### Quick Compatibility Check

**Linux**: Full support on all distributions with nl80211 drivers

The overall goal of this tool is to provide a single-interface survey capability with advanced automated attacks that result in valid hashlines you can crack with [Hashcat](https://hashcat.net/hashcat/).

## Install Requirements

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