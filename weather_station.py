import serial
import time
import struct
import sys
from datetime import datetime

# --- Configuration ---
# Update this to your station's serial port
SERIAL_PORT = 'COM3'
BAUD_RATE = 19200
SERIAL_TIMEOUT = 5.0

# --- CRC-CCITT (0x1021) Table ---
CRC_TABLE = [
    0x0, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
    0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
    0x1231, 0x210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
    0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
    0x2462, 0x3443, 0x420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
    0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
    0x3653, 0x2672, 0x1611, 0x630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
    0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
    0x48c4, 0x58e5, 0x6886, 0x78a7, 0x840, 0x1861, 0x2802, 0x3823,
    0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
    0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0xa50, 0x3a33, 0x2a12,
    0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
    0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0xc60, 0x1c41,
    0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
    0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0xe70,
    0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
    0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
    0x1080, 0xa1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
    0x2b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
    0x34e2, 0x24c3, 0x14a0, 0x481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
    0x26d3, 0x36f2, 0x691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x8e1, 0x3882, 0x28a3,
    0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
    0x4a75, 0x5a54, 0x6a37, 0x7a16, 0xaf1, 0x1ad0, 0x2ab3, 0x3a92,
    0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
    0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0xcc1,
    0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
    0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0xed1, 0x1ef0
]

# --- Unit Conversion & Helpers ---

def f_to_c(f_temp):
    if f_temp is None: return None
    return (f_temp - 32.0) * 5.0 / 9.0

def mph_to_ms(mph_speed):
    if mph_speed is None: return None
    return mph_speed * 0.44704

def inhg_to_hpa(inhg_press):
    if inhg_press is None: return None
    return inhg_press * 33.8639

def parse_time(time_val):
    if time_val == 65535: # 0xFFFF
        return None
    try:
        hour = time_val // 100
        minute = time_val % 100
        return f"{hour:02d}:{minute:02d}"
    except Exception:
        return None

def wind_deg_to_text(deg):
    if deg is None:
        return None
    directions = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
    ]
    index = round(deg / (360. / 16)) % 16
    return directions[index]

def round_safe(value, precision=3):
    if isinstance(value, (int, float)):
        return round(value, precision)
    return value

def calc_crc(data):
    crc = 0
    for byte in data:
        if isinstance(byte, str):
            byte = ord(byte)
        table_index = (crc >> 8) ^ byte
        crc = (CRC_TABLE[table_index] ^ (crc << 8)) & 0xFFFF
    return crc

# --- Serial Command Functions ---

def wake_up(ser):
    print("Attempting to wake up console...")
    for _ in range(3):
        try:
            ser.write(b'\n')
            response = ser.read(2)
            if response == b'\n\r':
                print("Console is awake.")
                return True
            else:
                print(f"Wake up failed. Got: {response!r}. Retrying...")
                time.sleep(1.2)
        except serial.SerialException as e:
            print(f"Serial error during wake up: {e}")
            return False
    print("Failed to wake up console after 3 attempts.")
    return False

def get_firmware_ver(ser):
    try:
        ser.write(b'VER\n')
        ok_response = ser.read_until(b'OK\n\r')
        if b'OK' not in ok_response:
            return None
        data = ser.read_until(b'\n\r')
        return data.decode('ascii').strip()
    except Exception as e:
        print(f"Error getting 'VER': {e}")
        return None

def get_firmware_nver(ser):
    try:
        ser.write(b'NVER\n')
        ok_response = ser.read_until(b'OK\n\r')
        if b'OK' not in ok_response:
            return None
        data = ser.read_until(b'\n\r')
        return data.decode('ascii').strip()
    except Exception as e:
        print(f"Error getting 'NVER': {e}")
        return None

def get_console_time(ser):
    try:
        ser.write(b'GETTIME\n')
        packet = ser.read(9)
        if len(packet) != 9 or packet[0:1] != b'\x06':
            return None
        
        data_to_check = packet[1:7]
        received_crc = struct.unpack('>H', packet[7:9])[0]
        calculated_crc = calc_crc(data_to_check)

        if received_crc != calculated_crc:
            return None

        sec, min, hour, day, month, year_offset = struct.unpack_from('BBBBBB', data_to_check, 0)
        year = year_offset + 1900
        return f"{year}-{month:02d}-{day:02d} {hour:02d}:{min:02d}:{sec:02d}"
    except Exception as e:
        print(f"Serial error while getting GETTIME: {e}")
        return None

def get_data_packets(ser):
    try:
        ser.write(b'LPS 3 2\n')
        ack = ser.read(1)
        if ack != b'\x06':
            print(f"Command not acknowledged. Expected 0x06, got: {ack!r}")
            return None
        
        packet1 = ser.read(99)
        if len(packet1) != 99:
            return None
        
        packet2 = ser.read(99)
        if len(packet2) != 99:
            return None
            
        return [packet1, packet2]
    except Exception as e:
        print(f"Serial error while getting packets: {e}")
        return None

def get_hilows_packet(ser):
    try:
        ser.write(b'HILOWS\n')
        ack = ser.read(1)
        if ack != b'\x06':
            print(f"HILOWS not acknowledged. Expected 0x06, got: {ack!r}")
            return None
        
        packet = ser.read(438)
        if len(packet) != 438:
            return None
            
        return packet
    except Exception as e:
        print(f"Serial error while getting HILOWS packet: {e}")
        return None

# --- Parsing Functions ---

def validate_packet(packet, expected_type, expected_len=99):
    if packet[0:3] != b'LOO':
        return None, False
        
    packet_type = struct.unpack_from('B', packet, 4)[0]
    if packet_type != expected_type:
        return None, False

    data_to_check = packet[0:expected_len-2]
    received_crc = struct.unpack('>H', packet[expected_len-2:expected_len])[0]
    calculated_crc = calc_crc(data_to_check)
    
    if received_crc != calculated_crc:
        return None, False
        
    return data_to_check, True

def parse_loop_packet(packet):
    data_to_check, is_valid = validate_packet(packet, expected_type=0, expected_len=99)
    if not is_valid:
        return None
        
    data = {}
    try:
        raw_barometer = struct.unpack_from('<H', data_to_check, 7)[0]
        data['barometerHpa'] = round_safe(inhg_to_hpa(raw_barometer / 1000.0 if raw_barometer != 0 else None))
        
        raw_inside_temp = struct.unpack_from('<h', data_to_check, 9)[0]
        data['insideTempC'] = round_safe(f_to_c(raw_inside_temp / 10.0 if raw_inside_temp != 32767 else None))
        
        raw_inside_hum = struct.unpack_from('B', data_to_check, 11)[0]
        data['insideHumidityPercent'] = raw_inside_hum if raw_inside_hum != 255 else None
        
        raw_outside_temp = struct.unpack_from('<h', data_to_check, 12)[0]
        data['outsideTempC'] = round_safe(f_to_c(raw_outside_temp / 10.0 if raw_outside_temp != 32767 else None))
        
        data['windSpeedMs'] = round_safe(mph_to_ms(struct.unpack_from('B', data_to_check, 14)[0]))
        data['avgWind10minMs'] = round_safe(mph_to_ms(struct.unpack_from('B', data_to_check, 15)[0]))
        
        wind_dir_deg = struct.unpack_from('<H', data_to_check, 16)[0]
        data['windDirectionDeg'] = wind_dir_deg
        data['windDirectionText'] = wind_deg_to_text(wind_dir_deg)

        raw_outside_hum = struct.unpack_from('B', data_to_check, 33)[0]
        data['outsideHumidityPercent'] = raw_outside_hum if raw_outside_hum != 255 else None
        
        RAIN_CLICK_TO_IN = 0.01
        IN_TO_MM = 25.4

        rain_rate_clicks_hr = struct.unpack_from('<H', data_to_check, 41)[0]
        data['rainRateMmHr'] = round_safe((rain_rate_clicks_hr * RAIN_CLICK_TO_IN) * IN_TO_MM)
        
        daily_rain_clicks = struct.unpack_from('<H', data_to_check, 50)[0]
        data['dailyRainMm'] = round_safe((daily_rain_clicks * RAIN_CLICK_TO_IN) * IN_TO_MM)
        
        storm_rain_clicks = struct.unpack_from('<H', data_to_check, 46)[0]
        data['stormRainMm'] = round_safe((storm_rain_clicks * RAIN_CLICK_TO_IN) * IN_TO_MM)

        monthly_rain_clicks = struct.unpack_from('<H', data_to_check, 52)[0]
        data['monthlyRainMm'] = round_safe((monthly_rain_clicks * RAIN_CLICK_TO_IN) * IN_TO_MM)
        
        yearly_rain_clicks = struct.unpack_from('<H', data_to_check, 54)[0]
        data['yearlyRainMm'] = round_safe((yearly_rain_clicks * RAIN_CLICK_TO_IN) * IN_TO_MM)
        
        raw_battery_volt = struct.unpack_from('<H', data_to_check, 87)[0]
        data['consoleBatteryV'] = round_safe(((raw_battery_volt * 300) / 512) / 100.0)
        
        sunrise = struct.unpack_from('<H', data_to_check, 91)[0]
        sunset = struct.unpack_from('<H', data_to_check, 93)[0]
        data['sunrise'] = f"{sunrise // 100:02d}:{sunrise % 100:02d}"
        data['sunset'] = f"{sunset // 100:02d}:{sunset % 100:02d}"

        return data
    except Exception as e:
        print(f"Error parsing LOOP1: {e}")
        return None

def parse_loop2_packet(packet):
    data_to_check, is_valid = validate_packet(packet, expected_type=1, expected_len=99)
    if not is_valid:
        return None

    data = {}
    try:
        raw_10m_avg_wind = struct.unpack_from('<H', data_to_check, 18)[0]
        data['avgWind10minMsHires'] = round_safe(mph_to_ms(raw_10m_avg_wind / 10.0 if raw_10m_avg_wind != 32767 else None))
        
        raw_2m_avg_wind = struct.unpack_from('<H', data_to_check, 20)[0]
        data['avgWind2minMs'] = round_safe(mph_to_ms(raw_2m_avg_wind / 10.0 if raw_2m_avg_wind != 32767 else None))

        raw_10m_gust = struct.unpack_from('<H', data_to_check, 22)[0]
        data['windGust10minMs'] = round_safe(mph_to_ms(raw_10m_gust / 10.0 if raw_10m_gust != 32767 else None))
        
        data['windGust10minDirDeg'] = struct.unpack_from('<H', data_to_check, 24)[0]

        raw_dewpoint = struct.unpack_from('<h', data_to_check, 30)[0]
        data['dewpointC'] = round_safe(f_to_c(raw_dewpoint if raw_dewpoint != 32767 else None))
        
        raw_heat_index = struct.unpack_from('<h', data_to_check, 35)[0]
        data['heatIndexC'] = round_safe(f_to_c(raw_heat_index if raw_heat_index != 32767 else None))

        raw_wind_chill = struct.unpack_from('<h', data_to_check, 37)[0]
        data['windChillC'] = round_safe(f_to_c(raw_wind_chill if raw_wind_chill != 32767 else None))

        raw_thsw = struct.unpack_from('<h', data_to_check, 39)[0]
        data['thswIndexC'] = round_safe(f_to_c(raw_thsw if raw_thsw != 32767 else None))

        RAIN_CLICK_TO_IN = 0.01
        IN_TO_MM = 25.4
        
        last_15min_rain_clicks = struct.unpack_from('<H', data_to_check, 52)[0]
        data['last15minRainMm'] = round_safe((last_15min_rain_clicks * RAIN_CLICK_TO_IN) * IN_TO_MM)
        
        last_hour_rain_clicks = struct.unpack_from('<H', data_to_check, 54)[0]
        data['lastHourRainMm'] = round_safe((last_hour_rain_clicks * RAIN_CLICK_TO_IN) * IN_TO_MM)
        
        last_24hr_rain_clicks = struct.unpack_from('<H', data_to_check, 58)[0]
        data['last24hrRainMm'] = round_safe((last_24hr_rain_clicks * RAIN_CLICK_TO_IN) * IN_TO_MM)
        
        return data
    except Exception as e:
        print(f"Error parsing LOOP2: {e}")
        return None

def parse_hilows_packet(packet):
    data_to_check = packet[0:436]
    received_crc = struct.unpack('>H', packet[436:438])[0]
    calculated_crc = calc_crc(data_to_check)
    
    if received_crc != calculated_crc:
        print("HILOWS CRC ERROR!")
        return None
    
    data = {}
    try:
        raw_bar_day_low = struct.unpack_from('<H', data_to_check, 0)[0]
        data['baroDayLowHpa'] = round_safe(inhg_to_hpa(raw_bar_day_low / 1000.0))
        
        raw_bar_day_high = struct.unpack_from('<H', data_to_check, 2)[0]
        data['baroDayHighHpa'] = round_safe(inhg_to_hpa(raw_bar_day_high / 1000.0))
        
        data['baroDayLowTime'] = parse_time(struct.unpack_from('<H', data_to_check, 12)[0])
        data['baroDayHighTime'] = parse_time(struct.unpack_from('<H', data_to_check, 14)[0])
        
        raw_wind_day_high = struct.unpack_from('B', data_to_check, 16)[0]
        data['windDayHighMs'] = round_safe(mph_to_ms(raw_wind_day_high))
        data['windDayHighTime'] = parse_time(struct.unpack_from('<H', data_to_check, 17)[0])
        
        raw_wind_month_high = struct.unpack_from('B', data_to_check, 19)[0]
        data['windMonthHighMs'] = round_safe(mph_to_ms(raw_wind_month_high))
        
        raw_wind_year_high = struct.unpack_from('B', data_to_check, 20)[0]
        data['windYearHighMs'] = round_safe(mph_to_ms(raw_wind_year_high))
        
        raw_in_temp_day_high = struct.unpack_from('<h', data_to_check, 21)[0]
        data['inTempDayHighC'] = round_safe(f_to_c(raw_in_temp_day_high / 10.0))
        
        raw_in_temp_day_low = struct.unpack_from('<h', data_to_check, 23)[0]
        data['inTempDayLowC'] = round_safe(f_to_c(raw_in_temp_day_low / 10.0))
        
        data['inTempDayHighTime'] = parse_time(struct.unpack_from('<H', data_to_check, 25)[0])
        data['inTempDayLowTime'] = parse_time(struct.unpack_from('<H', data_to_check, 27)[0])

        raw_out_temp_day_low = struct.unpack_from('<h', data_to_check, 47)[0]
        data['outTempDayLowC'] = round_safe(f_to_c(raw_out_temp_day_low / 10.0))
        
        raw_out_temp_day_high = struct.unpack_from('<h', data_to_check, 49)[0]
        data['outTempDayHighC'] = round_safe(f_to_c(raw_out_temp_day_high / 10.0))
        
        data['outTempDayLowTime'] = parse_time(struct.unpack_from('<H', data_to_check, 51)[0])
        data['outTempDayHighTime'] = parse_time(struct.unpack_from('<H', data_to_check, 53)[0])
        
        raw_chill_day_low = struct.unpack_from('<h', data_to_check, 79)[0]
        data['windChillDayLowC'] = round_safe(f_to_c(raw_chill_day_low))
        data['windChillDayLowTime'] = parse_time(struct.unpack_from('<H', data_to_check, 81)[0])
        
        raw_chill_month_low = struct.unpack_from('<h', data_to_check, 83)[0]
        data['windChillMonthLowC'] = round_safe(f_to_c(raw_chill_month_low))
        
        raw_chill_year_low = struct.unpack_from('<h', data_to_check, 85)[0]
        data['windChillYearLowC'] = round_safe(f_to_c(raw_chill_year_low))

        raw_heat_day_high = struct.unpack_from('<h', data_to_check, 87)[0]
        data['heatIndexDayHighC'] = round_safe(f_to_c(raw_heat_day_high))
        data['heatIndexDayHighTime'] = parse_time(struct.unpack_from('<H', data_to_check, 89)[0])
        
        raw_heat_month_high = struct.unpack_from('<h', data_to_check, 91)[0]
        data['heatIndexMonthHighC'] = round_safe(f_to_c(raw_heat_month_high))
        
        raw_heat_year_high = struct.unpack_from('<h', data_to_check, 93)[0]
        data['heatIndexYearHighC'] = round_safe(f_to_c(raw_heat_year_high))

        RAIN_CLICK_TO_IN = 0.01
        IN_TO_MM = 25.4
        raw_rain_rate_day_high = struct.unpack_from('<H', data_to_check, 116)[0]
        data['rainRateDayHighMmHr'] = round_safe((raw_rain_rate_day_high * RAIN_CLICK_TO_IN) * IN_TO_MM)
        data['rainRateDayHighTime'] = parse_time(struct.unpack_from('<H', data_to_check, 118)[0])
        
        raw_rain_rate_hour_high = struct.unpack_from('<H', data_to_check, 120)[0]
        data['rainRateHourHighMmHr'] = round_safe((raw_rain_rate_hour_high * RAIN_CLICK_TO_IN) * IN_TO_MM)

        return data
    except Exception as e:
        print(f"Error parsing HILOWS: {e}")
        return None

# --- Main Data Fetching Function ---

def fetch_all_data():
    """
    Connects to the station, fetches all data, and returns a structured dict.
    """
    ser = None
    all_data = {
        "liveData": None,
        "hiLowData": None,
        "consoleInfo": None,
        "error": None
    }

    try:
        print(f"Opening serial port {SERIAL_PORT}...")
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUD_RATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=SERIAL_TIMEOUT
        )
        
        if not wake_up(ser):
            raise Exception("Failed to wake up console.")
            
        # --- 1. Fetch Live Data ---
        print("Fetching LOOP packets...")
        packets = get_data_packets(ser)
        if packets:
            loop1_data = parse_loop_packet(packets[0])
            loop2_data = parse_loop2_packet(packets[1])
            if loop1_data and loop2_data:
                live_data = {**loop1_data, **loop2_data}
                live_data["liveDataTimestamp"] = datetime.now().isoformat()
                all_data["liveData"] = live_data
            else:
                print("Failed to parse LOOP packets.")
        else:
            print("Failed to retrieve LOOP packets.")

        # --- 2. Fetch HILOWS Data ---
        print("Fetching HILOWS packet...")
        hilows_packet = get_hilows_packet(ser)
        if hilows_packet:
            hilows_data = parse_hilows_packet(hilows_packet)
            if hilows_data:
                all_data["hiLowData"] = hilows_data
            else:
                print("Failed to parse HILOWS packet.")
        else:
            print("Failed to retrieve HILOWS packet.")

        # --- 3. Fetch Console Info ---
        print("Fetching console info...")
        all_data["consoleInfo"] = {
            "consoleTime": get_console_time(ser),
            "firmwareDate": get_firmware_ver(ser),
            "firmwareVersion": get_firmware_nver(ser)
        }
        
        print("Data fetch complete.")

    except serial.SerialException as e:
        print(f"SERIAL ERROR: {e}")
        all_data["error"] = str(e)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        all_data["error"] = str(e)
    finally:
        if ser and ser.is_open:
            ser.close()
            print(f"Serial port {SERIAL_PORT} closed.")
    
    return all_data

if __name__ == "__main__":
    # This allows you to run this file directly to test the data fetch
    print("Running standalone test...")
    data = fetch_all_data()
    import json
    print(json.dumps(data, indent=2))