import logging
import aiohttp
import json

from datetime import date, timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import CONF_API_KEY
from ynab_sdk import YNAB

from custom_components.ynab.const import (
    CONF_CURRENCY_KEY,
    CONF_BUDGET_KEY,
    CONF_CATEGORIES_KEY,
    CONF_CATEGORIES_ALL_KEY,
    CONF_ACCOUNTS_KEY,
    CONF_ACCOUNTS_ALL_KEY,
    DEFAULT_API_ENDPOINT,
    DOMAIN
)

_LOGGER = logging.getLogger(__name__)

class YnabDataCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, config):
        super().__init__(hass, _LOGGER, name="YNAB", update_interval=timedelta(seconds=300))
        self.ynab = YNAB(config[CONF_API_KEY])
        self.api_key = config[CONF_API_KEY]
        self.budget = config[CONF_BUDGET_KEY]
        self.categories = config[CONF_CATEGORIES_KEY]
        self.categories_all = config[CONF_CATEGORIES_ALL_KEY]
        self.accounts = config[CONF_ACCOUNTS_KEY]
        self.accounts_all = config[CONF_ACCOUNTS_ALL_KEY]


    async def _async_update_data(self):
        """Update data."""
        data = {}

        # setup YNAB API
        await self.request_import()

        raw_budget = await self.hass.async_add_executor_job(
            self.ynab.budgets.get_budget, self.budget
        )

        get_data = raw_budget.data.budget
        _LOGGER.debug("Retrieving data from budget id: %s", get_data.id)

        # get to be budgeted data
        data["to_be_budgeted"] = (
            get_data.months[0].to_be_budgeted / 1000
        )
        _LOGGER.debug(
            "Received data for: to be budgeted: %s",
            (get_data.months[0].to_be_budgeted / 1000),
        )

        # get unapproved transactions
        unapproved_transactions = len(
            [
                transaction.amount
                for transaction in get_data.transactions
                if transaction.approved is not True
            ]
        )
        data["need_approval"] = unapproved_transactions
        _LOGGER.debug(
            "Received data for: unapproved transactions: %s",
            unapproved_transactions,
        )

        # get number of uncleared transactions
        uncleared_transactions = len(
            [
                transaction.amount
                for transaction in get_data.transactions
                if transaction.cleared == "uncleared"
            ]
        )
        data["uncleared_transactions"] = uncleared_transactions
        _LOGGER.debug(
            "Received data for: uncleared transactions: %s", uncleared_transactions
        )

        data[CONF_CURRENCY_KEY] = get_data.currency_format.iso_code

        total_balance = 0
        # get account data
        for account in get_data.accounts:
            if account.on_budget:
                total_balance += account.balance

        # get to be budgeted data
        data["total_balance"] = total_balance / 1000
        _LOGGER.debug(
            "Received data for: total balance: %s",
            (data["total_balance"]),
        )

        # get accounts
        data[CONF_ACCOUNTS_KEY] = {}
        for account in get_data.accounts:
            if not self.accounts_all and account.id not in self.accounts:
                continue

            data[CONF_ACCOUNTS_KEY].update([(account.id, {"name": account.name, "balance": account.balance / 1000})])
            _LOGGER.debug(
                "Received data for account: %s",
                [account.name, account.balance / 1000],
            )

        # get current month data
        for month in get_data.months:
            if month.month != date.today().strftime("%Y-%m-01"):
                continue

            # budgeted
            data["budgeted_this_month"] = month.budgeted / 1000
            _LOGGER.debug(
                "Received data for: budgeted this month: %s",
                data["budgeted_this_month"],
            )

            # activity
            data["activity_this_month"] = month.activity / 1000
            _LOGGER.debug(
                "Received data for: activity this month: %s",
                data["activity_this_month"],
            )

            # get age of money
            data["age_of_money"] = month.age_of_money
            _LOGGER.debug(
                "Received data for: age of money: %s",
                data["age_of_money"],
            )

            # get number of overspend categories
            overspent_categories = len(
                [
                    category.balance
                    for category in month.categories
                    if category.balance < 0
                ]
            )
            data["overspent_categories"] = overspent_categories
            _LOGGER.debug(
                "Received data for: overspent categories: %s",
                overspent_categories,
            )

            # get remaining category balances
            data[CONF_CATEGORIES_KEY] = {}
            for category in month.categories:
                if not self.categories_all and category.id not in self.categories:
                    continue

                data[CONF_CATEGORIES_KEY].update(
                    [(category.id, {"balance": category.balance / 1000, "budgeted": category.budgeted / 1000, "name": category.name})]
                )
                _LOGGER.debug(
                    "Received data for categories: %s",
                    [category.name, category.balance / 1000, category.budgeted / 1000],
                )

            return data

    async def request_import(self):
        """Force transaction import."""

        import_endpoint = (
            f"{DEFAULT_API_ENDPOINT}/budgets/{self.budget}/transactions/import"
        )
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(url=import_endpoint) as response:
                    if response.status in [200, 201]:
                        response_data = json.loads(await response.text())

                        _LOGGER.debug(
                            "Imported transactions: %s",
                            len(response_data["data"]["transaction_ids"]),
                        )
                        _LOGGER.debug("API Stats: %s", response.headers["X-Rate-Limit"])

                        if len(response_data["data"]["transaction_ids"]) > 0:
                            _event_topic = DOMAIN + "_event"
                            _event_data = {
                                "transactions_imported": len(
                                    response_data["data"]["transaction_ids"]
                                )
                            }
                            self.hass.bus.async_fire(_event_topic, _event_data)

        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.debug("Error encounted during forced import - %s", error)