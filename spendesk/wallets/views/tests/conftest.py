import pytest
import mock
import uuid

from ...models import Currencies, Card, Entity, Transfer, Wallet


COMPANY_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())

MOCK_FIXER_RESPONSE = mock.Mock(
    ok=True,
    json=mock.Mock(return_value={
        "success": True,
        "timestamp": 1542551947,
        "base": "EUR",
        "date": "2018-11-18",
        "rates": {
            "USD": 2,
            "GBP": 0.5,
            "EUR": 1
        }
    })
)


@pytest.fixture
def create_card():

    def _create_card(
        wallet,
        is_blocked=False,
        user_id=USER_ID,
        current_balance=0
    ):
        return Card.objects.create(
            currency=wallet.currency,
            user_id=user_id,
            wallet=wallet,
            current_balance=current_balance,
            is_blocked=is_blocked
        )

    return _create_card


@pytest.fixture
def create_wallet():

    def _create_wallet(
        currency=Currencies.EUR.name,
        company_id=COMPANY_ID,
        current_balance=0
    ):
        return Wallet.objects.create(
            currency=currency,
            company_id=company_id,
            current_balance=current_balance
        )

    return _create_wallet


@pytest.fixture
def create_master_wallets():

    def _create_master_wallets():
        return Wallet.objects.bulk_create(
            [
                Wallet(
                    currency=c.name,
                    company_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                    is_master=True
                )
                for c in Currencies
            ]
        )

    return _create_master_wallets
