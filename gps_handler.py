import gpsd
from datetime import datetime as dt
from time import sleep
import csv

def read_gps():
    try:
        gpsd.connect()
        packet = gpsd.get_current()
        datetime = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        if packet.mode >= 2:  # 2D fix
            latitude = packet.lat
            longitude = packet.lon
            return (latitude, longitude)
        elif packet.mode == 3:  # 3D fix
            latitude = packet.lat
            longitude = packet.lon
            altitude = packet.alt
            return (datetime, latitude, longitude, altitude)
        else:
            print("[!] No GPS fix available.")
            return None
    except Exception as e:
        print(f"[!] Error reading GPS data: {e}")
        return None
    
if __name__ == "__main__":
    while True:
        try:
            gps_data = read_gps()
            if gps_data:
                print(f"GPS Data: {gps_data}")
                with open("gps_output.csv", "w") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Datetime", "Latitude", "Longitude", "Altitude"])
                    #if len(gps_data) == 4:
                    writer.writerow(gps_data)
                    #else:
                    #    writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), gps_data[0], gps_data[1], "N/A"])
                    f.close()
                sleep(2)
            else:
                print("Failed to retrieve GPS data.")
        except Exception or KeyboardInterrupt:
            if Exception:
                print(f"[!] Exception occurred: {Exception}")
            else:
                print("\n[!] SIGINT detected (Ctrl-C), shutting down gracefully...")
                break