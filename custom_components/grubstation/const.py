"""Constants for GrubStation."""

from logging import Logger, getLogger
from typing import Final

LOGGER: Logger = getLogger(__package__)

ACTION_TURN_OFF: Final = "turn_off"

CONF_AGENT_VERSION: Final = "agent_version"
CONF_BOOT_OPTIONS: Final = "boot_options"
CONF_OS_SERVICE: Final = "os_service"
CONF_TURN_OFF: Final = "turn_off"

DEFAULT_NAME: Final = "GrubStation"

DOMAIN: Final = "grubstation"

DEFAULT_AGENT_PORT: Final = 8081
DEFAULT_BOOT_OPTION_NONE: Final = "(none)"

WEBHOOK_NAME: Final = "GrubStation Ingest"
WEBHOOK_MAX_PAYLOAD_BYTES: Final = 102400  # 100 KB limit

GRUB_OS_REPORTER_URL: Final = "https://github.com/jjack/grubstation-cli"
GRUB_VIEW_URL: Final = "/api/grubstation/{mac_address}"

SAVE_DELAY: Final = 15.0  # seconds to debounce saving to storage after changes

SIGNAL_NEW_HOST: Final = f"{DOMAIN}_new_host"

WAIT_FOR_HOST_POWER_SECONDS: Final = 10

PING_COUNT: Final = 1
PING_TIMEOUT_SECONDS: Final = 1
