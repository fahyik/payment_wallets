import uuid

from django.core.management.base import BaseCommand


def seed():
    from spendesk.wallets.models import Currencies, Wallet

    for currency in Currencies:
        if not Wallet.objects.filter(is_master=True, currency=currency.name).exists():
            Wallet.objects.create(
                is_master=True,
                currency=currency.name,
                company_id=uuid.UUID("00000000-0000-0000-0000-000000000000")
            )


class Command(BaseCommand):
    help = 'Add master wallets if they dont yet exist'

    def handle(self, *args, **kwargs):

        seed()
        self.stdout.write("Master wallets initialised")
