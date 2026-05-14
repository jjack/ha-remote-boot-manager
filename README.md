# GrubStation for Home Assistant

![GitHub release (latest by date)](https://img.shields.io/github/v/release/jjack/ha-grubstation)
[![Python and Coverage](https://github.com/jjack/ha-grubstation/actions/workflows/test.yml/badge.svg)](https://github.com/jjack/ha-grubstation/actions/workflows/test.yml)
[![CodeQL](https://github.com/jjack/ha-grubstation/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/jjack/ha-grubstation/actions/workflows/github-code-scanning/codeql)
[![Codecov branch](https://img.shields.io/codecov/c/github/jjack/ha-grubstation)](https://app.codecov.io/gh/jjack/ha-grubstation)

### Select your next boot OS, boot your machine, and shut it down all from Home Assistant.

**GrubStation** combines Wake-on-Lan functionality with the ability to select your next boot OS (even when your machine is off).

* **Dynamic Host Configuration**: Hosts automatically report their available OS list (e.g., Ubuntu, Windows) to Home Assistant.
* **Next Boot Selection**: Change the next boot OS via a dropdown `select` entity.
* **Wake-on-LAN & Power Status**: Sends magic packets to wake hosts and tracks power state via ping.
* **Turn Off Remote Host**: Turn _off_ your remote hosts from Home Assistant.

## Who is GrubStation For?
* People with a multi-boot system and a bluetooth keyboard.
* Multi-boot system that you need to programatically and dynamically change the boot OS.
* People who have difficulty with physical access to a computer to change the next boot target for GRUB.
* TODO: Insert other use cases here.

## How Does it Work?

At the core of this integration is `grubstation`. It is a GO-based agent that performs three functions:
1) Configures GRUB to look for its next-boot option from Home Assistant, falling back to your default boot option on error.
2) Parses your GRUB configuration and pushes the available boot options to Home Assistant.
3) Runs as a daemon on your machine (less than 5MB RAM usage) to listen for Home Assistant shutdown requests.

## Installation

### Via HACS (Recommended)
1. Open HACS in Home Assistant.
2. Go to **Integrations**.
3. Click the 3 dots in the top right -> **Custom repositories**.
4. Add `jjack/ha-grubstation` as an Integration.
5. Download it and restart Home Assistant.

### Manual Installation
1. Download the .zip from link_to_latest.zip
2. Copy the `custom_components/grubstation` directory to your Home Assistant `custom_components` directory.
3. Restart Home Assistant.

## Configuration & Setup

1. Go to **Settings** -> **Devices & Services** in Home Assistant.
2. Click **+ Add Integration** and search for "GrubStation".
3. **IMPORTANT:** During setup, Home Assistant will generate a unique, secure `webhook_id`. **You must copy and save this ID!** It is only shown to you once for security reasons. You will need it to configure your remote hosts.

## GrubStation Agent (Client Setup)

For this integration to work properly, you must install `grubstation` on **every** target host you want to manage. It doesn't need to be installed as a daemon, but it must at least run once to push your available boot options to Home Assistant and to configure GRUB.

### Basic Agent Setup:
1. Download the latest [GrubStation](https://github.com/jjack/grubstation/releases/latest) agent.
2. Install it on your target host.
3. Run `grubstation setup` to auto-detect as much of the configuration as possible. For the majority of installs, you can just mash "Enter" until you get to the `webhook_id` part.
4. Run the agent manually with `grubstation options push`. The integration uses a **Trust On First Use (TOFU)** model; the first time an agent pings Home Assistant with your secure Webhook ID, it will be automatically registered and appear instantly as a new Device.

*(For detailed installation instructions, see the grubstation repository).*

## Usage

### Screenshots

TODO: Take some.

### Configuring Graceful Shutdowns
By default, turning off a host's `switch` entity will attempt to use the built-in agent shutdown command (which requires `grubstation` to be running and accessible). However, you can also map a custom Home Assistant **Action** to the host if you do not wish to use `grubstation` in daemon mode or you have your own Actions:
1. Go to **Settings** -> **Devices & Services** and find the GrubStation integration.
2. Click **Configure** on the integration card (gear icon) to open the options flow.
3. Select "Configure a Host" and then your host.
4. Define a **Shutdown Action**. This action (which can be a script, a shell command, or any other HA service call) will be triggered when you toggle the host's switch to "off".

### Regenerating the Webhook ID
If you suspect your Webhook ID has been compromised, you can securely regenerate it:
1. Go to **Settings** -> **Devices & Services** and find the GrubStation integration.
2. Click the three dots (menu) on the integration card and select **Reconfigure**.
3. Follow the prompts to generate a new Webhook ID.
*(Note: Regenerating this ID will immediately break the connection with your existing agents until they are updated with the new ID.)*

### Viewing the Webhook ID
If you add a new host or need to view your Webhook ID:
1. Go to **Settings** -> **Devices & Services** and find the GrubStation integration.
2. Click **Configure** on the integration card (gear icon) to open the options flow.
3. Select "View Webhook ID" to view it.
*(Note: You can click the X or "Submit" to get out of that window. "Submit" won't actually change anything.)*

### API Endpoints
This integration exposes two primary endpoints for managing remote hosts:
* **Agent Webhook Endpoint** (`/api/webhook/{webhook_id}`): Used by the `grubstation` to securely push OS lists, network states, and metadata to Home Assistant.
* **GRUB Endpoint** (`/api/grubstation/{mac_address}`): A smart endpoint queried by GRUB at startup to determine the next boot option. **Note:** To prevent unauthorized state resets during testing, this endpoint is read-only unless the correct `token` (your Webhook ID) is provided.

## Tips & Hints

* **Testing GRUB**: The GRUB endpoint is read-only by default so you can safely test it. To actually consume the next boot option, append `?token=YOUR_WEBHOOK_ID` to the request URL.
* **IP address or hostname changes**: If a host's IP address or hostname changes, the integration will attempt to update the Device Registry automatically. If you need to remove an old host, you can do so directly from the Home Assistant UI via the device page.
* **Testing Network Configurations**: You can manually adjust a host's `address`, `broadcast_address`, and `broadcast_port` via the **Configure** button (Options Flow). Note that these changes are temporary and will be automatically overwritten by the agent on its next check-in. They should only be used for testing or troubleshooting (e.g. if you are dealing with complex subnets or VLANs).



This integration creates a new Home Assistant Device for each host discovered by the agent. Each device will have the following entities:

*   **Switch**: A `switch` entity named `[Host Name] Wake` that sends the Wake-on-LAN magic packet and tracks the host's power state via ping.

> [!NOTE]
> **Ping (ICMP) Requirements:** This integration uses the `icmplib` library for tracking host power state. In some environments (like Home Assistant Container or Docker), you may need to grant Home Assistant permission to send ICMP packets by setting the following sysctl on the host machine: `sysctl -w net.ipv4.ping_group_range="0 2147483647"`.

*   **Select**: A `select` entity named `[Host Name] Next Boot Option` that allows you to choose which OS the host should boot into on its next restart.

