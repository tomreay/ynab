import logging
from typing import Callable

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.components.sensor.const import STATE_CLASS_TOTAL
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo

from custom_components.ynab.api.data_coordinator import YnabDataCoordinator, DataCoordinatorModel
from custom_components.ynab.const import ICON

_LOGGER = logging.getLogger(__name__)

class BalanceSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = STATE_CLASS_TOTAL
    _attr_has_entity_name = True
    _attr_icon = ICON

    def __init__(self, coordinator: YnabDataCoordinator, handle_data: Callable, data_id: str, device_info: DeviceInfo, budget_name: str):
        super().__init__(coordinator)

        self._data_id = data_id
        self._attr_extra_state_attributes = {}
        self._attr_unique_id = f"{budget_name}_{data_id}"
        self._attr_device_info = device_info
        self._attr_native_unit_of_measurement = self.coordinator.data.currency_iso
        self._handle_data = handle_data
        self._handle_data(coordinator.data)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._handle_data(self.coordinator.data)
        self.async_write_ha_state()

class AccountSensor(BalanceSensor):

    def __init__(self, coordinator: YnabDataCoordinator, account_id: str, device_info: DeviceInfo, budget_name: str):
        super(). __init__(coordinator, self.handle_data, account_id, device_info, budget_name)

    def handle_data(self, data: DataCoordinatorModel):
        category_data = data.accounts[self._data_id]

        _LOGGER.debug("Received data for %s %s", self._data_id, category_data)
        self._attr_native_value = category_data.balance
        self._attr_name = category_data.name

class CategorySensor(BalanceSensor):

    def __init__(self, coordinator: YnabDataCoordinator, category_id: str, device_info: DeviceInfo, budget_name: str):
        super(). __init__(coordinator, self.handle_data, category_id, device_info, budget_name)

    def handle_data(self, data: DataCoordinatorModel):
        category_data = data.categories[self._data_id]

        _LOGGER.debug("Received data for %s %s", self._data_id, category_data)
        self._attr_native_value = category_data.balance
        self._attr_extra_state_attributes["budgeted"] = category_data.budgeted
        self._attr_name = category_data.name