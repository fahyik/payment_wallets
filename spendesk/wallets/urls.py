from django.conf import settings
from django.urls import path

from rest_framework.documentation import include_docs_urls

from .views import (
    CardListCreateView, CardRetrieveView, CardBlockView, CardUnblockView, CardLoadView,
    WalletListCreateView, WalletRetrieveView, WalletTransferView, WalletDebugView
)

urlpatterns = [
    path('cards/', CardListCreateView.as_view()),
    path('cards/load/', CardLoadView.as_view()),
    path('cards/<uuid:card_id>/', CardRetrieveView.as_view()),
    path('cards/<uuid:card_id>/block/', CardBlockView.as_view()),
    path('cards/<uuid:card_id>/unblock/', CardUnblockView.as_view()),
    path('wallets/', WalletListCreateView.as_view()),
    path('wallets/<uuid:wallet_id>/', WalletRetrieveView.as_view()),
    path('wallets/transfer/', WalletTransferView.as_view()),
    path(
        'docs/',
        include_docs_urls(
            title='Wallet Management',
            authentication_classes=[],
            permission_classes=[]
        )
    )
]


if settings.DEBUG:
    urlpatterns += [
        path('wallets/<uuid:wallet_id>/credit/', WalletDebugView.as_view()),
    ]