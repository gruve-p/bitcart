#pylint: disable=no-member
from . import models
from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
from bitcart.coins.btc import BTC

RPC_USER=settings.RPC_USER
RPC_PASS=settings.RPC_PASS

RPC_URL=settings.RPC_URL

btc=BTC(RPC_URL)

def provide_stats(request):
    if request.user.is_authenticated:
        products=models.Product.objects.filter(store__wallet__user=request.user)
        products=products.order_by("-date")
        products_count=len(products)
        stores_count=models.Store.objects.filter(wallet__user=request.user).count()
        wallets=models.Wallet.objects.filter(user=request.user)
        wallets_count=len(wallets)
        wallets_balance=0
        for i in wallets:
            if timezone.now() - i.updated_date  >= timezone.timedelta(hours=2):
                wallets_balance+=float(BTC(RPC_URL,xpub=i.xpub, rpc_user=RPC_USER, rpc_pass=RPC_PASS).balance()['confirmed'])
                i.updated_date=timezone.now()
                i.save()
            else:
                wallets_balance+=i.balance
        wallets_balance=format(wallets_balance,".08f").rstrip("0").rstrip(".")
        return {"products":products, "stores_count":stores_count, "wallets_count":wallets_count,
        "products_count":products_count, "wallets_balance":wallets_balance}
    else:
        return {}