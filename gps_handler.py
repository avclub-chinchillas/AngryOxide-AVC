import gpsd
from time import datetime

def read_gps():
    try:
        gpsd.connect()
        packet = gpsd.get_current()
        datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if packet.mode >= 2:  # 2D fix
            latitude = packet.lat
            longitude = packet.lon
            return (latitude, longitude)
        elif packet.mode == 3:  # 3D fix
            latitude = packet.lat
            longitude = packet.lon
            altitude = packet.alt
            return (latitude, longitude, altitude)
        else:
            print("[!] No GPS fix available.")
            return None
    except Exception as e:
        print(f"[!] Error reading GPS data: {e}")
        return None