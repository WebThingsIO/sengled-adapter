"""Sengled adapter for Mozilla WebThings Gateway."""

from gateway_addon import Adapter, Database

from .client import SengledClient
from .sengled_device import SengledDevice


_TIMEOUT = 3


class SengledAdapter(Adapter):
    """Adapter for Sengled smart home devices."""

    def __init__(self, verbose=False):
        """
        Initialize the object.

        verbose -- whether or not to enable verbose logging
        """
        self.name = self.__class__.__name__
        Adapter.__init__(self,
                         'sengled-adapter',
                         'sengled-adapter',
                         verbose=verbose)

        self.client = None

        database = Database(self.package_name)
        if database.open():
            config = database.load_config()

            if 'username' in config and len(config['username']) > 0 and \
                    'password' in config and len(config['password']) > 0:
                self.client = SengledClient(
                    config['username'],
                    config['password']
                )
                self.client.login()

            database.close()

        self.pairing = False
        self.start_pairing(_TIMEOUT)

    def start_pairing(self, timeout):
        """
        Start the pairing process.

        timeout -- Timeout in seconds at which to quit pairing
        """
        if self.client is None or self.pairing:
            return

        self.pairing = True

        self.client.login()
        devices = self.client.get_devices(force_update=True)
        for dev in devices:
            if not self.pairing:
                break

            _id = 'sengled-' + dev.uuid
            if _id not in self.devices:
                device = SengledDevice(self, _id, dev)
                self.handle_device_added(device)

        self.pairing = False

    def cancel_pairing(self):
        """Cancel the pairing process."""
        self.pairing = False
