from eqiva import Eqiva
import ntptime
import network
import time

SSID = '<EDIT>'
PASSWD = '<EDIT>'

# Connect to WiFi to get cunnrent time via NTP
sta_if = network.WLAN(network.WLAN.IF_STA)
if not sta_if.isconnected():
    print('\nConnecting to WiFi')
    sta_if.active(True)
    sta_if.connect(SSID, PASSWD)
    while not sta_if.isconnected():
        print(".", end='')
        time.sleep(0.5)
        pass
print('\nNetwork config:', sta_if.ipconfig('addr4'))

# Set time
ntptime.settime()
print('Current time:', time.localtime(), '\n')

eq = Eqiva()  # Change utc_offset if you are not in UTC+1

try:
    eq = Eqiva()  # utc_offset sets the time zone, default UTC+1

    # Scan for thermostats in the vicinity
    eq.scan()

    # Connect to a specific device
    eq.connect('00:1A:22:XX:XX:XX', max_retries=3)  # <EDIT>

    # Get the serial number, firmware version and pin
    print(eq.get_serial())

    # Get current status
    eq.get_status()

    # Set manual mode
    eq.set_mode(MODE_MANUAL)

    # Set auto mode
    eq.set_mode(MODE_AUTO)

    # Set vacation mode
    eq.set_mode(0, 20.0, 18, 1, 2025, (18, 30))  # 20.0° until 18.01.2025 18:30

    # Switch to the comfort temperature
    eq.set_temp(-1, COMFORT)

    # Switch to the comfort temperature
    eq.set_temp(0, ECO)

    # Set a temperature value - ON=30.0°; OFF=4.5°
    eq.set_temp(22.5)

    # Turn on the boost mode
    eq.set_temp(0, BOOST_ON)

    # Turn off the boost mode
    eq.set_temp(0, BOOST_OFF)

    # Get the timer value of a specific day: MON, TUE, WED, THU, FRI, SAT, SUN
    print(eq.get_timer('FRI'))

    # Set the timer values for a specific day
    # Base temperature: 10.0°, 9:30 - 10:00: 20.0°, 9:30 - 24:00: 10.0°
    temps_times = ((10.0, None, None), (20.0, 9, 30), (10.0, 10, 0))
    eq.set_timer('SUN', temps_times)

    # Configure comfort temperature
    eq.conf_comfort_eco(20.0, 10.0)  # Comfort: 20.0°, Eco: 10.0°

    # Configure open window temperature and time in min
    eq.conf_window_open(15.0, 30)  # 15.0° for 30 min

    # Configure the temperature offset
    eq.conf_offset(-2.5)

    # Lock the controls
    eq.set_lock(True)

    # Perform a factory rest
    eq.factory_reset()


except Exception as e:
    print("Error:", e)
finally:
    eq.disconnect()
