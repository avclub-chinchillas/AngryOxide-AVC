import subprocess
import time
import sys
import csv
import pandas as pd
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
+ r"||  / ___ \ |_| | |_____|  / ___ \ V /| |___  ||"  + " Version 0.3a\n"\
+ r"|| /_/   \_\___/          /_/   \_\_/  \____| ||"  + " Build 251013\n"\
+ r"||                                            ||"  + "\n"\
+ r">>============================================<<"  + "\n"\
+ "[*] AngryOxide-AVClub Wi-Fi Scan Tool starting up...\n"\
+ "[!] Send SIGINT (Ctrl-C) to exit.\n"

EXFIL_INTERVAL = 3  # Interval in seconds to exfiltrate hashes
GPS_DEVICE = '/dev/ttyACM0'  # GPS device path

# ======================
# Helper Functions
# ======================

def read_csv(file_path):
    """Reads a CSV file and returns its contents as a list of dictionaries."""
    data = []
    data_row = []
    with open(file_path, mode='r') as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            for item in row:
                if item:  # Only add non-empty items
                    item = item.strip()
                    data_row.append(item)
            if data_row:  # Only add non-empty rows
                data.append(data_row)
            data_row = []
    return data

def list_to_df(data):
    """Converts a list of lists into a pandas DataFrame."""
    if not data:
        return pd.DataFrame()  # Return empty DataFrame if data is empty
    headers = data[0]
    rows = data[1:]
    df = pd.DataFrame(rows, columns=headers)
    return df
    
def transform_wifi_data(data):
    """Transforms raw Wi-Fi data into a structured format."""
    print(data)
    transformed = []
    for entry in data:
        transformed_entry = {
            'BSSID': entry.get('BSSID', ''),
            'ESSID': entry.get('ESSID', ''),
            'Channel': entry.get('channel', ''),
            'Signal': entry.get('power', ''),
            'Encryption': entry.get('Privacy', ''),
            'Last Seen': entry.get('last seen', '')
        }

# ======================
# Main Function
# ======================
def main():
    print("[*] Cleaning up...")
    subprocess.run(["./cleanup.sh"])

    print("[*] Starting attack modules...")
    ### Start AngryOxide subprocess
    #am1 = "./AgOx.sh"
    #am1p = subprocess.Popen([am1], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    #print(f"[*] Started AngryOxide with PID {am1p.pid}")
    
    ### Start airodump-ng subprocess
    am2 = "./airodump.sh"
    am2p = subprocess.Popen([am2], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[*] Started airodump-ng with PID {am2p.pid}")

    ### Start Kafka producer subprocess
    #producer = KafkaProducer(bootstrap_servers='localhost:9092')
    time.sleep(1)
    print(f"[*] Exfiltrating hashes every {EXFIL_INTERVAL} seconds...")
    while True:
        try:
            wifi_data = read_csv('airfile-01.csv')
            wifi_data = list_to_df(wifi_data)
            #print(transform_wifi_data(wifi_data))
            print(read_gps(GPS_DEVICE))
            #producer.send('wifi_data', wifi_data)

            subprocess.run(["./exfil_hash.sh"])
            time.sleep(EXFIL_INTERVAL)
        except Exception or KeyboardInterrupt:
            if Exception:
                print(f"[!] Exception occurred: {Exception}")
            else:
                print("\n[!] SIGINT detected (Ctrl-C), shutting down gracefully...")
                print("[*] Terminating subprocesses...")
                #am1p.terminate()
                am2p.terminate()

# ======================
# Main Loop
# ======================
if __name__ == "__main__":
    try:
        print(WELCOME_MESSAGE)
        main()
    except Exception as e:
        print(f"[!] Fatal error: {e}")
        sys.exit(0)
