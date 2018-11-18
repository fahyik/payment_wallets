from django.db import transaction

from rest_framework import exceptions, serializers
from rest_framework.generics import (
    GenericAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
)
from rest_framework.response import Response

from .transfers import TransferBase
from ..models import Card, Wallet
from ..permissions import SpendeskIsOwnCompanyPermission
from ...exceptions import BadRequestError, NotFoundError


class CardSerializer(serializers.ModelSerializer):
    wallet_id = serializers.PrimaryKeyRelatedField(
        source='wallet',
        queryset=Wallet.objects.all()
    )

    def create(self, validated_data):
        """
        create method creates database instance of object
        see: http://www.cdrf.co/3.7/rest_framework.serializers/ModelSerializer.html#create

        in the case for Card, the currency of the card is fixed to
        the currency of the wallet
        """

        instance = super().create(validated_data)

        instance.currency = instance.wallet.currency
        instance.save()

        return instance

    def validate_wallet_id(self, value):
        """
        can only create card for own company's wallets
        ref: https://www.django-rest-framework.org/api-guide/serializers/#validation
        """

        if self.context.get('request').auth['company_id'] != value.company_id:
            raise exceptions.PermissionDenied()

        return value

    class Meta:
        model = Card
        exclude = ('wallet', )
        # fields = '__all__'
        read_only_fields = (
            'id',
            'ccv',
            'card_number',
            'current_balance',
            'expires_on',
            'is_blocked',
            'wallet',
            'currency'
        )


class CardListCreateView(ListCreateAPIView):

    queryset = Card.objects.all()
    serializer_class = CardSerializer

    def get_queryset(self):
        """
        Can only LIST Cards from own company's wallets

        TODO: add option to filter card by user_id
        """
        queryset = super().get_queryset()
        return queryset.filter(wallet__company_id=self.request.auth['company_id'])

    # TODO: add pagination


class CardRetrieveView(RetrieveAPIView):

    queryset = Card.objects.all()
    serializer_class = CardSerializer
    lookup_url_kwarg = 'card_id'

    permission_classes = (
        SpendeskIsOwnCompanyPermission,
    )


class CardBlockView(GenericAPIView, TransferBase):

    queryset = Card.objects.select_for_update()  # locks the card and related wallet object
    serializer_class = CardSerializer
    lookup_url_kwarg = 'card_id'

    permission_classes = (
        SpendeskIsOwnCompanyPermission,
    )

    def put(self, request, *args, **kwargs):

        card = self.block(*args, **kwargs)
        serializer = self.get_serializer(card)
        return Response(serializer.data)

    def block(self, *args, **kwargs):
        """
        block requires two action:
        1.  to set the card to blocked
        2.  to unload all money back to wallet
        """

        with transaction.atomic():

            card = self.get_object()
            wallet = card.wallet

            if not card.is_blocked:
                self.block_card(card)

                if card.current_balance > 0:
                    self.transfer_back_to_wallet(card, wallet)

        return card

    def block_card(self, card):
        card.is_blocked = True
        card.save()

    def transfer_back_to_wallet(self, card, wallet):

        self.make_simple_transfer(
            amount=card.current_balance,
            origin=card,
            target=wallet
        )


class CardUnblockView(GenericAPIView):

    queryset = Card.objects.select_for_update()  # locks the card and related wallet object
    serializer_class = CardSerializer
    lookup_url_kwarg = 'card_id'

    permission_classes = (
        SpendeskIsOwnCompanyPermission,
    )

    def put(self, request, *args, **kwargs):

        return self.unblock(*args, **kwargs)

    def unblock(self, *args, **kwargs):

        card = self.get_object()
        card.is_blocked = False
        card.save()

        serializer = self.get_serializer(card)
        return Response(serializer.data)


class CardLoadView(GenericAPIView, TransferBase):

    class CardLoadSerializer(serializers.Serializer):
        card_id = serializers.UUIDField()
        amount = serializers.DecimalField(max_digits=15, decimal_places=2)

    serializer_class = CardLoadSerializer
    permission_classes = (
        SpendeskIsOwnCompanyPermission,
    )

    def post(self, request, *args, **kwargs):

        ser = self.CardLoadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        card = self.transfer(ser.validated_data, *args, **kwargs)
        return Response(CardSerializer(card).data)

    def transfer(self, data, *args, **kwargs):

        with transaction.atomic():

            card = self.get_card(data['card_id'])
            wallet = card.wallet

            if data['amount'] > 0:
                amount = data['amount']
                origin = wallet
                target = card

            elif data['amount'] < 0:
                amount = abs(data['amount'])
                origin = card
                target = wallet

            else:
                return card

            self.ensure_enough_balance(amount, origin)
            self.make_simple_transfer(amount, origin, target)

        return card

    def get_card(self, card_id):

        try:
            card = Card.objects.select_for_update().get(id=card_id)
        except Card.DoesNotExist:
            raise NotFoundError("Invalid card id - Card not found")

        self.check_object_permissions(self.request, card)

        if card.is_blocked:
            raise BadRequestError("Card has been blocked")

        return card
