from __future__ import annotations

from collections.abc import Callable
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.components import mqtt
from homeassistant.components.camera import Camera
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    TOPIC_IMAGE_ORIGINAL,
    TOPIC_IMAGE_FILTERED,
    CAMERA_ORIGINAL_NAME,
    CAMERA_FILTERED_NAME,
)

IMAGES = {
    TOPIC_IMAGE_ORIGINAL: CAMERA_ORIGINAL_NAME,
    TOPIC_IMAGE_FILTERED: CAMERA_FILTERED_NAME,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Huerizon MQTT-backed camera entities from a config entry."""
    entities: list[HuerizonCamera] = [
        HuerizonCamera(
            hass=hass,
            topic=topic,
            name=name,
            entry_id=entry.entry_id,
            device_name=entry.title or "Huerizon Sky Sync",
        )
        for topic, name in IMAGES.items()
    ]
    async_add_entities(entities)


class HuerizonCamera(Camera):
    """A simple camera that renders the last JPEG payload seen on an MQTT topic."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        topic: str,
        name: str,
        entry_id: str,
        device_name: str,
    ) -> None:
        super().__init__()
        self.hass = hass
        self._topic = topic
        self._attr_name = name
        self._image: bytes | None = None
        self._unsub: Callable[[], None] | None = None
        self._attr_unique_id = f"{entry_id}_camera_{topic.replace('/', '_')}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=device_name,
            manufacturer="Huerizon",
            model="Sky Sync",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to the MQTT topic when entity is added."""

        @callback
        def _message_received(msg: mqtt.ReceiveMessage) -> None:
            if msg.topic == self._topic and msg.payload:
                self._image = msg.payload
                self.async_write_ha_state()

        if "mqtt" not in self.hass.data:
            return

        self._unsub = await mqtt.async_subscribe(
            self.hass, self._topic, _message_received, qos=0
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from MQTT when entity is removed."""
        if self._unsub:
            self._unsub()
            self._unsub = None

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return the most recently received image bytes."""
        return self._image
