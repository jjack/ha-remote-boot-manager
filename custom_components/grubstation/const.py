"""Constants for GrubStation."""

from logging import Logger, getLogger
from typing import Final

from wakeonlan import BROADCAST_IP, DEFAULT_PORT

LOGGER: Logger = getLogger(__package__)

ACTION_TURN_OFF: Final = "turn_off"

CONF_DAEMON_PORT: Final = "daemon_port"
CONF_DAEMON_SERVICE_MANAGER: Final = "daemon_service_manager"
CONF_DAEMON_TOKEN: Final = "daemon_token"  # noqa: S105
CONF_DAEMON_VERSION: Final = "daemon_version"
CONF_BOOT_OPTIONS: Final = "boot_options"
CONF_HOST_OS: Final = "host_os"
CONF_TURN_OFF_ACTION: Final = "turn_off_action"

DEFAULT_NAME: Final = "GrubStation"

DOMAIN: Final = "grubstation"

DEFAULT_BROADCAST_ADDRESS: Final = BROADCAST_IP
DEFAULT_BROADCAST_PORT: Final = DEFAULT_PORT
DEFAULT_DAEMON_PORT: Final = 8081
DEFAULT_BOOT_OPTION_NONE: Final = "(none)"

WEBHOOK_NAME: Final = "GrubStation Ingest"
WEBHOOK_MAX_PAYLOAD_BYTES: Final = 102400  # 100 KB limit

GRUBSTATION_DAEMON_URL: Final = "https://github.com/jjack/grubstation-daemon"
GRUB_VIEW_URL: Final = "/api/grubstation/{mac_address}"

SAVE_DELAY: Final = 15.0  # seconds to debounce saving to storage after changes

SIGNAL_NEW_HOST: Final = f"{DOMAIN}_new_host"
SIGNAL_HOST_UPDATED: Final = f"{DOMAIN}_host_updated"
SIGNAL_HOST_REMOVED: Final = f"{DOMAIN}_host_removed"

WAIT_FOR_HOST_POWER_SECONDS: Final = 10

PING_COUNT: Final = 1
PING_TIMEOUT_SECONDS: Final = 1
