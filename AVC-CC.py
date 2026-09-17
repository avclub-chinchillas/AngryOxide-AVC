import argparse
import time
import json
import sys
from os import path
from subprocess import Popen, PIPE, run, DEVNULL

PROCESS_NAMES = ['hashcat', 'hashcat64.bin', 'hashcat32.bin']

DESC_MESSAGE = \
  r">>============================================<<" + "\n"\
+ r"||     _    ___               ___     ______  ||"  + "\n"\
+ r"||    / \  / _ \             / \ \   / / ___| ||"  + "\n"\
+ r"||   / _ \| | | |  _____    / _ \ \ / / |     ||"  + " by dr0pp1n\n"\
+ r"||  / ___ \ |_| | |_____|  / ___ \ V /| |___  ||"  + " Version 0.1a\n"\
+ r"|| /_/   \_\___/          /_/   \_\_/  \____| ||"  + " Build 260817\n"\
+ r"||                                            ||"  + " Crack & Comms\n"\
+ r">>============================================<<"  + "\n"

WELCOME_MESSAGE = DESC_MESSAGE \
+ "[*] AngryOxide-AVClub Cracking and Communications Tool starting up...\n"\
+ "[*] Monitoring hashcat progress and cracked passwords.\n"\
+ "[!] Send SIGINT (Ctrl-C) to exit.\n"

def check_pids(process_names):
    """Return the set of PIDs of any running hashcat process."""
    stdout = Popen('pidof ' + ' '.join(process_names), shell=True, stdout=PIPE).stdout
    output = stdout.read().rstrip().decode('utf-8')
    if output:
        return set(output.split())
    return set()


def check_file(hashcat_outfile):
    """Check number of lines in designated outfile."""
    if not path.isfile(hashcat_outfile):
        return False
    with open(hashcat_outfile) as file:
        i = 0
        for i, lines in enumerate(file):
            pass
    return i + 1

def load_targets_from_json(json_file):
    """Load remote targets from JSON configuration file."""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'targets' in data:
            return data['targets']
        else:
            print("[!] Invalid JSON format. Expected list or dict with 'targets' key.")
            return []
    except Exception as e:
        print(f"[!] Error loading JSON file: {e}")
        return []

def parse_remote_target(address, credentials=None):
    """Parse remote target in format 'ip:filepath' and credentials 'username:password'."""
    try:
        ip, filepath = address.rsplit(':', 1)
        if not credentials:
            print("[!] Credentials required for direct address format.")
            return None
        username, password = credentials.split(':', 1)
        return {'ip': ip, 'filepath': filepath, 'username': username, 'password': password}
    except Exception as e:
        print(f"[!] Error parsing remote target: {e}")
        return None

def scp_copy_file(ip, filepath, username, password, local_path):
    """Copy file from remote host via SCP using sshpass."""
    try:
        remote_path = f"{username}@{ip}:{filepath}"
        cmd = ['sshpass', '-p', password, 'scp', '-o', 'StrictHostKeyChecking=no',
               remote_path, local_path]
        print(f"[*] Copying from {remote_path} to {local_path}...")
        result = run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"[+] Successfully copied from {ip}:{filepath}")
            return True
        else:
            print(f"[!] Failed to copy from {ip}:{filepath}: {result.stderr}")
            return False
    except Exception as e:
        print(f"[!] Error during SCP transfer: {e}")
        return False

def fetch_remote_hashes(remote_targets):
    """Fetch hash files from remote targets via SCP."""
    print("[*] Fetching hash files from remote targets...")
    all_hashes = []

    for target in remote_targets:
        local_temp = f"remote_{target['ip']}_{path.basename(target['filepath'])}"
        if scp_copy_file(target['ip'], target['filepath'], target['username'],
                        target['password'], local_temp):
            try:
                with open(local_temp, 'r') as f:
                    all_hashes.extend(f.readlines())
            except Exception as e:
                print(f"[!] Error reading {local_temp}: {e}")

    return all_hashes

def find_hc22000_files(directory='.'):
    """Find all .hc22000 files in directory."""
    import os
    files = []
    for f in os.listdir(directory):
        if f.endswith('.hc22000'):
            files.append(f)
    return files

def extract_essid_from_filename(filename):
    """Extract ESSID from filename format: essid_BSSID.hc22000"""
    name_without_ext = filename[:-8]  # Remove .hc22000
    parts = name_without_ext.rsplit('_', 1)
    if len(parts) == 2:
        return parts[0]
    return name_without_ext

def start_hashcat_process(hash_file, wordlist, output_file):
    """Start a hashcat cracking subprocess."""
    try:
        cmd = ['hashcat', '-a', '0', '-m', '22000', hash_file, wordlist, '-o', output_file]
        process = Popen(cmd, stdout=DEVNULL, stderr=DEVNULL)
        print(f"[*] Started hashcat for {hash_file} (PID: {process.pid})")
        return process
    except FileNotFoundError:
        print("[!] hashcat not found. Please install hashcat.")
        return None
    except Exception as e:
        print(f"[!] Error starting hashcat: {e}")
        return None

def parse_hashcat_output(hashcat_outfile, essid):
    """Parse hashcat output file and extract password."""
    try:
        if not path.isfile(hashcat_outfile):
            return None
        with open(hashcat_outfile, 'r') as f:
            line = f.readline().strip()
            if line:
                parts = line.split(':')
                if len(parts) >= 2:
                    password = parts[-1]
                    return f"{essid}:{password}"
    except Exception as e:
        print(f"[!] Error parsing hashcat output: {e}")
    return None

def start_cracking_subprocesses(wordlist='/usr/share/wordlists/rockyou.txt'):
    """Start hashcat subprocesses for all .hc22000 files."""
    hc_files = find_hc22000_files()
    if not hc_files:
        print("[!] No .hc22000 files found to crack.")
        return {}

    hashcat_processes = {}
    for hc_file in hc_files:
        essid = extract_essid_from_filename(hc_file)
        output_file = f"cracked_{hc_file[:-8]}.txt"

        if path.isfile(output_file):
            print(f"[+] Already cracked: {hc_file}, skipping.")
            continue

        process = start_hashcat_process(hc_file, wordlist, output_file)
        if process:
            hashcat_processes[hc_file] = {
                'process': process,
                'essid': essid,
                'output_file': output_file
            }

    return hashcat_processes

def start_single_crack(hash_file, creds_file, wordlist='/usr/share/wordlists/rockyou.txt'):
    """Start cracking a single .hc22000 file."""
    if not path.isfile(hash_file):
        print(f"[!] Hash file not found: {hash_file}")
        return None

    essid = extract_essid_from_filename(hash_file)
    output_file = f"cracked_{path.basename(hash_file)[:-8]}.txt"

    if path.isfile(output_file):
        print(f"[+] Already cracked: {hash_file}, reading results...")
        password = parse_hashcat_output(output_file, essid)
        if password:
            write_cracked_credentials(creds_file, essid, password.split(':')[1])
        return None

    process = start_hashcat_process(hash_file, wordlist, output_file)
    if process:
        return {
            'hash_file': hash_file,
            'process': process,
            'essid': essid,
            'output_file': output_file,
            'creds_file': creds_file
        }
    return None

def write_cracked_credentials(creds_file, essid, password):
    """Write cracked credentials to output file."""
    try:
        with open(creds_file, 'a') as f:
            f.write(f"{essid}:{password}\n")
        print(f"[+] Cracked: {essid}:{password}")
        return True
    except Exception as e:
        print(f"[!] Error writing credentials: {e}")
        return False

def monitor_hashcat_processes(hashcat_processes, creds_file):
    """Monitor hashcat subprocesses and collect results."""
    completed = []
    for hc_file, proc_info in hashcat_processes.items():
        process = proc_info['process']
        if process.poll() is not None:
            print(f"[*] Hashcat process for {hc_file} completed.")
            password = parse_hashcat_output(proc_info['output_file'], proc_info['essid'])
            if password:
                write_cracked_credentials(creds_file, proc_info['essid'], password.split(':')[1])
            completed.append(hc_file)

    for hc_file in completed:
        del hashcat_processes[hc_file]

    return hashcat_processes

def monitor_single_crack_process(single_crack_process):
    """Monitor a single hashcat cracking process."""
    if single_crack_process is None:
        return None

    process = single_crack_process['process']
    if process.poll() is not None:
        print(f"[*] Hashcat process for {single_crack_process['hash_file']} completed.")
        password = parse_hashcat_output(single_crack_process['output_file'],
                                       single_crack_process['essid'])
        if password:
            write_cracked_credentials(single_crack_process['creds_file'],
                                     single_crack_process['essid'],
                                     password.split(':')[1])
        return None

    return single_crack_process

def main():
    """Take user input to setup notifications. Print status updates to terminal."""
    parser = argparse.ArgumentParser(
        description=DESC_MESSAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python3 AVC-CC.py -o results.txt
  python3 AVC-CC.py -o results.txt -i 10
  python3 AVC-CC.py -o results.txt -i 5 -n 10
  python3 AVC-CC.py -r 192.168.1.100:/path/to/results.txt user:password -o results.txt
  python3 AVC-CC.py -r hash-targets.json -o results.txt
  python3 AVC-CC.py -ac
  python3 AVC-CC.py -ac passwords.txt
  python3 AVC-CC.py -sc network.hc22000
  python3 AVC-CC.py -sc network.hc22000 cracked.txt
  python3 AVC-CC.py -r hash-targets.json -o results.txt -ac
  python3 AVC-CC.py -h
        '''
    )
    monitor_group = parser.add_argument_group('Monitoring Configuration')
    monitor_group.add_argument('-o', '--outfile', dest='hashcat_outfile', required=True, metavar='OUTFILE',
                               help='hashcat outfile to monitor (required)')
    monitor_group.add_argument('-i', '--interval', dest='check_interval', required=False, type=float,
                               default=15, metavar='MINUTES',
                               help='Interval in minutes between checks (default: 15)')
    monitor_group.add_argument('-n', '--notification-count', dest='notification_count', required=False,
                               type=int, default=5, metavar='COUNT',
                               help='Cease operation after N notifications (default: 5)')
    monitor_group.add_argument('-p', '--process-name', dest='process_names', action='append',
                               required=False, metavar='NAME',
                               help=f'hashcat process name to monitor, repeatable (default: {", ".join(PROCESS_NAMES)})')

    remote_group = parser.add_argument_group('Remote Configuration')
    remote_group.add_argument('-r', '--remote', dest='remote', nargs='*', default=None,
                              metavar=('ADDRESS/JSON', 'CREDENTIALS'),
                              help='Remote target(s) for SCP: either IP:path [credentials] or JSON config file')

    cracking_group = parser.add_argument_group('Automatic Cracking Configuration')
    cracking_group.add_argument('-ac', '--autocrack', dest='autocrack', nargs='?', const='creds.txt',
                                metavar='CREDS_FILE',
                                help='Auto-crack .hc22000 files with hashcat and save results (default: creds.txt)')
    cracking_group.add_argument('-sc', '--singlecrack', dest='singlecrack', nargs='*',
                                metavar=('HASHFILE', 'CREDS_FILE'),
                                help='Crack a single .hc22000 file (required: hashfile, optional: output file)')

    args = parser.parse_args()
    print(WELCOME_MESSAGE)

    hashcat_outfile = args.hashcat_outfile
    check_interval = args.check_interval
    notification_count = args.notification_count

    # Handle remote targets if specified
    remote_targets = None
    if args.remote is not None:
        if len(args.remote) == 0:
            print("[!] -r/--remote requires at least one argument.")
            sys.exit(1)
        elif len(args.remote) == 1:
            remote_arg = args.remote[0]
            if remote_arg.endswith('.json'):
                remote_targets = load_targets_from_json(remote_arg)
                if not remote_targets:
                    sys.exit(1)
            else:
                print("[!] Direct address format requires credentials as second argument.")
                print("[!] Usage: -r IP:path username:password")
                sys.exit(1)
        elif len(args.remote) == 2:
            target = parse_remote_target(args.remote[0], args.remote[1])
            if target:
                remote_targets = [target]
            else:
                sys.exit(1)
        else:
            print("[!] -r/--remote accepts maximum 2 arguments.")
            sys.exit(1)

    process_names = args.process_names if args.process_names else PROCESS_NAMES
    cracking_requested = args.autocrack is not None or args.singlecrack is not None

    # An already-running hashcat is monitored if present, but it is not required:
    # -ac/-sc start their own, and the outfile can be watched before hashcat starts.
    starting_pids = check_pids(process_names)
    if starting_pids:
        print('[*] hashcat PID(s): {}'.format(', '.join(sorted(starting_pids))))
    elif cracking_requested:
        print('[*] No hashcat process running yet. AVC-CC will start its own.')
    else:
        print('[!] No hashcat process found (looked for: {}).'.format(', '.join(process_names)))
        print('[*] Monitoring {} anyway. Use -p to set the process name.'.format(hashcat_outfile))

    # Fetch from remote targets if specified
    if remote_targets:
        print('[*] Fetching hashes from remote targets...')
        remote_hashes = fetch_remote_hashes(remote_targets)
        if remote_hashes:
            print(f'[+] Fetched {len(remote_hashes)} hashes from remote targets.')
            try:
                with open(hashcat_outfile, 'a') as f:
                    f.writelines(remote_hashes)
                print(f'[+] Appended remote hashes to {hashcat_outfile}')
            except Exception as e:
                print(f'[!] Error writing remote hashes: {e}')

    starting_outfile = check_file(hashcat_outfile)
    if starting_outfile:
        print('[*] Outfile exists and is {} lines long.'.format(starting_outfile))

    # Initialize cracking if specified
    hashcat_processes = {}
    creds_file = None
    single_crack_process = None
    own_cracking = False  # True once AVC-CC has started a hashcat process itself

    # Handle autocrack
    if args.autocrack is not None:
        creds_file = args.autocrack
        print(f'[*] Starting hashcat cracking subprocesses for .hc22000 files...')
        hashcat_processes = start_cracking_subprocesses()
        if hashcat_processes:
            own_cracking = True
            print(f'[+] Started {len(hashcat_processes)} hashcat processes')
        else:
            print('[!] No hashcat processes started. Check if .hc22000 files exist.')

    # Handle single crack
    if args.singlecrack is not None:
        if len(args.singlecrack) == 0:
            print("[!] -sc/--singlecrack requires at least one argument (hash file).")
            sys.exit(1)
        elif len(args.singlecrack) == 1:
            creds_file = 'creds.txt'
            hash_file = args.singlecrack[0]
        elif len(args.singlecrack) == 2:
            hash_file = args.singlecrack[0]
            creds_file = args.singlecrack[1]
        else:
            print("[!] -sc/--singlecrack accepts maximum 2 arguments.")
            sys.exit(1)

        print(f'[*] Starting hashcat for single file: {hash_file}...')
        single_crack_process = start_single_crack(hash_file, creds_file)
        if single_crack_process:
            own_cracking = True
            print(f'[+] Started hashcat for {hash_file}')
        else:
            print('[!] Single crack process failed to start.')

    i = 1
    try:
        while i < notification_count + 1:
            # Monitor hashcat cracking processes if active
            if hashcat_processes and creds_file:
                hashcat_processes = monitor_hashcat_processes(hashcat_processes, creds_file)

            # Monitor single crack process if active
            if single_crack_process:
                single_crack_process = monitor_single_crack_process(single_crack_process)

            # Our own crackers finished and there is no pre-existing run to watch.
            if own_cracking and not starting_pids and not hashcat_processes and single_crack_process is None:
                print('[*] All cracking processes finished. Results written to {}.'.format(creds_file))
                sys.exit(0)

            current_pids = check_pids(process_names)
            current_outfile = check_file(hashcat_outfile)
            current_time = time.strftime('%A %d %B %Y at %H:%M')
            # Only give up on a pre-existing hashcat run, and only once every PID
            # we started out with is gone (ours may be in the list too).
            if starting_pids and not (starting_pids & current_pids):
                print('[-] Original hashcat process stopped. Exiting.')
                sys.exit(0)
            elif not current_outfile:
                print('[-] File does not exist. Monitoring for file creation.'
                      'Checked on {}'.format(current_time))
            elif starting_outfile == current_outfile:
                print('[-] No more hashes cracked yet. Checked on {}'.format(current_time))
            elif starting_outfile != current_outfile:
                print('[+] Additional hashes cracked! Checked on {}'.format(current_time))
                message = ('{} hashes have been cracked.'
                           'Notification {} of {}.'.format(current_outfile, i, notification_count))

                i += 1
                if i == notification_count + 1:
                    print('[*] Notification limit reached. Happy hunting.')
                    sys.exit(0)
                starting_outfile = current_outfile
                print('[*] Sent {} out of {} notifications.'.format(i - 1, notification_count))
            print('[*] Sleeping for {} minutes...'.format(check_interval))
            time.sleep(float(check_interval) * 60)
    except KeyboardInterrupt:
        print('[!] SIGINT detected, exiting...')
        sys.exit(0)

if __name__ == '__main__':
    main()