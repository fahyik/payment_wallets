# Wallet Management System


## Quickstart

This project is build on Django / Django Rest Framework

Some reference links if you are new to django / django rest framework:
- https://www.django-rest-framework.org/
- http://www.cdrf.co/

### with docker-compose (recommended)
```bash
> docker-compose -f local.yml build
> docker-compose -f local.yml up
```

### with command line
if you want to start the local server from the command line,
you will have set up postgres on your machine, with the db settings as per
`./.envs/.local/.postgres`
```bash
> pip install -r requirements/local.txt
> ./manage.py migrate
> ./manage.py seed_master_wallets
> ./manage.py runserver 0.0.0.0:5000
```

You should then be able to access the API on http://0.0.0.0:5000/v1/wallets/docs/


## Testing

### with docker-compose (recommended)
```bash
> docker-compose -f local.yml run django pytest -v --cov
```

# Notes on API

## List of all API endpoints:
This should also be available on `/v1/docs/`

A Postman collection is also included: `spendesk.postman_colletion.json`
### CARDS
```
GET   /v1/cards/                      # list all cards
POST  /v1/cards/                      # create card
GET   /v1/cards/{card_id}/            # get specific card 
POST  /v1/cards/load/                 # load/unload card
PUT   /v1/cards/{card_id}/block/      # block card
PUT   /v1/cards/{card_id}/unblock/    # unblock card
```

### WALLETS
```
GET   /v1/wallets/                    # list all wallets
POST  /v1/wallets/                    # create wallet
GET   /v1/wallets/{wallet_id}/        # get specific wallet
POST  /v1/wallets/transfer/           # make transfer between wallets

## DEBUG END POINT to simulate credit of wallets
PUT /v1/wallets/{wallet_id}/credit/   # add 100 bucks to the balance
```

Each request needs to be accompanied by setting the header properties User-Id and Company-Id. UUID type is expected. If the headers are missing, a 403-Forbidden will be returned.

API permissions are then assessed according to these values set.

For examples, a call to GET `/v1/cards/` will only return cards that are linked to the company-id
provided.
A call to retrieve a specific wallet or card that is not linked to the company-id provided will also return a 403-Forbidden.


#### Special case:
The master wallets are initialised with the `company_id = 00000000-0000-0000-0000-000000000000`
To list all master wallets make a call to GET `v1/cards/` with header property `Company-Id = 00000000-0000-0000-0000-000000000000`.

