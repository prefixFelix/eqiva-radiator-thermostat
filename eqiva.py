# Simple Eqiva radiator thermostat module (MicroPython)
# v0.2 (c) Copyright prefixFelix 2025

from micropython import const
import bluetooth
import ubinascii
import time

# BLE IRQ event constants
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_NOTIFY = const(18)

# EQ3 specific constants
HANDLE_WRITE = const(0x0411)  # Write handle for commands
HANDLE_NOTIFY = const(0x0421)  # Notification handle

# EQ3 Mode Commands
MODE_MANUAL = const(0x40)
MODE_AUTO = const(0x00)
COMFORT = const(0x43)
ECO = const(0x44)
BOOST_ON = const(0xff)
BOOST_OFF = const(0x00)

DAYS = ["SAT", "SUN", "MON", "TUE", "WED", "THU", "FRI"]


class Eqiva:
    def __init__(self, utc_offset=1):
        self.ble = bluetooth.BLE()
        self.ble.active(False)  # Reset BLE
        time.sleep(0.1)
        self.ble.active(True)
        self.ble.irq(self._irq_handler)
        self.addr = None
        self.conn_handle = None
        self.is_connected = False
        self._notification_data = None
        self.status = None
        self.parse_status = True
        self.utc_offset = utc_offset

    def _addr_to_bytes(self, addr_str):
        """Convert string MAC address to bytes."""
        addr = addr_str.replace(':', '')
        return bytes.fromhex(addr)

    def _parse_status(self, data):
        """Parse status response from Eqiva."""
        if not data or len(data) < 6:
            # if not data or len(data) not in (3, 6, 10, 15, 16):
            return "Invalid data received"

        status = {}

        # Convert bytes to list of integers for easier handling
        bytes_data = list(data)

        # Parse mode from first byte
        mode_byte = bytes_data[2]
        mode_flags = {
            0x01: "manual",
            0x02: "vacation",
            0x04: "boost",
            0x08: "dst",
            0x10: "open window",
            0x20: "locked",
            0x40: "unknown",
            0x80: "battery_low"
        }

        status["modes"] = []
        if not (mode_byte & 0x01):  # If bit 1 is not set
            status["modes"].append("auto")

        # Check each flag
        for flag, mode in mode_flags.items():
            if mode_byte & flag:
                status["modes"].append(mode)

        # Parse temperature (byte 5)
        temp = bytes_data[5] / 2
        status["temperature"] = temp

        # Parse valve position (byte 3)
        status["valve"] = bytes_data[3]

        # If vacation mode is active (bytes 7-9)
        if "vacation" in status["modes"] and len(bytes_data) > 10:
            status["vacation"] = {
                "day": bytes_data[6],
                "month": bytes_data[9],
                "year": bytes_data[7] + 2000,
                "time": [(bytes_data[8] * 30) // 60, (bytes_data[8] * 30) % 60]  # Hour, Min from 30 min counter
            }

        # Parse extended data if available (bytes 10-14)
        if len(bytes_data) > 14:
            # Temperature in open windows mode (byte 10)
            status["window_open_temp"] = bytes_data[10] / 2

            # Open windows interval (byte 11)
            status["window_open_time"] = bytes_data[11] * 5  # in minutes

            # Comfort and eco temperatures (bytes 12-13)
            status["comfort_temp"] = bytes_data[12] / 2
            status["eco_temp"] = bytes_data[13] / 2

            # Temperature offset (byte 14)
            status["temp_offset"] = (bytes_data[14] - 7) / 2

        return status

    def _irq_handler(self, event, data):
        """Handle BLE events."""
        if event == _IRQ_PERIPHERAL_CONNECT:
            conn_handle, addr_type, addr = data
            self.conn_handle = conn_handle
            self.is_connected = True
            print("Connected")

        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            conn_handle, addr_type, addr = data
            self.conn_handle = None
            self.is_connected = False
            print("Disconnected")

        elif event == _IRQ_GATTC_NOTIFY:
            conn_handle, value_handle, notify_data = data
            print("Raw data:", ubinascii.hexlify(notify_data))
            if self.parse_status:
                self.status = self._parse_status(notify_data)
                print("Status:", self.status)
            self.parse_status = True
            self._notification_data = notify_data

    def connect(self, addr_str, max_retries=3):
        """Connect to Eqiva thermostat with retries."""
        self.addr = self._addr_to_bytes(addr_str)

        for attempt in range(max_retries):
            print(f"Connection attempt {attempt + 1}/{max_retries}")

            try:
                # Reset connection state
                if self.is_connected:
                    self.disconnect()

                # Make sure BLE is active
                if not self.ble.active():
                    self.ble.active(True)
                    time.sleep(0.1)

                print("Connecting to", addr_str)
                self.ble.gap_connect(0, self.addr)

                # Wait for connection
                timeout = 10
                while timeout > 0 and not self.is_connected:
                    time.sleep(1)
                    timeout -= 1

                if self.is_connected:
                    print("Connection successful")
                    return True

            except Exception as e:
                print(f"Connection attempt failed: {e}")

            # Wait before retry
            if not self.is_connected and attempt < max_retries - 1:
                print("Waiting before retry...")
                time.sleep(2)

        raise Exception("Failed to connect after all retries")

    def disconnect(self):
        """Disconnect from thermostat."""
        if self.conn_handle is not None:
            self.ble.gap_disconnect(self.conn_handle)
            time.sleep(1)
        self.conn_handle = None
        self.is_connected = False

    def scan(self, timeout=10):
        """Scan for Eqiva thermostats."""
        found_devices = []

        def _irq_handler_scan(event, data):
            if event == _IRQ_SCAN_RESULT:
                addr_type, addr, adv_type, rssi, adv_data = data
                # Convert address to string format
                addr_string = ":".join(["{:02X}".format(b) for b in addr])

                # Check if it starts with EQ3's prefix (00:1A:22)
                if addr_string.startswith("00:1A:22"):
                    if addr_string not in found_devices:
                        found_devices.append(addr_string)
                        print(f"Found Eqiva thermostat: {addr_string}, RSSI: {rssi} dB")

            elif event == _IRQ_SCAN_DONE:
                print("Scan complete")

        try:
            # Set our scan handler
            self.ble.irq(_irq_handler_scan)

            # Start scanning
            print(f"Scanning for {timeout} seconds...")
            self.ble.gap_scan(timeout * 1000, 30000, 30000)

            # Wait for the scan to complete
            time.sleep(timeout + 1)

        finally:
            # Restore the original handler
            self.ble.irq(self._irq_handler)

        return found_devices

    def get_serial(self):
        """Read the serial number, firmware version and PIN."""
        self.parse_status = False
        command = bytearray([0x00])
        self.ble.gattc_write(self.conn_handle, HANDLE_WRITE, command, 1)
        time.sleep(1)

        if not self._notification_data or len(self._notification_data) < 15:
            raise Exception("Failed to read serial number")

        # Get firmware version from byte 1
        firmware = self._notification_data[1] / 100.0

        # Serial starts at byte 4, length 10 bytes
        serial_bytes = self._notification_data[4:14]

        # Convert each byte by subtracting 0x30
        serial = ''.join(chr(b - 0x30) for b in serial_bytes)

        pin = (
                str((ord(serial[3]) ^ ord(serial[7])) % 10) +  # First digit
                str((ord(serial[4]) ^ ord(serial[8])) % 10) +  # Second digit
                str((ord(serial[5]) ^ ord(serial[9])) % 10) +  # Third digit
                str(((ord(serial[6]) - 48) ^ (ord(serial[0]) - 65)) % 10)  # Fourth digit
        )

        return [serial, firmware, pin]

    def get_status(self):
        """Request a status update from the thermostat."""
        # Get current time for status request
        current_time = time.localtime()
        command = bytearray([
            0x03,  # Status request command
            current_time[0] - 2000,  # Year (relative to 2000)
            current_time[1],  # Month
            current_time[2],  # Day
            current_time[3] + self.utc_offset,  # Hour
            current_time[4],  # Minute
            current_time[5]  # Second
        ])

        # Write command and wait for notification
        self.ble.gattc_write(self.conn_handle, HANDLE_WRITE, command, 1)
        time.sleep(1)
        if not self.status:
            raise Exception("Failed to read status")
        return self.status

    def set_mode(self, mode, temp=-1.0, day=0, month=0, year=0, t=(0, 0)):
        """Switch mode (MANUAL, AUTO, VACATION)."""
        if temp != -1.0:
            # Vacation only
            if not 4.5 <= temp <= 30:
                raise ValueError("Temperature must be between 4.5°C and 30°C")

            command = bytearray([
                0x40,
                int(temp * 2) + 128,
                day,
                year - 2000,
                int(((t[0] * 60) + t[1]) / 30),  # 30 minute steps
                month,
            ])
        else:
            command = bytearray([0x40, mode])
        self.ble.gattc_write(self.conn_handle, HANDLE_WRITE, command, 1)
        time.sleep(1)
        if not self.status:
            raise Exception("Failed to read status")
        return self.status

    def set_temp(self, temp, mode=-1):
        """Set target temperature / boost (ON / OFF)."""
        if mode != -1:
            command = bytearray([
                0x45,
                mode
            ])
        else:
            if not 4.5 <= temp <= 30:
                raise ValueError("Temperature must be between 4.5°C and 30°C")

            command = bytearray([
                0x41,
                int(temp * 2)
            ])

        self.ble.gattc_write(self.conn_handle, HANDLE_WRITE, command, 1)
        time.sleep(1)
        if not self.status:
            raise Exception("Failed to read status")
        return self.status

    def get_timer(self, day):
        """Read timer of a specific day."""
        if day.upper() not in DAYS:
            raise ValueError("Not a valid day")

        # Command 0x20 for read timer, followed by day
        self.parse_status = False
        command = bytearray([0x20, DAYS.index(day.upper())])
        self.ble.gattc_write(self.conn_handle, HANDLE_WRITE, command, 1)

        # Wait for notification with timer data
        time.sleep(1)

        if not self._notification_data or len(self._notification_data) < 16:
            raise Exception("Failed to read timer data")

        data = list(self._notification_data)

        # Parse the timer data
        events = []

        # First temperature (midnight to first event)
        initial_temp = data[2] / 2.0
        events.append((initial_temp, None))

        # Parse remaining events
        for i in range(0, 7):  # Max 7 events
            time_byte = data[3 + i * 2]
            temp_byte = data[4 + i * 2]

            if time_byte == 0 and temp_byte == 0:
                break

            # Convert time value to hours and minutes
            hours = time_byte // 6
            minutes = (time_byte % 6) * 10
            temp = temp_byte / 2.0

            events.append((temp, f"{hours:02d}:{minutes:02d}"))

        return events

    def set_timer(self, day, temps_times):
        """Set timer for a specific day."""
        if day.upper() not in DAYS:
            raise ValueError("Not a valid day")

        # Command start (0x10 for set timer, followed by day)
        command = bytearray([0x10, DAYS.index(day.upper())])

        # Add initial midnight temperature
        first_temp = temps_times[0][0]
        command.append(int(first_temp * 2))

        # Add each event's time and following temperature
        for i in range(1, len(temps_times)):
            temp, hour, minute = temps_times[i]

            # Convert time to 10-minute intervals
            time_value = (hour * 6) + (minute // 10)
            command.append(time_value)

            # Add temperature for period after this event
            command.append(int(temp * 2))

        # Ensure that last time is 24:00
        if len(command) < 16:
            command.append(24 * 6)
        else:
            command[15] = 24 * 6

        # Pad remaining slots with zeros up to 16 bytes total
        while len(command) < 16:
            command.append(0)

        self.parse_status = False
        self.ble.gattc_write(self.conn_handle, HANDLE_WRITE, command, 1)
        time.sleep(1)

        if not self._notification_data or len(self._notification_data) != 3:
            raise Exception("Failed to read data")

        data = list(self._notification_data)
        print("Day: ", data[2])
        return data[2]

    def conf_comfort_eco(self, comfort_temp, eco_temp):
        """Configure comfort and eco temperatures."""
        if not 5.0 <= comfort_temp <= 30.0 or not 5.0 <= eco_temp <= 30.0:
            raise ValueError("Temperature must be between 5°C and 30°C")

        command = bytearray([
            0x11,  # Command for comfort/eco config
            int(comfort_temp * 2),  # Comfort temperature
            int(eco_temp * 2)  # Eco temperature
        ])
        self.ble.gattc_write(self.conn_handle, HANDLE_WRITE, command, 1)
        time.sleep(1)
        if not self.status:
            raise Exception("Failed to read status")
        return self.status

    def conf_window_open(self, temp, duration):
        """Configure window open mode."""
        if not 5.0 <= temp <= 30.0:
            raise ValueError("Temperature must be between 5°C and 30°C")
        if duration % 5 != 0:
            raise ValueError("Duration must be a multiple of 5 minutes")
        if not 0 <= duration <= 150:  # Based on API examples
            raise ValueError("Duration must be between 0 and 150 minutes")

        command = bytearray([
            0x14,  # Command for window open config
            int(temp * 2),  # Temperature in 0.5°C steps
            duration // 5  # Duration in 5-minute steps
        ])
        self.ble.gattc_write(self.conn_handle, HANDLE_WRITE, command, 1)
        time.sleep(1)
        if not self.status:
            raise Exception("Failed to read status")
        return self.status

    def conf_offset(self, offset):
        """Set temperature offset."""
        if not -3.5 <= offset <= 3.5:
            raise ValueError("Offset must be between -3.5°C and 3.5°C")

        if abs(offset * 2) % 1 != 0:
            raise ValueError("Offset must be in 0.5°C steps")

        command = bytearray([0x13, int((offset + 3.5) * 2)])  # Convert offset to encoded value
        self.ble.gattc_write(self.conn_handle, HANDLE_WRITE, command, 1)
        time.sleep(1)
        if not self.status:
            raise Exception("Failed to read status")
        return self.status

    def set_lock(self, lock):
        """Lock the thermostat."""
        if lock:
            command = bytearray([0x80, 0x01])
        else:
            command = bytearray([0x80, 0x00])
        self.ble.gattc_write(self.conn_handle, HANDLE_WRITE, command, 1)
        time.sleep(1)
        if not self.status:
            raise Exception("Failed to read status")
        return self.status

    def factory_reset(self):
        """Perform a factory rest."""
        command = bytearray([0xF0])
        self.ble.gattc_write(self.conn_handle, HANDLE_WRITE, command, 1)
        time.sleep(1)

        if not self._notification_data or len(self._notification_data) != 3:
            raise Exception("Failed to read data")

        data = list(self._notification_data)
        if data[1] == 0:
            print("Performing a factory reset...")
        return data[1]
