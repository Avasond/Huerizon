# Huerizon – Dynamic Sky Lighting for Home Assistant

---
## Installation

1. Go to **HACS → Integrations → Custom Repositories**.
2. Add this repository URL and select the category **Integration**.
3. Search for **Huerizon** and click **Download**.
4. Restart Home Assistant, then add the integration via **Settings → Devices & Services → Add Integration → Huerizon**.

## Configuration Options


**Source Camera**  
Optional camera entity for sky images. Nice for troubleshooting!

**Target Lights**  
Select one or more lights that should receive updates based on the sky data. These lights will update whenever new color or brightness data is published.

**Input Format**  
Defines how color data is formatted from your source device or MQTT topic.  
- `xy`: CIE 1931 xy color space (default)  
- `hs`: Hue/Saturation  
- `rgb`: Red/Green/Blue  
- `color_temp`: Color temperature (Kelvin or Mireds)

**Hue Scale**  
How hue values are scaled in the source data.  
- `auto`: Detect automatically  
- `0–360`: Standard degrees of hue  
- `0–255`: Typical for some sensors or APIs  
- `0–1`: Normalized decimal values

**Percent Scale**  
How saturation and brightness are represented in the source data.  
Options include `auto`, `0–100`, `0–255`, or `0–1`.

**Apply Mode**  
Specifies which color mode Huerizon should prioritize when applying updates.  
Example: Use `xy` if your Hue bulbs respond most accurately in CIE color mode.

**Active Start / Active End**  
Define the time range (HH:MM:SS) when Huerizon is active. This allows precise scheduling (e.g., 18:00–23:00).

**Active Days**  
Select the days of the week when updates should be applied (e.g., weekdays only).

**Min Delta**  
The minimum threshold of color change required to trigger a new update. Helps reduce flicker or unnecessary updates.

**Rate Limit (Seconds)**  
Sets the minimum time between consecutive updates. Ideal for MQTT sources that send frequent messages.

---

## Companion Project — Huerizon SkyCam

Alongside the main integration, I’m also working on **Huerizon SkyCam**, a lightweight Raspberry Pi setup that automatically detects sky color and brightness, then sends it to MQTT for Home Assistant to read. If you already have a camera capable of providing color and brightness data to the integration, it will accept and format most data. Let me know if your format isn't in the configuration walkthrough!

### Recommended Hardware
- Raspberry Pi Zero 2 W or newer, whatever you have in the electronics drawer.
- Raspberry Pi HQ Camera Module or v3 Wide Camera  
- Raspberry Pi OS Lite (Bookworm or later)  

### Setup Overview
1. Clone the SkyCam repo if you need it (coming soon).  
2. Run the included setup script. It will:  
   - Create a Python virtual environment and install dependencies (`numpy`, `pillow`, `paho-mqtt`)  
   - Configure **libcamera** for automatic image capture  
   - Create a `systemd` service to continuously publish to these topics:
     - `sky/color` → hue and saturation  
     - `sky/brightness` → light intensity  
     - `sky/image/original` and `sky/image/filtered` → optional images for testing  

The Huerizon integration uses these MQTT topics and syncs your lights based on real-time sky data.  
If you already have your own MQTT camera you can skip SkyCam, there is no restriction about which topics your camera needs to publish to as long as it is a selectable entity in HASS.

---

## Roadmap

### **v1.0 - Core Sky Sync**
✅ MQTT color and brightness publishing  
✅ Camera and light selection through the UI setup  
✅ Basic automation and Apply Sky blueprint  
✅ Fully compatible with Home Assistant 2025.10+
Live entity previews for color and brightness  
Expanded service calls (manual sync and refresh options)  

