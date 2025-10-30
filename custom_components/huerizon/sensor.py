"""Huerizon Sensor Entities - handles sky sync HSB values."""

from __future__ import annotations

import json
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.components import mqtt

from .const import (
    DOMAIN,
    CONF_SOURCE_MODE,
    SOURCE_MODE_JSON,
    SOURCE_MODE_STATES,
    CONF_JSON_SENSOR,
    CONF_STATE_H_ENTITY,
    CONF_STATE_S_ENTITY,
    CONF_STATE_B_ENTITY,
    CONF_HUE_SCALE,
    CONF_PERCENT_SCALE,
    SCALE_AUTO,
)

from .helpers import extract_hsb_from_json, extract_hsb_from_states


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Huerizon sensors dynamically based on config."""
    mode = entry.options.get(CONF_SOURCE_MODE, SOURCE_MODE_JSON)
    hue_scale = entry.options.get(CONF_HUE_SCALE, SCALE_AUTO)
    pct_scale = entry.options.get(CONF_PERCENT_SCALE, SCALE_AUTO)

    sensors = []

    if mode == SOURCE_MODE_JSON:
        json_entity_id = entry.options.get(CONF_JSON_SENSOR)
        if json_entity_id:
            sensors.append(
                HuerizonJsonSensor(hass, json_entity_id, hue_scale, pct_scale)
            )

    elif mode == SOURCE_MODE_STATES:
        h_ent = entry.options.get(CONF_STATE_H_ENTITY)
        s_ent = entry.options.get(CONF_STATE_S_ENTITY)
        b_ent = entry.options.get(CONF_STATE_B_ENTITY)
        if all([h_ent, s_ent, b_ent]):
            sensors.append(
                HuerizonStateSensor(hass, h_ent, s_ent, b_ent, hue_scale, pct_scale)
            )

    async_add_entities(sensors)


class HuerizonJsonSensor(SensorEntity):
    """Sensor that reads a single JSON payload (MQTT or state)."""

    def __init__(self, hass, entity_id: str, hue_scale: str, pct_scale: str):
        self.hass = hass
        self._entity_id = entity_id
        self._attr_name = "Huerizon Sky HSB"
        self._attr_unique_id = f"{DOMAIN}_{entity_id}_hsb"
        self._attr_native_unit_of_measurement = None
        self._hue_scale = hue_scale
        self._pct_scale = pct_scale
        self._state = None

    async def async_added_to_hass(self):
        """Subscribe to MQTT if entity_id is an MQTT topic; else use HA state listener."""
        if self._entity_id.startswith("mqtt."):
            await mqtt.async_subscribe(
                self.hass, self._entity_id, self._message_received
            )
        else:
            self.async_on_remove(
                self.hass.helpers.event.async_track_state_change_event(
                    [self._entity_id], self._handle_state_event
                )
            )

    async def _handle_state_event(self, event):
        """Handle Home Assistant state updates."""
        state = event.data.get("new_state")
        if not state or not state.state:
            return
        self._process_payload(state.state)

    async def _message_received(self, msg):
        """Handle direct MQTT message."""
        self._process_payload(msg.payload)

    def _process_payload(self, payload):
        try:
            h, s, b, notes = extract_hsb_from_json(
                payload, self._hue_scale, self._pct_scale, self._pct_scale
            )
            if None not in (h, s, b):
                self._state = {"hue": h, "saturation": s, "brightness": b}
                self.async_write_ha_state()
        except Exception as e:
            self._state = None
            self._attr_extra_state_attributes = {"error": str(e)}

    @property
    def native_value(self):
        return json.dumps(self._state) if self._state else None


class HuerizonStateSensor(SensorEntity):
    """Sensor that reads H, S, and B values from three entities."""

    def __init__(self, hass, h_ent, s_ent, b_ent, hue_scale, pct_scale):
        self.hass = hass
        self._attr_name = "Huerizon Sky HSB"
        self._attr_unique_id = f"{DOMAIN}_{h_ent}_{s_ent}_{b_ent}_hsb"
        self._attr_native_unit_of_measurement = None
        self._state = None
        self._h_ent = h_ent
        self._s_ent = s_ent
        self._b_ent = b_ent
        self._hue_scale = hue_scale
        self._pct_scale = pct_scale

    async def async_added_to_hass(self):
        """Listen for changes on all three sensors."""
        self.async_on_remove(
            self.hass.helpers.event.async_track_state_change_event(
                [self._h_ent, self._s_ent, self._b_ent],
                self._handle_state_event,
            )
        )

    async def _handle_state_event(self, _):
        """When any sensor updates, recompute combined HSB."""
        try:
            h_state = self.hass.states.get(self._h_ent)
            s_state = self.hass.states.get(self._s_ent)
            b_state = self.hass.states.get(self._b_ent)

            if not all([h_state, s_state, b_state]):
                return

            h, s, b, notes = extract_hsb_from_states(
                h_state.state,
                s_state.state,
                b_state.state,
                self._hue_scale,
                self._pct_scale,
                self._pct_scale,
            )

            if None not in (h, s, b):
                self._state = {"hue": h, "saturation": s, "brightness": b}
                self.async_write_ha_state()
        except Exception as e:
            self._attr_extra_state_attributes = {"error": str(e)}

    @property
    def native_value(self):
        return json.dumps(self._state) if self._state else None
