"""Sengled adapter for Mozilla WebThings Gateway."""

from gateway_addon import Device

from .sengled_property import SengledProperty


_POLL_INTERVAL = 5


class SengledDevice(Device):
    """Sengled device type."""

    def __init__(self, adapter, _id, sengled_dev):
        """
        Initialize the object.

        adapter -- the Adapter managing this device
        _id -- ID of this device
        sengled_dev -- the sengled device object to initialize from
        """
        Device.__init__(self, adapter, _id)
        self._type = ['OnOffSwitch', 'Light']
        self.type = 'onOffLight'

        self.sengled_dev = sengled_dev
        self.name = sengled_dev.name
        self.description = sengled_dev.type_code
        if not self.name:
            self.name = self.description

        self.properties['on'] = SengledProperty(
            self,
            'on',
            {
                '@type': 'OnOffProperty',
                'title': 'On/Off',
                'type': 'boolean',
            },
            self.on
        )

        self.properties['level'] = SengledProperty(
            self,
            'level',
            {
                '@type': 'BrightnessProperty',
                'title': 'Brightness',
                'type': 'integer',
                'unit': 'percent',
                'minimum': 0,
                'maximum': 100,
            },
            self.level
        )

        self.sengled_dev.set_attribute_update_callback(self.update_property)

    def update_property(self, name, value):
        """Poll the device for changes."""
        prop = None
        if name == 'switch':
            prop = self.properties['on']
        elif name == 'brightness':
            prop = self.properties['level']
        else:
            return

        prop.set_cached_value(value)
        self.notify_property_changed(prop)

    @property
    def on(self):
        """Determine whether or not the device is on."""
        return self.sengled_dev.switch

    @property
    def level(self):
        """Determine the brightness."""
        return self.sengled_dev.brightness
