from ..fixer_io import get_rate
from ..models import Card, Entity, Transfer, Wallet
from ...exceptions import BadRequestError


class TransferBase():
    """
    IMPORTANT: origin and target objects have to be locked in order
    to prevent concurrent updates
    """

    def create_transfer(
        self,
        amount,
        origin,
        target,
    ):

        transfer = Transfer.objects.create(
            executed_by=self.request.auth['user_id'],
            origin_amount=amount,
            origin_currency=origin.currency,
            target_amount=amount,
            target_currency=target.currency,
            origin_entity_id=origin.id,
            origin_entity_type=(Entity.CARD if isinstance(origin, Card) else Entity.WALLET),
            target_entity_id=target.id,
            target_entity_type=(Entity.CARD if isinstance(target, Card) else Entity.WALLET)
        )

        return transfer

    def ensure_enough_balance(self, amount, origin):
        if origin.current_balance < amount:
            raise BadRequestError("Insufficient credit to execute transfer")

    def make_simple_transfer(self, amount, origin, target):
        """
        simple transfer between same currency
        """

        transfer = self.create_transfer(
            amount=amount,
            origin=origin,
            target=target
        )

        self.update_origin_balance(transfer, origin)
        self.update_target_balance(transfer, target)

    def make_converted_transfer(self, amount, origin, target):
        """
        converted transfer between currencies

        conversion logic:
            converted_amount = (origin_amount * fx_rate)
            target_amount = (1 - CONVERSION_FEE) * converted_amount
            conversion_fee = CONVERSION_FEE * converted_amount
        """

        transfer = self.create_transfer(
            amount=amount,
            origin=origin,
            target=target
        )

        if transfer.origin_currency != transfer.target_currency:
            # only do conversion if currency is different
            transfer = self.update_transfer_with_conversion(transfer)

        self.update_origin_balance(transfer, origin)
        self.update_target_balance(transfer, target)
        self.update_master_wallet(transfer)

    def update_transfer_with_conversion(self, transfer):

        transfer.fx_rate = get_rate(transfer.origin_currency, transfer.target_currency)

        converted_amount = transfer.origin_amount * transfer.fx_rate
        transfer.target_amount = (1 - Transfer.CONVERSION_FEE) * converted_amount
        transfer.conversion_fee = Transfer.CONVERSION_FEE * converted_amount

        transfer.save()

        return transfer

    def update_origin_balance(self, transfer, origin):

        origin.current_balance -= transfer.origin_amount
        origin.save()

        return origin

    def update_target_balance(self, transfer, target):

        target.current_balance += transfer.target_amount
        target.save()

        return target

    def update_master_wallet(self, transfer):

        # again obtain lock on object with select for update
        master = Wallet.objects.select_for_update().get(is_master=True, currency=transfer.target_currency)

        master.current_balance += transfer.conversion_fee

        master.save()
