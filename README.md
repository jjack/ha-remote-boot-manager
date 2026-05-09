# GrubStation for Home Assistant

![GitHub](https://img.shields.io/github/license/jjack/ha-grubstation)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/jjack/ha-grubstation)
[![Python and Coverage](https://github.com/jjack/ha-grubstation/actions/workflows/test.yml/badge.svg)](https://github.com/jjack/ha-grubstation/actions/workflows/test.yml)
[![CodeQL](https://github.com/jjack/ha-grubstation/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/jjack/ha-grubstation/actions/workflows/github-code-scanning/codeql)
[![Codecov branch](https://img.shields.io/codecov/c/github/jjack/ha-grubstation)](https://app.codecov.io/gh/jjack/ha-grubstation)

Manage and automate the booting of your remote bare-metal hosts in Home Assistant.

## Features
* **Dynamic OS Discovery**: Hosts automatically report their available OS list (e.g., Ubuntu, Windows) to Home Assistant. (requires `grubstation-cli` to be installed on the host)
* **Next Boot Selection**: Change the next boot OS via a dropdown `select` entity.
* **Wake-on-LAN & Power Status**: Sends magic packets to wake hosts and tracks power state via ping.
* **GRUB Endpoint**: Exposes a smart endpoint for GRUB to fetch the selected OS and automatically reset state to prevent boot loops.
* **Secure Webhooks**: Uses auto-generated, secure webhooks for agent-to-HA communication.


This integration creates a new Home Assistant Device for each host discovered by the agent. Each device will have the following entities:

*   **Switch**: A `switch` entity named `[Host Name] Wake` that sends the Wake-on-LAN magic packet and tracks the host's power state via ping.

> [!NOTE]
> **Ping (ICMP) Requirements:** This integration uses the `icmplib` library for tracking host power state. In some environments (like Home Assistant Container or Docker), you may need to grant Home Assistant permission to send ICMP packets by setting the following sysctl on the host machine: `sysctl -w net.ipv4.ping_group_range="0 2147483647"`.

*   **Select**: A `select` entity named `[Host Name] Next Boot Option` that allows you to choose which OS the host should boot into on its next restart.

## Installation

### Via HACS (Recommended)
1. Open HACS in Home Assistant.
2. Go to **Integrations**.
3. Click the 3 dots in the top right -> **Custom repositories**.
4. Add `jjack/ha-grubstation` as an Integration.
5. Download it and restart Home Assistant.

### Manual Installation
1. Copy the `custom_components/grubstation` directory to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## Configuration & Setup

1. Go to **Settings** -> **Devices & Services** in Home Assistant.
2. Click **+ Add Integration** and search for "GrubStation".
3. **IMPORTANT:** During setup, Home Assistant will generate a unique, secure `webhook_id`. **You must copy and save this ID and the example configuration!** It is only shown to you once for security reasons. You will need it to configure your remote hosts.

## Remote Boot Agent (Client Setup)

For this integration to work, you must install a bare-metal GO agent on **every** target host you want to manage.

### Basic Agent Setup:
1. Download the latest [grubstation-cli](https://github.com/jjack/grubstation-cli/releases/latest).
2. Install the agent on your target host.
3. Run `grubstation-cli setup` to auto-detect as much of the configuration as possible (GRUB, init system, network info, etc.) and configure it with GRUB and your init system. This uses the `webhook_id` you saved during the integration setup.
4. Run the agent manually with `grubstation-cli options push`. The integration uses a **Trust On First Use (TOFU)** model; the first time an agent pings Home Assistant with your secure Webhook ID, it will be automatically registered and appear instantly as a new Device!

*(For detailed installation instructions, see the grubstation-cli repository).*

## Usage

### Configuring Graceful Shutdowns
By default, turning off a host's `switch` entity will attempt to use the built-in agent shutdown command (which requires the host's IP and API Key to be accessible). However, you can also map a custom Home Assistant **Action** to the host:
1. Go to **Settings** -> **Devices & Services** and find the GrubStation integration.
2. Click **Configure** on the integration card to open the options flow.
3. Select your desired host.
4. Define a **Shutdown Action**. This action (which can be a script, a shell command, or any other HA service call) will be triggered when you toggle the host's switch to "off".

### Regenerating the Webhook ID
If you suspect your Webhook ID has been compromised, you can securely regenerate it:
1. Go to **Settings** -> **Devices & Services** and find the GrubStation integration.
2. Click the three dots (menu) on the integration card and select **Reconfigure**.
3. Follow the prompts to generate a new Webhook ID.
*(Note: Regenerating this ID will immediately break the connection with your existing agents until they are updated with the new ID.)*

### API Endpoints
This integration exposes two primary endpoints for managing remote hosts:
* **Agent Webhook Endpoint** (`/api/webhook/{webhook_id}`): Used by the `grubstation-cli` to securely push OS lists, network states, and metadata to Home Assistant.
* **GRUB Endpoint** (`/api/grubstation/{mac_address}`): A smart endpoint queried by GRUB at startup to determine the next boot option. **Note:** To prevent unauthorized state resets during testing, this endpoint is read-only unless the correct `token` (your Webhook ID) is provided.

## Tips & Hints

* **Testing GRUB**: The GRUB endpoint is read-only by default so you can safely test it. To actually consume the next boot option, append `?token=YOUR_WEBHOOK_ID` to the request URL.
* **IP address or hostname changes**: If a host's IP address or hostname changes, the integration will attempt to update the Device Registry automatically. If you need to remove an old host, you can do so directly from the Home Assistant UI via the device page.
* **Testing Network Configurations**: You can manually adjust a host's `address`, `broadcast_address`, and `broadcast_port` via the **Configure** button (Options Flow). Note that these changes are temporary and will be automatically overwritten by the agent on its next check-in. They should only be used for testing or troubleshooting (e.g. if you are dealing with complex subnets or VLANs).
