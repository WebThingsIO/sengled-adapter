"""Sengled Wi-Fi LED bulb client."""

from urllib.parse import urlparse
from uuid import uuid4
import json
import paho.mqtt.client as mqtt
import requests
import time


class SengledBulb:
    """Class to represent an individual bulb."""

    def __init__(self, client, info):
        """
        Initialize the bulb.

        client -- SengledClient instance this is attached to
        info -- the device info object returned by the server
        """
        self._client = client
        self._uuid = info['deviceUuid']
        self._category = info['category']
        self._type_code = info['typeCode']
        self._attributes = info['attributeList']

        self._client._subscribe_mqtt(
            'wifielement/{}/status'.format(self.uuid),
            self._update_status,
        )

    def set_attribute_update_callback(self, callback):
        """
        Set the callback to be called when an attribute is updated.

        callback -- callback
        """
        self._attribute_update_callback = callback

    @property
    def brightness(self):
        """Bulb brightness."""
        for attr in self._attributes:
            if attr['name'] == 'brightness':
                return int(attr['value'], 10)

        return 0

    @property
    def consumption_time(self):
        """Bulb consumption time."""
        for attr in self._attributes:
            if attr['name'] == 'consumptionTime':
                return int(attr['value'], 10)

        return 0

    @property
    def rssi(self):
        """Wi-Fi RSSI."""
        for attr in self._attributes:
            if attr['name'] == 'deviceRssi':
                return int(attr['value'], 10)

        return 0

    @property
    def identify_no(self):
        """Unsure what this is."""
        for attr in self._attributes:
            if attr['name'] == 'identifyNO':
                return attr['value']

        return ''

    @property
    def ip(self):
        """IP address."""
        for attr in self._attributes:
            if attr['name'] == 'ip':
                return attr['value']

        return ''

    @property
    def name(self):
        """Bulb name."""
        for attr in self._attributes:
            if attr['name'] == 'name':
                return attr['value']

        return ''

    @property
    def online(self):
        """Whether or not the bulb is online."""
        for attr in self._attributes:
            if attr['name'] == 'online':
                return attr['value'] == '1'

        return False

    @property
    def product_code(self):
        """Product code, e.g. 'wifielement'."""
        for attr in self._attributes:
            if attr['name'] == 'product_code':
                return attr['value']

        return ''

    @property
    def save_flag(self):
        """Unsure what this is."""
        for attr in self._attributes:
            if attr['name'] == 'save_flag':
                return attr['value'] == '1'

        return False

    @property
    def start_time(self):
        """Time this device was last connected to network."""
        for attr in self._attributes:
            if attr['name'] == 'start_time':
                return attr['value']

        return ''

    @property
    def support_attributes(self):
        """Unsure what this is."""
        for attr in self._attributes:
            if attr['name'] == 'support_attributes':
                return attr['value']

        return ''

    @property
    def switch(self):
        """Whether or not the bulb is switched on."""
        for attr in self._attributes:
            if attr['name'] == 'switch':
                return attr['value'] == '1'

        return False

    @property
    def time_zone(self):
        """Time zone of device."""
        for attr in self._attributes:
            if attr['name'] == 'time_zone':
                return attr['value']

        return ''

    @property
    def type_code(self):
        """Type code, e.g. 'wifia19-L'."""
        for attr in self._attributes:
            if attr['name'] == 'type_code':
                return attr['value']

        return self._type_code

    @property
    def version(self):
        """Firmware version."""
        for attr in self._attributes:
            if attr['name'] == 'version':
                return attr['value']

        return ''

    @property
    def uuid(self):
        """Universally unique identifier."""
        return self._uuid

    @property
    def category(self):
        """Category, e.g. 'wifielement'."""
        return self._category

    def toggle(self, on):
        """
        Toggle the state of the bulb.

        on -- whether or not to turn the bulb on

        Returns True on success, False on failure.
        """
        data = {
            'dn': self.uuid,
            'type': 'switch',
            'value': '1' if on else '0',
            'time': int(time.time() * 1000),
        }

        return self._client._publish_mqtt(
            'wifielement/{}/update'.format(self.uuid),
            json.dumps(data),
        )

    def set_brightness(self, level):
        """
        Set the brightness of the bulb.

        level -- new brightness level (0-100)

        Returns True on success, False on failure.
        """
        level = max(min(level, 100), 0)

        data = {
            'dn': self.uuid,
            'type': 'brightness',
            'value': str(level),
            'time': int(time.time() * 1000),
        }

        return self._client._publish_mqtt(
            'wifielement/{}/update'.format(self.uuid),
            json.dumps(data),
        )

    def _update_status(self, message):
        """
        Update the status from an incoming MQTT message.

        message -- the incoming message
        """
        try:
            data = json.loads(message)
        except ValueError:
            return

        for status in data:
            if 'type' not in status or 'dn' not in status:
                continue

            if status['dn'] != self.uuid:
                continue

            for attr in self._attributes:
                if attr['name'] == status['type']:
                    attr['value'] = status['value']

                    if self._attribute_update_callback:
                        name = self._attribute_to_property(attr['name'])

                        if hasattr(self, name):
                            self._attribute_update_callback(
                                name,
                                getattr(self, name)
                            )

                    break

    @staticmethod
    def _attribute_to_property(attr):
        attr_map = {
            'consumptionTime': 'consumption_time',
            'deviceRssi': 'rssi',
            'identifyNO': 'identify_no',
            'productCode': 'product_code',
            'saveFlag': 'save_flag',
            'startTime': 'start_time',
            'supportAttributes': 'support_attributes',
            'timeZone': 'time_zone',
            'typeCode': 'type_code',
        }

        return attr_map.get(attr, attr)


class SengledClient:
    """Class to control Sengled Wi-Fi LED bulbs."""

    def __init__(self, username, password):
        """
        Initialize the client.

        username -- username for Sengled mobile app
        password -- password for Sengled mobile app
        """
        self._uuid = uuid4().hex[:-16]
        self._username = username
        self._password = password
        self._jsession_id = None
        self._mqtt_server = {
            'host': 'us-mqtt.cloud.sengled.com',
            'port': 443,
            'path': '/mqtt',
        }
        self._mqtt_client = None
        self._devices = []
        self._subscribed = {}

    def login(self):
        """
        Log user into server.

        Returns True on success, False on failure.
        """
        if self._jsession_id:
            if not self._is_session_timeout():
                return

        r = requests.post(
            'https://ucenter.cloud.sengled.com/user/app/customer/v2/AuthenCross.json',  # noqa
            headers={
                'Content-Type': 'application/json',
            },
            json={
                'uuid': self._uuid,
                'user': self._username,
                'pwd': self._password,
                'osType': 'android',
                'productCode': 'life',
                'appCode': 'life',
            },
        )

        if r.status_code != 200:
            return False

        data = r.json()
        if 'jsessionId' not in data or not data['jsessionId']:
            return False

        self._jsession_id = data['jsessionId']

        self._get_server_info()

        if not self._mqtt_client:
            self._initialize_mqtt()
        else:
            self._reinitialize_mqtt()

        self.get_devices(force_update=True)

        return True

    def _is_session_timeout(self):
        """
        Determine whether or not the session has timed out.

        Returns True if timed out, False otherwise.
        """
        if not self._jsession_id:
            return True

        r = requests.post(
            'https://ucenter.cloud.sengled.com/user/app/customer/isSessionTimeout.json',  # noqa
            headers={
                'Content-Type': 'application/json',
                'Cookie': 'JSESSIONID={}'.format(self._jsession_id),
                'sid': self._jsession_id,
                'X-Requested-With': 'com.sengled.life2',
            },
            json={
                'uuid': self._uuid,
                'os_type': 'android',
                'appCode': 'life',
            },
        )

        if r.status_code != 200:
            return True

        data = r.json()
        if 'info' not in data or data['info'] != 'OK':
            return True

        return False

    def _get_server_info(self):
        """Get secondary server info from the primary."""
        if not self._jsession_id:
            return

        r = requests.post(
            'https://life2.cloud.sengled.com/life2/server/getServerInfo.json',
            headers={
                'Content-Type': 'application/json',
                'Cookie': 'JSESSIONID={}'.format(self._jsession_id),
                'sid': self._jsession_id,
                'X-Requested-With': 'com.sengled.life2',
            },
            json={},
        )

        if r.status_code != 200:
            return

        data = r.json()
        if 'inceptionAddr' not in data or not data['inceptionAddr']:
            return

        url = urlparse(data['inceptionAddr'])
        if ':' in url.netloc:
            self._mqtt_server['host'] = url.netloc.split(':')[0]
            self._mqtt_server['port'] = int(url.netloc.split(':')[1], 10)
            self._mqtt_server['path'] = url.path
        else:
            self._mqtt_server['host'] = url.netloc
            self._mqtt_server['port'] = 443
            self._mqtt_server['path'] = url.path

    def get_devices(self, force_update=False):
        """
        Get list of connected devices.

        force_update -- whether or not to force an update from the server
        """
        if not self._jsession_id:
            return self._devices

        if len(self._devices) > 0 and not force_update:
            return self._devices

        r = requests.post(
            'https://life2.cloud.sengled.com/life2/device/list.json',
            headers={
                'Content-Type': 'application/json',
                'Cookie': 'JSESSIONID={}'.format(self._jsession_id),
                'sid': self._jsession_id,
                'X-Requested-With': 'com.sengled.life2',
            },
            json={},
        )

        if r.status_code != 200:
            return self._devices

        data = r.json()
        if 'deviceList' not in data or not data['deviceList']:
            return self._devices

        for d in data['deviceList']:
            found = False

            for dev in self._devices:
                if dev.uuid == d['deviceUuid']:
                    found = True
                    break

            if not found:
                self._devices.append(SengledBulb(self, d))

        return self._devices

    def _initialize_mqtt(self):
        """Initialize the MQTT connection."""
        if not self._jsession_id:
            return False

        def on_message(client, userdata, msg):
            if msg.topic in self._subscribed:
                self._subscribed[msg.topic](msg.payload)

        self._mqtt_client = mqtt.Client(
            client_id='{}@lifeApp'.format(self._jsession_id),
            transport='websockets'
        )
        self._mqtt_client.tls_set_context()
        self._mqtt_client.ws_set_options(
            path=self._mqtt_server['path'],
            headers={
                'Cookie': 'JSESSIONID={}'.format(self._jsession_id),
                'X-Requested-With': 'com.sengled.life2',
            },
        )
        self._mqtt_client.on_message = on_message
        self._mqtt_client.connect(
            self._mqtt_server['host'],
            port=self._mqtt_server['port'],
            keepalive=30,
        )
        self._mqtt_client.loop_start()

        return True

    def _reinitialize_mqtt(self):
        """Re-initialize the MQTT connection."""
        if self._mqtt_client is None or not self._jsession_id:
            return False

        self._mqtt_client.loop_stop()
        self._mqtt_client.disconnect()
        self._mqtt_client.ws_set_options(
            path=self._mqtt_server['path'],
            headers={
                'Cookie': 'JSESSIONID={}'.format(self._jsession_id),
            },
        )
        self._mqtt_client.reconnect()
        self._mqtt_client.loop_start()

        for topic in self._subscribed:
            self._subscribe_mqtt(topic, self._subscribed[topic])

        return True

    def _publish_mqtt(self, topic, payload=None):
        """
        Publish an MQTT message.

        topic -- topic to publish the message on
        payload -- message to send

        Returns True if publish succeeded, False if not.
        """
        if self._mqtt_client is None:
            return False

        r = self._mqtt_client.publish(topic, payload=payload)

        try:
            r.wait_for_publish()
            return r.is_published
        except ValueError:
            pass

        return False

    def _subscribe_mqtt(self, topic, callback):
        """
        Subscribe to an MQTT topic.

        topic -- topic to subscribe to
        callback -- callback to call when a message comes in
        """
        if self._mqtt_client is None:
            return False

        r = self._mqtt_client.subscribe(topic)
        if r[0] != mqtt.MQTT_ERR_SUCCESS:
            return False

        self._subscribed[topic] = callback
        return True

    def _unsubscribe_mqtt(self, topic, callback):
        """
        Unsubscribe from an MQTT topic.

        topic -- topic to unsubscribe from
        callback -- callback from previous subscription
        """
        if topic in self._subscribed:
            del self._subscribed[topic]
