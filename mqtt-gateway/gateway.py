import ntptime
import network
import time
from umqtt.simple import MQTTClient
import ssl
import config
import eqiva
import json


def wifi_connect():
    sta_if = network.WLAN(network.WLAN.IF_STA)
    if not sta_if.isconnected():
        print('\nConnecting to WiFi')
        sta_if.active(True)
        sta_if.connect(config.SSID, config.PASSWD)
        while not sta_if.isconnected():
            print(".", end='')
            time.sleep(0.5)
            pass
    print('connected!\nNetwork config:', sta_if.ipconfig('addr4'))

    # Set time via NTP
    ntptime.settime()
    print('Current time:', time.localtime(), '\n')


def mqtt_connect():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.verify_mode = ssl.CERT_NONE
    client = MQTTClient(client_id=config.MQTT_CLIENT_ID,
                        server=config.MQTT_SERVER,
                        port=config.MQTT_PORT,
                        user=config.MQTT_USER,
                        password=config.MQTT_PASSWD,
                        keepalive=7200,
                        ssl=context
                        )
    client.connect()
    client.set_callback(sub)
    client.connect()
    print('Connected to MQTT Broker.')

    # Sub to topics
    client.subscribe(f'{config.DEVICE_NAME}/radin/scan'.encode())
    client.subscribe(f'{config.DEVICE_NAME}/radin/trv'.encode())
    print('Subscribed to topics.')
    return client


def sub(topic, msg):
    print('Received message %s on topic %s' % (msg, topic))
    topic_str = topic.decode()
    msg_j = json.loads(msg.decode())

    # Handle msgs
    if topic_str == f'{config.DEVICE_NAME}/radin/scan':
        res = eq.scan()

        # Publish results
        client.publish(f'{config.DEVICE_NAME}/radout/devlist'.encode(),
                       json.dumps({"devices": res}).encode(),
                       qos=0
                       )

    elif topic_str == f'{config.DEVICE_NAME}/radin/trv':
        eq.connect(msg_j['mac'], max_retries=3)

        # Get status
        # {"mac": "00:1A:22:XX:XX:XX", "cmd": "status"}
        if msg_j['cmd'].lower() == 'status':
            res = eq.get_status()

        # Set mode
        # {"mac": "00:1A:22:XX:XX:XX", "cmd": "mode", "params": "auto"}
        # {"mac": "00:1A:22:XX:XX:XX", "cmd": "mode", "params": {"temp": 20.0, "time": [19, 1, 2025, 20, 30]}}
        elif msg_j['cmd'].lower() == 'mode':
            if not isinstance(msg_j['params'], dict) and msg_j['params'].lower() == 'manual':
                res = eq.set_mode(eqiva.MODE_MANUAL)
            elif not isinstance(msg_j['params'], dict) and msg_j['params'].lower() == 'auto':
                res = eq.set_mode(eqiva.MODE_AUTO)
            elif isinstance(msg_j['params'], dict) and len(msg_j['params']['time']) == 5:
                t = msg_j['params']['time']
                res = eq.set_mode(0, msg_j['params']['temp'], t[0], t[1], t[2], (t[3], t[4]))
            else:
                res = {"error": "Unknown mode"}

        # Set temperature
        # {"mac": "00:1A:22:XX:XX:XX", "cmd": "temp", "params": 22.4}
        # {"mac": "00:1A:22:XX:XX:XX", "cmd": "temp", "params": "boost_on"}
        elif msg_j['cmd'].lower() == 'temp':
            if isinstance(msg_j['params'], float):
                res = eq.set_temp(msg_j['params'])
            elif isinstance(msg_j['params'], str):
                if msg_j['params'].lower() == 'comfort':
                    res = eq.set_temp(0, eqiva.COMFORT)
                elif msg_j['params'].lower() == 'eco':
                    res = eq.set_temp(0, eqiva.ECO)
                elif msg_j['params'].lower() == 'boost_on':
                    res = eq.set_temp(0, eqiva.BOOST_ON)
                elif msg_j['params'].lower() == 'boost_off':
                    res = eq.set_temp(0, eqiva.BOOST_OFF)
                else:
                    res = {"error": "Unknown mode"}
            else:
                res = {"error": "Unknown parameter"}

        # Get timer
        # {"mac": "00:1A:22:XX:XX:XX", "cmd": "get_timer", "params": "fri"}
        elif msg_j['cmd'].lower() == 'get_timer':
            if isinstance(msg_j['params'], str):
                res = eq.get_timer(msg_j['params'])
            else:
                res = {"error": "Unknown parameter"}

        # Set timer
        # {"mac": "00:1A:22:XX:XX:XX", "cmd": "set_timer", "params": {"day": "fri", "temps_times": [...]}}
        elif msg_j['cmd'].lower() == 'set_timer':
            if isinstance(msg_j['params']['temps_times'], list):
                res = eq.set_timer(msg_j['params']['day'], msg_j['params']['temps_times'])
            else:
                res = {"error": "Unknown parameter"}

        # Set comfort / eco temperature
        # {"mac": "00:1A:22:XX:XX:XX", "cmd": "comfort_eco", "params": {"comfort": 22.5, "eco": 10.0}}
        elif msg_j['cmd'].lower() == 'comfort_eco':
            if isinstance(msg_j['params']['comfort'], float) and isinstance(msg_j['params']['eco'], float):
                res = eq.conf_comfort_eco(msg_j['params']['eco'], msg_j['params']['comfort'])
            else:
                res = {"error": "Unknown parameter"}

        # Set window open temperature
        # {"mac": "00:1A:22:XX:XX:XX", "cmd": "window_open", "params": {"temp": 12.5, "duration": 30}}
        elif msg_j['cmd'].lower() == 'window_open':
            if isinstance(msg_j['params']['temp'], float) and isinstance(msg_j['params']['duration'], int):
                res = eq.conf_window_open(msg_j['params']['temp'], msg_j['params']['duration'])
            else:
                res = {"error": "Unknown parameter"}

        # Set offset temperature
        # {"mac": "00:1A:22:XX:XX:XX", "cmd": "offset", "params": 3.5}
        elif msg_j['cmd'].lower() == 'offset':
            if isinstance(msg_j['params'], float):
                res = eq.conf_offset(msg_j['params'])
            else:
                res = {"error": "Unknown parameter"}

        # Set offset temperature
        # {"mac": "00:1A:22:XX:XX:XX", "cmd": "lock", "params": true}
        elif msg_j['cmd'].lower() == 'lock':
            if isinstance(msg_j['params'], bool):
                res = eq.set_lock(msg_j['params'])
            else:
                res = {"error": "Unknown parameter"}

        # Factory reset
        # {"mac": "00:1A:22:XX:XX:XX", "cmd": "reset"}
        elif msg_j['cmd'].lower() == 'reset':
            res = eq.factory_reset()

        # Final
        else:
            print('Unknown command')
            res = {"error": "Unknown command"}

        # Publish results
        client.publish(f'{config.DEVICE_NAME}/radout/status'.encode(),
                       json.dumps(res).encode(),
                       qos=0
                       )
        eq.disconnect()
    else:
        print(f'Unknown topic: {topic_str}')


if __name__ == '__main__':
    # Initial setup
    wifi_connect()
    client = mqtt_connect()
    eq = eqiva.Eqiva()

    # Receive msgs
    print('Waiting for incoming messages...')
    while True:
        client.wait_msg()
