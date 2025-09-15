import argparse
import time
from os import path
from subprocess import Popen, PIPE

PROCESS_NAME = 'hashcat64.bin'

def check_pid(process_name):
    """Return pid of hashcat process."""
    stdout = Popen('pidof ' + process_name, shell=True, stdout=PIPE).stdout
    output = stdout.read().rstrip()
    output = output.decode('utf-8')
    if output:
        return output
    return False


def check_file(hashcat_outfile):
    """Check number of lines in designated outfile."""
    if not path.isfile(hashcat_outfile):
        return False
    with open(hashcat_outfile) as file:
        i = 0
        for i, lines in enumerate(file):
            pass
    return i + 1

def main():
    """Take user input to setup notifications. Print status updates to terminal."""
    parser = argparse.ArgumentParser(description='Periodically check hashcat cracking progress and notify of success.')
    parser.add_argument('-o', '--outfile', dest='hashcat_outfile', required=True,
                        help='hashcat outfile to monitor.')
    parser.add_argument('-i', '--interval', dest='check_interval', required=False, type=float,
                        default=15, help='Interval in minutes between checks. Default 15.')
    parser.add_argument('-n', '--notification-count', dest='notification_count', required=False,
                        type=int, default=5, help='Cease operation after N notifications. Default 5.')
    args = parser.parse_args()
    hashcat_outfile = args.hashcat_outfile
    check_interval = args.check_interval
    notification_count = args.notification_count

    starting_pid = check_pid(PROCESS_NAME)
    if not starting_pid:
        print('[-] hashcat is not running. Exiting.')
        exit()
    print('[*] hashcat PID: {}'.format(starting_pid))

    starting_outfile = check_file(hashcat_outfile)
    if starting_outfile:
        print('[*] Outfile exists and is {} lines long.'.format(starting_outfile))

    i = 1
    try:
        while i < notification_count + 1:
            current_pid = check_pid(PROCESS_NAME)
            current_outfile = check_file(hashcat_outfile)
            current_time = time.strftime('%A %d %B %Y at %H:%M')
            if starting_pid != current_pid:
                print('[-] Original hashcat process stopped. Exiting.')
                exit()
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
                    exit()
                starting_outfile = current_outfile
                print('[*] Sent {} out of {} notifications.'.format(i - 1, notification_count))
            print('[*] Sleeping for {} minutes...'.format(check_interval))
            time.sleep(float(check_interval) * 60)
    except KeyboardInterrupt:
        print('[!] SIGINT detected, exiting...')
        exit()

if __name__ == '__main__':
    main()