# Huerizon – Dynamic Sky Lighting for Home Assistant

> [!CAUTION]
> Huerizon is in development. It doesn't work yet! The earlier version ran entirely on edge hardware using MQTT, and I’m porting that functionality into a native integration.

### Current Focus
- Making setup smoother and catching config errors early  
- Improving error handling and logs for MQTT camera connections  
- Adding optional smoothing for brightness and color transitions  
- Adding official icons and logos once they’re approved in the Home Assistant brands repo  
- Expanding localization and documentation  
- Building a companion **Raspberry Pi SkyCam** repo for anyone who doesn’t have their own MQTT camera  

---

## 🖥️ Companion Project — Huerizon SkyCam

Alongside the main integration, I’m also working on **Huerizon SkyCam**, a lightweight Raspberry Pi setup that automatically detects sky color and brightness, then sends it to MQTT for Home Assistant to read.  

### Recommended Hardware
- Raspberry Pi Zero 2 W or newer  
- Raspberry Pi HQ Camera Module or v3 Wide Camera  
- Raspberry Pi OS Lite (Bookworm or later)  
- Optional: weatherproof case if you’re mounting it outdoors  

### Setup Overview
1. Clone the SkyCam repo (coming soon).  
2. Run the included setup script. It will:  
   - Create a Python virtual environment and install dependencies (`numpy`, `pillow`, `paho-mqtt`)  
   - Configure **libcamera** for automatic image capture  
   - Create a `systemd` service to continuously publish to these topics:
     - `sky/color` → hue and saturation  
     - `sky/brightness` → light intensity  
     - `sky/image/original` and `sky/image/filtered` → optional images for testing  

The Huerizon integration automatically detects those MQTT topics and syncs your lights based on real-time sky data.  
If you already have your own MQTT camera, you can skip SkyCam and just make sure your device publishes to the same topics.

---

## 🗺️ Roadmap

### **v1.0 - Core Sky Sync**
✅ MQTT color and brightness publishing  
✅ Camera and light selection through the UI setup  
✅ Basic automation and Apply Sky blueprint  
✅ Fully compatible with Home Assistant 2025.10+

### **v1.1 - Enhanced Integration**
- Live entity previews for color and brightness  
- Optional adaptive update timing based on lighting conditions  
- Adjustable transition duration for smoother light fades  
- Expanded service calls (manual sync and refresh options)  

### **v1.2 - Smart Environment Awareness**
- Dynamic updates using time of day and weather conditions  
- Integration with forecast and sun entities for better blending  
- Support for multiple sky sources or MQTT topics  

### **v1.3 - UI and Ecosystem Polish**
- Official icons and logos once approved in Home Assistant brands  
- Improved configuration panel with live sky preview  
- Localization in more languages  
- Example dashboards and advanced automations  
