import subprocess
import time
import sys

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
# Main Function
# ======================
def main():
    print("[*] Cleaning up...")
    subprocess.run(["./cleanup.sh"])

    # Start AngryOxide subprocesses
    print("[*] Starting attack modules...")
    ao1 = "./attack_i1.sh"
    #ao2 = "./attack_i2.sh"
    ao1p = subprocess.Popen([ao1], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    #ao2p = subprocess.Popen([ao2], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    while True:
        try:
            print(f"[*] Exfiltrating hashes every {EXFIL_INTERVAL} seconds...")
            subprocess.run(["./exfil_hash.sh"])
            time.sleep(EXFIL_INTERVAL)
        except Exception as e:
            print(f"[!] Exception occurred: {e}")
            print("[*] Terminating subprocesses...")
            ao1p.terminate()
            #ao2p.terminate()

# ======================
# Main Loop
# ======================
if __name__ == "__main__":
    try:
        print(WELCOME_MESSAGE)
        main()
    except KeyboardInterrupt:

        print("\n[!] SIGINT detected (Ctrl-C), shutting down gracefully...")
        sys.exit(0)
