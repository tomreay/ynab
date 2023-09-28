import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.components.sensor.const import STATE_CLASS_TOTAL
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo

from custom_components.ynab.api.data_coordinator import YnabDataCoordinator
from custom_components.ynab.const import ICON, CONF_CURRENCY_KEY

_LOGGER = logging.getLogger(__name__)

class BalanceSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = STATE_CLASS_TOTAL
    _attr_has_entity_name = True
    _attr_icon = ICON

    def __init__(self, coordinator: YnabDataCoordinator, data_key: str, data_id: str, device_info: DeviceInfo, budget_name: str):
        super().__init__(coordinator)

        self._data_key = data_key
        self._data_id = data_id
        self._attr_extra_state_attributes = {}
        self._attr_unique_id = f"{budget_name}_{data_key}_{data_id}"
        self._attr_device_info = device_info
        self._attr_native_unit_of_measurement = self.coordinator.data[CONF_CURRENCY_KEY]
        self._handle_data(coordinator.data[data_key][data_id])

    @callback
    def _handle_coordinator_update(self) -> None:
        self._handle_data(self.coordinator.data[self._data_key][self._data_id])
        self.async_write_ha_state()

    def _handle_data(self, data) -> None:
        _LOGGER.debug("Received data for %s %s", self._data_id, data)
        self._attr_native_value = data["balance"]
        self._attr_name = data["name"]

        if "budgeted" in data:
            self._attr_extra_state_attributes["budgeted"] = data["budgeted"]