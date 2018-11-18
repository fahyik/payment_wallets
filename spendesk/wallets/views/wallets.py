from django.db import transaction

from rest_framework import exceptions, serializers
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveAPIView,
    UpdateAPIView,
    GenericAPIView,
)
from rest_framework.response import Response

from .transfers import TransferBase
from ..models import Wallet
from ..permissions import SpendeskIsOwnCompanyPermission
from ...exceptions import NotFoundError


class WalletSerializer(serializers.ModelSerializer):

    def validate_company_id(self, value):
        """
        can only create wallet for own company
        ref: https://www.django-rest-framework.org/api-guide/serializers/#validation
        """

        if self.context.get('request').auth['company_id'] != value:
            raise exceptions.PermissionDenied()

        return value

    class Meta:
        model = Wallet
        exclude = ('is_master', )
        read_only_fields = (
            'id', 'is_master', 'current_balance'
        )


class WalletListCreateView(ListCreateAPIView):

    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer

    def get_queryset(self):
        """
        Can only LIST wallets from own company
        """
        queryset = super().get_queryset()
        return queryset.filter(company_id=self.request.auth['company_id'])

    # TODO: add pagination


class WalletRetrieveView(RetrieveAPIView):

    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    lookup_url_kwarg = 'wallet_id'

    permission_classes = (
        SpendeskIsOwnCompanyPermission,
    )


class WalletTransferView(GenericAPIView, TransferBase):

    class WalletTransferSerializer(serializers.Serializer):
        origin_wallet_id = serializers.UUIDField()
        target_wallet_id = serializers.UUIDField()
        amount = serializers.DecimalField(max_digits=15, decimal_places=2)

        def validate_amount(self, value):

            if value <= 0:
                raise serializers.ValidationError("Has to be greater than 0")

            return value

        def validate(self, data):
            """
            Check that wallets are different
            """
            if data['origin_wallet_id'] == data['target_wallet_id']:
                raise serializers.ValidationError("Origin and target wallets cannot be the same")

            return data

    permission_classes = (
        SpendeskIsOwnCompanyPermission,
    )
    serializer_class = WalletTransferSerializer

    def post(self, request, *args, **kwargs):

        ser = self.WalletTransferSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        self.transfer(ser.validated_data, *args, **kwargs)
        return Response({"transfer": "ok"})

    def transfer(self, data, *args, **kwargs):

        with transaction.atomic():
            origin = self.get_wallet(data['origin_wallet_id'])
            target = self.get_wallet(data['target_wallet_id'])

            self.ensure_enough_balance(data['amount'], origin)
            self.make_converted_transfer(data['amount'], origin, target)

        return

    def get_wallet(self, wallet_id):

        try:
            wallet = Wallet.objects.select_for_update().get(id=wallet_id)
        except Wallet.DoesNotExist:
            raise NotFoundError("Invalid wallet id provided")

        self.check_object_permissions(self.request, wallet)

        return wallet


class WalletDebugView(UpdateAPIView):  # pragma: no cover

    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    lookup_url_kwarg = 'wallet_id'

    permission_classes = (
        SpendeskIsOwnCompanyPermission,
    )

    def update(self, request, *args, **kwargs):

        wallet = self.get_object()
        wallet.current_balance += 100
        wallet.save()

        serializer = self.get_serializer(wallet)
        return Response(serializer.data)
