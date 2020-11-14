import asyncio
import signal
import sys
from multiprocessing import Process

from api import invoices, settings
from api.ext import tor as tor_ext
from api.ext import update as update_ext
from api.logserver import main as start_logserver
from api.utils import run_repeated

process = Process(target=start_logserver)
process.start()


async def main():
    await settings.init_db()
    await asyncio.sleep(1)
    settings.log_startup_info()
    await tor_ext.refresh(log=False)  # to pre-load data for initial requests
    await update_ext.refresh()
    asyncio.ensure_future(run_repeated(tor_ext.refresh, 60 * 15, 10))
    asyncio.ensure_future(run_repeated(update_ext.refresh, 60 * 60 * 24))
    settings.manager.add_event_handler("new_payment", invoices.new_payment_handler)
    await settings.manager.start_websocket(reconnect_callback=invoices.check_pending, force_connect=True)


def handler(signum, frame):
    process.terminate()
    sys.exit()


signal.signal(signal.SIGINT, handler)
asyncio.get_event_loop().run_until_complete(main())