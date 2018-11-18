from datetime import datetime, timedelta
from enum import Enum
from random import randint
import uuid

from django.conf import settings
from django.db import models

"""
Note:
1.  All amounts and balances are set to use DecimalField
    and are arbitrarily set to to a maximum of 15 digits (required)
    see: https://docs.djangoproject.com/en/2.0/ref/models/fields/#decimalfield

2.  Db indices are not set, may need to optimise later
"""


class Currencies(Enum):
    """
    TODO: Using simple enum here,
    may want to change to have a table to manage all supported currencies
    """

    EUR = 'Euros'
    USD = 'US Dollars'
    GBP = 'British Pound'


class Entity(models.Model):

    # TODO: using simple enum for entity types for the moment
    # may want to switch to a table managing these types later
    CARD = 'C'
    WALLET = 'W'
    EXTERNAL = 'E'  # for credit or debit transfers, i.e. loading money from bank

    ENTITY_TYPE = (
        (CARD, 'card'),
        (WALLET, 'wallet'),
        (EXTERNAL, 'external')
    )

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    currency = models.CharField(max_length=3, choices=[(cur.name, cur.value) for cur in Currencies])
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Wallet(Entity):

    company_id = models.UUIDField(db_index=True)
    is_master = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['currency', 'is_master']),
        ]


class Card(Entity):

    def random_ccv():
        return str(randint(0, 999)).zfill(3)

    def random_card_number():
        return str(randint(0, 9999999999999999)).zfill(16)

    def get_expiry_date():
        return (datetime.utcnow() + timedelta(days=30)).date()

    card_number = models.CharField(max_length=16, unique=True, default=random_card_number)  # stored as char in case of numbers with leading 0s
    ccv = models.CharField(max_length=3, default=random_ccv)
    is_blocked = models.BooleanField(default=False)  # since there is only one status for now, we will use a bool

    user_id = models.UUIDField(db_index=True)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='cards')

    expires_on = models.DateField(default=get_expiry_date)


class Transfer(models.Model):

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)

    CONVERSION_FEE = settings.SPENDESK_CONVERSION_FEE
    """
    For the amounts:
    converted_amount = (origin_amount * fx_rate)
    target_amount = (1 - CONVERSION_FEE) * converted_amount
    conversion_fee = CONVERSION_FEE * converted_amount
    """

    # TODO: add db constraint for origin_amount and target_amount --> positive values

    origin_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # always positive
    origin_currency = models.CharField(max_length=3, choices=[(cur.name, cur.value) for cur in Currencies])

    target_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # always positive
    target_currency = models.CharField(max_length=3, choices=[(cur.name, cur.value) for cur in Currencies])

    fx_rate = models.DecimalField(max_digits=15, decimal_places=6, default=1)  # arbitrarily set
    conversion_fee = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    origin_entity_id = models.UUIDField(db_index=True, blank=True, null=True)
    origin_entity_type = models.CharField(max_length=1, choices=Entity.ENTITY_TYPE)
    target_entity_id = models.UUIDField(db_index=True, blank=True, null=True)
    target_entity_type = models.CharField(max_length=1, choices=Entity.ENTITY_TYPE)

    created_at = models.DateTimeField(auto_now_add=True)
    executed_by = models.UUIDField(db_index=True, blank=True, null=True)
