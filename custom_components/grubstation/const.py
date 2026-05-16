"""Constants for GrubStation."""

from logging import Logger, getLogger
from typing import Final

from wakeonlan import BROADCAST_IP, DEFAULT_PORT

LOGGER: Logger = getLogger(__package__)

ACTION_TURN_OFF: Final = "turn_off"

# API response keys (from the remote agent)
API_KEY_OS: Final = "os"
API_KEY_SERVICE_MANAGER: Final = "service_manager"
API_KEY_STATUS: Final = "status"
API_KEY_VERSION: Final = "version"

# UI attribute labels (for Home Assistant)
ATTR_AGENT_SERVICE_MANAGER: Final = "agent_service_manager"
ATTR_AGENT_STATUS: Final = "agent_status"
ATTR_AGENT_VERSION: Final = "agent_version"
ATTR_HOST_OS: Final = "host_os"
ATTR_LAST_AGENT_ACCESSIBLE: Final = "last_agent_accessible"

CONF_AGENT_PORT: Final = "agent_port"
CONF_AGENT_TOKEN: Final = "agent_token"
CONF_BOOT_OPTIONS: Final = "boot_options"
CONF_TURN_OFF_ACTION: Final = "turn_off_action"

DEFAULT_NAME: Final = "GrubStation"

DOMAIN: Final = "grubstation"

DEFAULT_BROADCAST_ADDRESS: Final = BROADCAST_IP
DEFAULT_BROADCAST_PORT: Final = DEFAULT_PORT
DEFAULT_AGENT_PORT: Final = 8081
DEFAULT_BOOT_OPTION_NONE: Final = "(none)"

WEBHOOK_NAME: Final = "GrubStation Ingest"
WEBHOOK_MAX_PAYLOAD_BYTES: Final = 102400  # 100 KB limit

GRUBSTATION_AGENT_URL: Final = "https://github.com/jjack/grubstation"
GRUB_VIEW_URL: Final = "/api/grubstation/{mac_address}"

SAVE_DELAY: Final = 15.0  # seconds to debounce saving to storage after changes

WAIT_FOR_HOST_POWER_SECONDS: Final = 10

PING_COUNT: Final = 1
PING_TIMEOUT_SECONDS: Final = 1
