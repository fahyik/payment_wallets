import pytest

from rest_framework import status

from .conftest import COMPANY_ID, USER_ID
from ...models import Entity, Transfer


@pytest.mark.django_db
class TestCards():

    def test_get_card_list(self, api_client, create_card, create_wallet):
        """
        We mock a wallet and a card,
        Expects a response with a list of ONE card
        """

        wallet = create_wallet()
        card = create_card(wallet)  # noqa

        response = api_client.get(
            '/v1/cards/',
            HTTP_USER_ID=USER_ID,
            HTTP_COMPANY_ID=COMPANY_ID
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1

    def test_get_card_specific(self, api_client, create_card, create_wallet):
        """
        We mock a wallet and a card,
        Expects a response with specific card when retrieving card with card_id
        """

        wallet = create_wallet()
        card = create_card(wallet)

        response = api_client.get(
            '/v1/cards/{}/'.format(card.id),
            HTTP_USER_ID=USER_ID,
            HTTP_COMPANY_ID=COMPANY_ID
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['id'] == str(card.id)

    def test_create_card(self, api_client, create_card, create_wallet):
        """
        We mock a wallet and create card
        Expects
            - a card response
            - card with same currency as wallet
            - card with user_id
        """

        wallet = create_wallet()

        response = api_client.post(
            '/v1/cards/',
            data={
                "wallet_id": str(wallet.id),
                "user_id": USER_ID
            },
            format='json',
            HTTP_USER_ID=USER_ID,
            HTTP_COMPANY_ID=COMPANY_ID
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['user_id'] == str(USER_ID)
        assert response.json()['currency'] == wallet.currency

    def test_block_card(self, api_client, create_card, create_wallet):
        """
        We mock a wallet and a valid card with fake balance of 10,
        Expects
            - a response with is_blocked = True
            - wallet to have balance of 10
            - card to have balance of 0
            - transfer object to have the appropriate fields set
        """

        wallet = create_wallet()
        card = create_card(wallet, current_balance=10)

        response = api_client.put(
            '/v1/cards/{}/block/'.format(card.id),
            HTTP_USER_ID=USER_ID,
            HTTP_COMPANY_ID=COMPANY_ID
        )

        wallet.refresh_from_db()
        card.refresh_from_db()

        assert response.status_code == status.HTTP_200_OK
        assert wallet.current_balance == 10.0
        assert card.current_balance == 0.0
        assert card.is_blocked

        transfer = Transfer.objects.first()
        assert transfer.origin_amount == 10
        assert transfer.target_amount == 10
        assert transfer.origin_entity_id == card.id
        assert transfer.target_entity_id == wallet.id
        assert transfer.origin_entity_type == Entity.CARD
        assert transfer.target_entity_type == Entity.WALLET
        assert str(transfer.executed_by) == USER_ID

    def test_unblock_card(self, api_client, create_card, create_wallet):
        """
        We mock a wallet and a blocked card,
        Expects
            - a response with is_blocked = False
        """

        wallet = create_wallet()
        card = create_card(wallet, is_blocked=True)

        response = api_client.put(
            '/v1/cards/{}/unblock/'.format(card.id),
            HTTP_USER_ID=USER_ID,
            HTTP_COMPANY_ID=COMPANY_ID
        )

        card.refresh_from_db()

        assert response.status_code == status.HTTP_200_OK
        assert not card.is_blocked

    def test_load_card_insufficient_funds(self, api_client, create_card, create_wallet):
        """
        We mock a wallet with zero balance and a card,
        Try to load the card with money
        Expects
            - a 400
            - insufficient balance message
        """

        wallet = create_wallet()
        card = create_card(wallet)

        response = api_client.post(
            '/v1/cards/load/'.format(card.id),
            data={
                "card_id": str(card.id),
                "amount": 10.0
            },
            format='json',
            HTTP_USER_ID=USER_ID,
            HTTP_COMPANY_ID=COMPANY_ID
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()['message'] == "Insufficient credit to execute transfer"

    def test_unload_card_insufficient_funds(self, api_client, create_card, create_wallet):
        """
        We mock a wallet with zero balance and a card with zero balance,
        Try to unload money from card to wallet
        Expects
            - a 400
            - insufficient balance message
        """

        wallet = create_wallet()
        card = create_card(wallet)

        response = api_client.post(
            '/v1/cards/load/'.format(card.id),
            data={
                "card_id": str(card.id),
                "amount": -10.0
            },
            format='json',
            HTTP_USER_ID=USER_ID,
            HTTP_COMPANY_ID=COMPANY_ID
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()['message'] == "Insufficient credit to execute transfer"

    def test_load_blocked_card(self, api_client, create_card, create_wallet):
        """
        We mock a wallet with zero balance and a blocked card,
        Try to load money to card
        Expects
            - a 400
            - card blocked message
        """

        wallet = create_wallet()
        card = create_card(wallet, is_blocked=True)

        response = api_client.post(
            '/v1/cards/load/'.format(card.id),
            data={
                "card_id": str(card.id),
                "amount": 10.0
            },
            format='json',
            HTTP_USER_ID=USER_ID,
            HTTP_COMPANY_ID=COMPANY_ID
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()['message'] == "Card has been blocked"

    def test_load_card_success(self, api_client, create_card, create_wallet):
        """
        We mock a wallet with 100 balance and a card with 0 balance,
        Try to load the card with money
        Expects
            - a 200
            - wallet to decrease by amount
            - card to increase by amount
            - transfer object to have the appropriate fields set

        """

        wallet = create_wallet(current_balance=100)
        card = create_card(wallet)

        amount = 25.5

        response = api_client.post(
            '/v1/cards/load/'.format(card.id),
            data={
                "card_id": str(card.id),
                "amount": amount
            },
            format='json',
            HTTP_USER_ID=USER_ID,
            HTTP_COMPANY_ID=COMPANY_ID
        )

        wallet.refresh_from_db()
        card.refresh_from_db()

        assert response.status_code == status.HTTP_200_OK
        assert wallet.current_balance == 100 - amount
        assert card.current_balance == amount

        transfer = Transfer.objects.first()
        assert transfer.origin_amount == amount
        assert transfer.target_amount == amount
        assert transfer.origin_entity_id == wallet.id
        assert transfer.target_entity_id == card.id
        assert transfer.origin_entity_type == Entity.WALLET
        assert transfer.target_entity_type == Entity.CARD
        assert str(transfer.executed_by) == USER_ID

    def test_unload_card_success(self, api_client, create_card, create_wallet):
        """
        We mock a wallet with 0 balance and a card with 100 balance,
        Try to unload the card to wallet
        Expects
            - a 200
            - wallet to increase by amount
            - card to decrease by amount
            - transfer object to have the appropriate fields set

        """

        wallet = create_wallet()
        card = create_card(wallet, current_balance=100)

        amount = 25.5

        response = api_client.post(
            '/v1/cards/load/'.format(card.id),
            data={
                "card_id": str(card.id),
                "amount": amount * -1  # unload by negative amount
            },
            format='json',
            HTTP_USER_ID=USER_ID,
            HTTP_COMPANY_ID=COMPANY_ID
        )

        wallet.refresh_from_db()
        card.refresh_from_db()

        assert response.status_code == status.HTTP_200_OK
        assert card.current_balance == 100 - amount
        assert wallet.current_balance == amount

        transfer = Transfer.objects.first()
        assert transfer.origin_amount == amount
        assert transfer.target_amount == amount
        assert transfer.origin_entity_id == card.id
        assert transfer.target_entity_id == wallet.id
        assert transfer.origin_entity_type == Entity.CARD
        assert transfer.target_entity_type == Entity.WALLET
        assert str(transfer.executed_by) == USER_ID
