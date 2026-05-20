# GrubStation for Home Assistant

![GitHub release (latest by date)](https://img.shields.io/github/v/release/jjack/ha-grubstation)
[![Python and Coverage](https://github.com/jjack/ha-grubstation/actions/workflows/test.yml/badge.svg)](https://github.com/jjack/ha-grubstation/actions/workflows/test.yml)
[![CodeQL](https://github.com/jjack/ha-grubstation/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/jjack/ha-grubstation/actions/workflows/github-code-scanning/codeql)
[![Codecov branch](https://img.shields.io/codecov/c/github/jjack/ha-grubstation)](https://app.codecov.io/gh/jjack/ha-grubstation)

**GrubStation** is a powerful Home Assistant integration that gives you full remote control over your multi-boot machines. It combines Wake-on-LAN functionality with the ability to select your next boot OS—even when the machine is completely powered off.

## Key Features

*   🚀 **Dynamic OS Discovery**: Hosts automatically report their available GRUB boot entries (e.g., Ubuntu, Windows, Fedora) to Home Assistant.
*   🔄 **Next-Boot Selection**: Choose your next operating system via a simple dropdown `select` entity before you even turn the machine on.
*   🔌 **Power Management**: Integrated Wake-on-LAN (WoL) to boot your machine and remote shutdown capabilities.
*   📡 **Real-time Status**: Monitors the health and status of the remote agent.
*   🛡️ **Secure by Design**: Uses a unique Webhook ID for secure communication and a **Trust On First Use (TOFU)** model for effortless device registration.

## Who is GrubStation For?

*   **Multi-Boot Power Users**: Switch between OSs (like Linux for work and Windows for gaming) without needing to be at the physical machine during the boot process.
*   **Headless Remote Management**: Manage multi-boot servers or workstations where physical input (keyboard/monitor) isn't always available or convenient.
*   **Automation Enthusiasts**: Create automations to boot into a specific OS based on triggers, such as booting into Windows when a "Gaming Mode" scene is activated.
*   **Accessibility**: Assist users who may have difficulty physically reaching their machine or interacting with the GRUB menu during startup.

## How It Works

GrubStation consists of two parts: this Home Assistant integration and the [GrubStation Agent](https://github.com/jjack/grubstation) (a lightweight Go-based daemon).

1.  **Boot Configuration**: The agent configures GRUB to fetch its next-boot instruction from Home Assistant at startup.
2.  **State Reporting**: The agent parses your GRUB configuration and securely pushes the list of available OSs to Home Assistant.
3.  **Remote Execution**: The agent listens for authenticated shutdown requests from Home Assistant to perform graceful power-offs.

## Installation

### Via HACS (Recommended)

1.  Ensure [HACS](https://hacs.xyz/) is installed and configured.
2.  Navigate to **HACS** > **Integrations**.
3.  Click the three dots in the top-right corner and select **Custom repositories**.
4.  Add `jjack/ha-grubstation` with the category **Integration**.
5.  Find "GrubStation" in the HACS list, click **Download**, and restart Home Assistant.

### Manual Installation

1.  Download the [latest release](https://github.com/jjack/ha-grubstation/releases/latest) zip file.
2.  Extract the `custom_components/grubstation` folder into your Home Assistant's `custom_components` directory.
3.  Restart Home Assistant.

## Configuration & Setup

### 1. Integration Setup
1.  Navigate to **Settings** > **Devices & Services**.
2.  Click **+ Add Integration** and search for **GrubStation**.
3.  **IMPORTANT**: A unique **Webhook ID** will be generated. Copy and save this ID immediately; it is required to configure your remote hosts and will not be displayed again for security reasons.

### 2. Agent Setup (Remote Host)
The [GrubStation Agent](https://github.com/jjack/grubstation) must be installed on every host you wish to manage.

1.  Download the latest [agent binary](https://github.com/jjack/grubstation/releases/latest) for your host OS.
2.  Run `grubstation setup` and follow the prompts. Use the Webhook ID generated in Step 1.
3.  Start the agent or run `grubstation options push` to register the host with Home Assistant.
4.  The host will appear instantly as a new Device in Home Assistant once it checks in.

## Entities Provided

Each discovered host creates a new Device with the following entities:

| Entity | Type | Description |
| :--- | :--- | :--- |
| **Power** | `switch` | Toggles the host power. Uses WoL to turn on and the agent (or custom action) to turn off. |
| **Next Boot Option** | `select` | Choose the OS for the next boot. Reset to `(none)` after successful consumption. |
| **Agent Status** | `binary_sensor` | Indicates if the remote agent is currently reachable and healthy. |
| **Last Successful Check** | `sensor` | Diagnostic sensor showing when the agent last contacted Home Assistant. |

> [!TIP]
> **Diagnostic Data**: The Agent sensors include detailed attributes like `Agent Version`, `Service Manager` (e.g., systemd), and a `Recent Activity` log for troubleshooting.

## Advanced Usage

### Custom Shutdown Actions
By default, turning off the **Power** switch sends a command to the remote agent. If you prefer to use a different method (like a custom script or shell command):
1.  Go to **Settings** > **Devices & Services** > **GrubStation**.
2.  Click **Configure** on the integration card.
3.  Select **Configure a Host** and choose your host.
4.  Define a **Shutdown Action**. This will override the default agent command.

### Troubleshooting Network Issues
If your host is on a different subnet or VLAN, you may need to manually adjust network settings:
1.  In the **Configure a Host** menu (see above), you can manually set the **Agent Address**, **Broadcast Address**, and **Broadcast Port**.
2.  *Note: These manual overrides will be maintained until the agent next checks in and provides updated auto-discovered values.*

### Services
GrubStation exposes two services for advanced automation:

*   **`grubstation.send_turn_on_command`**: Sends a Wake-on-LAN magic packet. Useful for waking machines that haven't been registered as devices yet.
*   **`grubstation.send_turn_off_command`**: Sends a shutdown command to a specific agent address/port.

## Troubleshooting & Requirements

*   **GRUB Endpoint**: The GRUB endpoint (`/api/grubstation/{mac_address}`) is read-only for safety. To test it manually and allow state changes, append `?token=YOUR_WEBHOOK_ID`.

---

*For detailed agent configuration and GRUB technical details, please refer to the [GrubStation Agent repository](https://github.com/jjack/grubstation).*
