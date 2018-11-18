import decimal
import pytest

from rest_framework import status

from .conftest import COMPANY_ID, USER_ID, MOCK_FIXER_RESPONSE
from ...models import Currencies, Entity, Transfer, Wallet


@pytest.mark.django_db
class TestCards():

    def test_get_wallets_list(self, api_client, create_wallet):
        """
        We mock a wallet
        Expects a response with a list of ONE wallet
        """

        wallet = create_wallet()  # noqa

        response = api_client.get(
            '/v1/wallets/',
            HTTP_USER_ID=USER_ID,
            HTTP_COMPANY_ID=COMPANY_ID
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1

    def test_get_wallet_specific(self, api_client, create_wallet):
        """
        We mock a wallet,
        Expects a response with specific wallet when retrieving wallet with wallet_id
        """

        wallet = create_wallet()

        response = api_client.get(
            '/v1/wallets/{}/'.format(wallet.id),
            HTTP_USER_ID=USER_ID,
            HTTP_COMPANY_ID=COMPANY_ID
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['id'] == str(wallet.id)

    def test_create_wallet(self, api_client):
        """
        We create wallet
        Expects
            - a wallet response
            - wallet with specified currency
            - wallet with company_id
        """

        currency = Currencies.EUR.name

        response = api_client.post(
            '/v1/wallets/',
            data={
                "company_id": COMPANY_ID,
                "currency": currency
            },
            format='json',
            HTTP_USER_ID=USER_ID,
            HTTP_COMPANY_ID=COMPANY_ID
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['company_id'] == COMPANY_ID
        assert response.json()['currency'] == currency

    def test_wallet_transfer_same_currency(
        self,
        api_client,
        monkeypatch,
        create_wallet,
        create_master_wallets
    ):

        """
        We create 2 wallets with same currency
        one with 0 balance one with 100 balance
        Move amount from one to two
        Expects
            - wallet1 to decrease by amount
            - wallet2 to increase by amount
            - no conversion fee
        """

        monkeypatch.setattr(
            'requests.get',
            lambda *args, **kwargs: MOCK_FIXER_RESPONSE
        )

        target_wallet = create_wallet(currency=Currencies.EUR.name, current_balance=0)
        origin_wallet = create_wallet(currency=Currencies.EUR.name, current_balance=100)
        master_wallets = create_master_wallets()

        # TODO: further investigate python decimal
        amount = decimal.Decimal('25.2')

        response = api_client.post(
            '/v1/wallets/transfer/',
            data={
                "origin_wallet_id": str(origin_wallet.id),
                "target_wallet_id": str(target_wallet.id),
                "amount": amount
            },
            format='json',
            HTTP_USER_ID=USER_ID,
            HTTP_COMPANY_ID=COMPANY_ID
        )

        assert response.status_code == status.HTTP_200_OK

        target_wallet.refresh_from_db()
        origin_wallet.refresh_from_db()

        assert target_wallet.current_balance == amount
        assert origin_wallet.current_balance == 100 - amount

        transfer = Transfer.objects.first()
        assert transfer.origin_amount == amount
        assert transfer.target_amount == amount
        assert transfer.origin_entity_id == origin_wallet.id
        assert transfer.target_entity_id == target_wallet.id
        assert transfer.origin_entity_type == Entity.WALLET
        assert transfer.target_entity_type == Entity.WALLET
        assert str(transfer.executed_by) == USER_ID
        assert transfer.conversion_fee == 0


    def test_wallet_transfer_diff_currency(
        self,
        api_client,
        monkeypatch,
        create_wallet,
        create_master_wallets
    ):

        """
        We create 2 wallets with different currencies
        one with 0 balance one with 100 balance
        Move amount from one to two

        Fixed the fx rate to:
        EUR 1 = USD 2
        EUR 1 = GBP 0.5

        Expects
            - wallet1 to decrease by amount
            - wallet2 to increase by amount
            - correct conversion fee
            - master_wallet increase by conversion fee
        """

        monkeypatch.setattr(
            'requests.get',
            lambda *args, **kwargs: MOCK_FIXER_RESPONSE
        )

        target_wallet = create_wallet(currency=Currencies.EUR.name, current_balance=0)
        origin_wallet = create_wallet(currency=Currencies.USD.name, current_balance=100)
        master_wallets = create_master_wallets()

        # TODO: further investigate python decimal
        amount = decimal.Decimal('10')

        response = api_client.post(
            '/v1/wallets/transfer/',
            data={
                "origin_wallet_id": str(origin_wallet.id),
                "target_wallet_id": str(target_wallet.id),
                "amount": amount
            },
            format='json',
            HTTP_USER_ID=USER_ID,
            HTTP_COMPANY_ID=COMPANY_ID
        )

        assert response.status_code == status.HTTP_200_OK

        transfer = Transfer.objects.first()
        assert transfer.origin_amount == amount
        assert (transfer.target_amount + transfer.conversion_fee) / transfer.fx_rate == amount
        assert transfer.origin_entity_id == origin_wallet.id
        assert transfer.target_entity_id == target_wallet.id
        assert transfer.origin_entity_type == Entity.WALLET
        assert transfer.target_entity_type == Entity.WALLET
        assert str(transfer.executed_by) == USER_ID

        target_wallet.refresh_from_db()
        origin_wallet.refresh_from_db()

        assert target_wallet.current_balance == transfer.target_amount
        assert origin_wallet.current_balance == 100 - amount

        master_wallet = Wallet.objects.get(is_master=True, currency=transfer.target_currency)
        assert master_wallet.current_balance == transfer.conversion_fee
