import subprocess
import time
import sys
import csv
import pandas as pd
import re
import os
import json
#from kafka import KafkaProducer
from gps_handler import read_gps

# ======================
# Global Configurations
# ======================

WELCOME_MESSAGE = \
  r">>============================================<<" + "\n"\
+ r"||     _    ___               ___     ______  ||"  + "\n"\
+ r"||    / \  / _ \             / \ \   / / ___| ||"  + "\n"\
+ r"||   / _ \| | | |  _____    / _ \ \ / / |     ||"  + " by dr0pp1n\n"\
+ r"||  / ___ \ |_| | |_____|  / ___ \ V /| |___  ||"  + " Version 0.5a\n"\
+ r"|| /_/   \_\___/          /_/   \_\_/  \____| ||"  + " Build 251016\n"\
+ r"||                                            ||"  + "\n"\
+ r">>============================================<<"  + "\n"\
+ "[*] AngryOxide-AVClub Wi-Fi Scan Tool starting up...\n"\
+ "[!] wlan0mon runs airodump-ng and wlan1mon runs AngryOxide! Ensure interfaces are started.\n"\
+ "[!] Send SIGINT (Ctrl-C) to exit.\n"

MODULE_INTERVAL = 5  # Interval in seconds to run attack modules
SCAN_INTERFACE = 'wlan0mon'  # Interface for scanning Wi-Fi networks
ATTACK_INTERFACE = 'wlan1mon'  # Interface for attacks

# ======================
# Helper Functions
# ======================

def check_monitor_interfaces(timeout=0, interval=1, targets=[SCAN_INTERFACE, ATTACK_INTERFACE]):
    """
    Check for monitor-mode interfaces wlan0mon and wlan1mon on Linux (Ubuntu 24.04).
    Returns a dict: {'wlan0mon': bool, 'wlan1mon': bool}.
    If timeout>0, retry until timeout seconds elapse (interval seconds between checks).
    """
    deadline = time.time() + timeout if timeout and timeout > 0 else None

    while True:
        found = {iface: os.path.exists(f'/sys/class/net/{iface}') for iface in targets}
        # if no deadline, or both found, or timeout reached -> return result
        if deadline is None or all(found.values()) or (deadline is not None and time.time() >= deadline):
            return found
        time.sleep(interval)

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

def open_gps(file_path):
    """Opens a GPS JSON file and returns its contents as a list of lists."""
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def list_to_df(data):
    """Converts a list of lists into a pandas DataFrame.
    Searches for "Station MAC in Column 2 to split DataFrames."""
    # Remove empty/blank rows
    clean = [row for row in data if not is_blank_row(row)]
    if not clean:
        return pd.DataFrame()  # Return empty DataFrame if data is empty
    headers = clean[0]
    rows = clean[1:]
    df = pd.DataFrame(rows, columns=headers)
    return df

def split_dataframe_on_marker(df, marker='Station MAC', col_index=None):
    """
    Split a DataFrame into two parts where a row indicates the start of a new table.
    - If col_index is provided, checks only that column for the marker.
    - Otherwise searches any column for the marker.
    Returns (top_df, bottom_df). If marker not found, returns (df, empty_df).
    """
    if df is None or df.empty:
        return df, pd.DataFrame()

    # Try a strict check on the requested column first (if provided),
    # then fallback to searching all columns. Comparison is whitespace-tolerant
    # and case-insensitive, and accepts partial matches (e.g. " Station MAC ").
    mask = pd.Series(False, index=df.index)

    if col_index is not None:
        try:
            col = df.iloc[:, col_index].astype(str).str.strip()
            mask = col.eq(marker) | col.str.contains(re.escape(marker), case=False, na=False)
        except Exception:
            mask = pd.Series(False, index=df.index)

    if not mask.any():
        # Search every column for the marker (case-insensitive, trimmed)
        try:
            mask = df.astype(str).apply(lambda c: c.str.strip().str.contains(re.escape(marker), case=False, na=False)).any(axis=1)
        except Exception:
            mask = pd.Series(False, index=df.index)

    if not mask.any():
        return df, pd.DataFrame()

    # Find first matching row position
    match_idx = mask[mask].index[0]
    pos = df.index.get_loc(match_idx)

    # The matching row is the header for the bottom table
    header_row = df.iloc[pos].tolist()

    # Top table: rows before the marker row
    top_df = df.iloc[:pos].reset_index(drop=True)

    # Bottom table: rows after the marker row; apply header_row as columns
    bottom_df = df.iloc[pos+1:].reset_index(drop=True)
    if not bottom_df.empty:
        # Make header_row match number of bottom columns (pad or truncate)
        if len(header_row) != bottom_df.shape[1]:
            if len(header_row) < bottom_df.shape[1]:
                header_row = header_row + [f'col{i}' for i in range(len(header_row), bottom_df.shape[1])]
            else:
                header_row = header_row[:bottom_df.shape[1]]
        bottom_df.columns = [str(h).strip() for h in header_row]

    return top_df, bottom_df

# ======================
# Main Function
# ======================
def main():
    print("[*] Cleaning up...")
    subprocess.run(["./cleanup.sh"])

    print('[*] Looking for wlan0mon and wlan1mon...')
    found = check_monitor_interfaces(timeout=3, interval=1)
    print(f"[*] Monitor interfaces found: {found}")

    print("[*] Starting attack modules...")
    ### Start AngryOxide subprocess
    if found.get(ATTACK_INTERFACE):
        print(f"[*] Starting AngryOxide on {ATTACK_INTERFACE}...")
        angryoxide = subprocess.Popen('sudo','angryoxide','-i',ATTACK_INTERFACE,'-c','1,2,3,4,5,6,7,8,10,11,12,13','-w','whitelist.txt','-r','3','--headless','--notar',
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[*] Started AngryOxide with PID {angryoxide.pid}")

    ### Start airodump-ng subprocess
    if found.get(SCAN_INTERFACE):
        print(f"[*] Starting airodump-ng on {SCAN_INTERFACE}...")
        airodump = subprocess.Popen(['sudo','airodump-ng', SCAN_INTERFACE, '--gpsd', '-w','scan'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(f"[*] Started airodump-ng with PID {airodump.pid}")

    ### Start Kafka producer subprocess
    #producer = KafkaProducer(bootstrap_servers='localhost:9092')

    ### Main loop
    while True:
        try:
            print(f"[*] Running data scans every {MODULE_INTERVAL} seconds...")
            time.sleep(MODULE_INTERVAL)
            wifi_data = open_csv('scan-01.csv')
            gps_data = open_gps('scan-01.gps')
            print(gps_data)
            wifi_data = list_to_df(wifi_data)
            ap_data, station_data = split_dataframe_on_marker(wifi_data, marker='Station MAC', col_index=1)
            print('[*] airodump AP output:\n', ap_data)
            print('[*] airodump STA output:\n', station_data)
            print('[*] GPS Reading: ', read_gps())
            #producer.send('wifi_data', wifi_data)
            subprocess.run(["./exfil_hash.sh"])

        except Exception or KeyboardInterrupt:
            if Exception:
                print(f"[!] Exception occurred: {Exception}")
            else:
                print("\n[!] SIGINT detected (Ctrl-C), shutting down gracefully...")
                print("[*] Terminating subprocesses...")
                if airodump:
                    airodump.terminate()
                if angryoxide:
                    angryoxide.terminate()

# ======================
# Main Loop
# ======================

if __name__ == "__main__":
    try:
        print(WELCOME_MESSAGE)
        main()
    except Exception or KeyboardInterrupt:
        if Exception:
            print(f"[!] Fatal error: {Exception}")
            sys.exit(0)
        else:
            print("\n[!] SIGINT detected (Ctrl-C), exiting...")
            sys.exit(0)
