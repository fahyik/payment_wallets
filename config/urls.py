from django.urls import include, path


urlpatterns = [
    path(
        "v1/",
        include("spendesk.wallets.urls"),
    ),
]

handler404 = 'spendesk.exceptions.django_handler_404'
handler500 = 'spendesk.exceptions.django_handler_500'
