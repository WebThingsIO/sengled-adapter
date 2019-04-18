"""Sengled adapter for Mozilla WebThings Gateway."""

from gateway_addon import Property


class SengledProperty(Property):
    """Sengled property type."""

    def __init__(self, device, name, description, value):
        """
        Initialize the object.

        device -- the Device this property belongs to
        name -- name of the property
        description -- description of the property, as a dictionary
        value -- current value of this property
        """
        Property.__init__(self, device, name, description)
        self.set_cached_value(value)

    def set_value(self, value):
        """
        Set the current value of the property.

        value -- the value to set
        """
        success = False
        if self.name == 'on':
            success = self.device.sengled_dev.toggle(value)
        elif self.name == 'level':
            success = self.device.sengled_dev.set_brightness(value)
        else:
            return

        if success:
            self.set_cached_value(value)
            self.device.notify_property_changed(self)
