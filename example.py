import eqiva
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

eq = eqiva.Eqiva()  # Change utc_offset if you are not in UTC+1

try:
    # Scan for thermostats in the vicinity
    eq.scan()

    # Connect to a specific device
    eq.connect('00:1A:22:XX:XX:XX', max_retries=3)  # <EDIT>
    time.sleep(2)

    # Get the serial number, firmware version and pin
    print(eq.get_serial())
    time.sleep(2)

    # Get current status
    eq.get_status()
    time.sleep(2)

    # Set manual mode
    eq.set_mode(eqiva.MODE_MANUAL)
    time.sleep(2)

    # Set auto mode
    eq.set_mode(eqiva.MODE_AUTO)
    time.sleep(2)

    # Set vacation mode
    eq.set_mode(0, 20.0, 18, 1, 2025, (18, 30))  # 20.0° until 18.01.2025 18:30
    time.sleep(2)

    # Switch to the comfort temperature
    eq.set_temp(-1, eqiva.COMFORT)
    time.sleep(2)

    # Switch to the comfort temperature
    eq.set_temp(0, eqiva.ECO)
    time.sleep(2)

    # Set a temperature value - ON=30.0°; OFF=4.5°
    eq.set_temp(22.5)
    time.sleep(2)

    # Turn on the boost mode
    eq.set_temp(0, eqiva.BOOST_ON)
    time.sleep(2)

    # Turn off the boost mode
    eq.set_temp(0, eqiva.BOOST_OFF)
    time.sleep(2)

    # Get the timer value of a specific day: MON, TUE, WED, THU, FRI, SAT, SUN
    print(eq.get_timer('FRI'))
    time.sleep(2)

    # Set the timer values for a specific day
    # Base temperature: 10.0°, 9:30 - 10:00: 20.0°, 9:30 - 24:00: 10.0°
    temps_times = ((10.0, None, None), (20.0, 9, 30), (10.0, 10, 0))
    eq.set_timer('SUN', temps_times)
    time.sleep(2)

    # Configure comfort temperature
    eq.conf_comfort_eco(20.0, 10.0)  # Comfort: 20.0°, Eco: 10.0°
    time.sleep(2)

    # Configure open window temperature and time in min
    eq.conf_window_open(15.0, 30)  # 15.0° for 30 min
    time.sleep(2)

    # Configure the temperature offset
    eq.conf_offset(-2.5)
    time.sleep(2)

    # Lock the controls
    eq.set_lock(True)
    time.sleep(2)

    # Perform a factory rest
    # eq.factory_reset()


except Exception as e:
    print("Error:", e)
finally:
    eq.disconnect()
