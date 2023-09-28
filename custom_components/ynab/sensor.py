"""Sensor platform for ynab."""
import logging
from homeassistant.helpers.entity import DeviceInfo

from .const import (DOMAIN, CONF_ACCOUNTS_KEY, CONF_BUDGET_KEY,
                    CONF_CATEGORIES_KEY, CONF_BUDGET_NAME_KEY)
from .sensors.balance_sensor import BalanceSensor
from .sensors.budget_sensor import BudgetSensor
from .api.data_coordinator import YnabDataCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass, config_entry, async_add_entities
):
    """Set up sensor platform."""
    _LOGGER.debug("Setting up entities")

    coordinator = YnabDataCoordinator(hass, config_entry.data)
    await coordinator.async_config_entry_first_refresh()

    budget_id = config_entry.data[CONF_BUDGET_KEY]
    budget_name = config_entry.data[CONF_BUDGET_NAME_KEY]
    device_info = DeviceInfo(
        name=budget_name,
        manufacturer=DOMAIN,
        model="Budget",
        via_device=(DOMAIN, budget_id),
        identifiers={(DOMAIN, budget_id)}
    )

    sensors = [BudgetSensor(coordinator, budget_id, budget_name, device_info)]

    if CONF_CATEGORIES_KEY in config_entry.data:
        for category in config_entry.data[CONF_CATEGORIES_KEY]:
            sensors.append(BalanceSensor(coordinator, data_key=CONF_CATEGORIES_KEY, data_id=category, device_info=device_info, budget_name=budget_name))

    if CONF_ACCOUNTS_KEY in config_entry.data:
        for account in config_entry.data[CONF_ACCOUNTS_KEY]:
            sensors.append(BalanceSensor(coordinator, data_key=CONF_ACCOUNTS_KEY, data_id=account, device_info=device_info, budget_name=budget_name))

    async_add_entities(sensors, update_before_add=True)