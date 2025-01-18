 

# Eqiva (EQ3) radiator thermostat - ESP32 (MicroPython)

> [!WARNING]
> This repository is still work in progress! 
- Simple MicroPython module (_library_) for communication with an [EQ3 bluetooth radiator thermostat](https://www.eq-3.de/produkte/eqiva/detail/bluetooth-smart-heizkoerperthermostat.html).
- Implements **all functions** of the app ([calor BT](https://play.google.com/store/apps/details?id=de.eq3.ble.android)) and the awesome Python CLI from **[Heckie75](https://github.com/Heckie75/Eqiva-Smart-Radiator-Thermostat)**!
- The repo also contains an implementation of an Eqiva <-> MQTT (with TLS support). 

## Installation of the Eqiva module

Simply copy the `eqiva.py` file into the `lib` directory of the ESP32:
```shell
$ mpremote connect /dev/ttyUSB0 cp eqiva.py :/lib/
```

## Usage of the Eqiva module

> [!NOTE]
> The thermostat must be paired with a device once. Either via the app or manually. Otherwise, the ESP32 cannot communicate with the thermostat.

These are all the functions that can be used. Example values have been set for demonstration purposes. You can find more details in the `example.py` file. 

```python
eq = Eqiva(utc_offset=2)  # utc_offset sets the time zone, in this case UTC+2


# Scan for thermostats in the vicinity
eq.scan()

# Connect to a specific device
eq.connect("00:1A:22:XX:XX:XX", max_retries=3)

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

eq.disconnect()
```

## Installation of the MQTT gateway

1. Install the Eqiva module as described above.
2. Install the [Asynchronous MQTT](https://github.com/peterhinch/micropython-mqtt) library on the ESP32:

   ```shell
   $ mpremote connect /dev/ttyUSB0 mip install github:peterhinch/micropython-mqtt
   ```
3. Configure your gateway by editing the `config.py` file.
4. Copy the `config.py` and `gateway.py` onto the ESP32:
   ```shell
   $ mpremote connect /dev/ttyUSB0 cp config.py :
   $ mpremote connect /dev/ttyUSB0 cp gateway.py :
   ```

