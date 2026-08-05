# payment_webhook.py
import logging
import json
import hmac
import hashlib
import os
from aiohttp import web
from datetime import datetime, timedelta
from typing import Dict, Any

try:
    from database_sqlite import Database
except ImportError:
    from database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

YUKASSA_SECRET_KEY = os.getenv("YUKASSA_SECRET_KEY", "your_yukassa_secret_key")
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

db = Database()

async def verify_yukassa_payment(request):
    if TEST_MODE:
        return True
    try:
        signature = request.headers.get('X-Signature')
        if not signature:
            logger.warning("Missing X-Signature")
            return False
        body = await request.read()
        calc_signature = hmac.new(
            YUKASSA_SECRET_KEY.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, calc_signature):
            logger.warning("Invalid signature")
            return False
        return True
    except Exception as e:
        logger.error(f"Verification error: {e}")
        return False

async def handle_successful_payment(payment_data: Dict[str, Any]) -> bool:
    try:
        await db.init()
        if payment_data.get('status') != 'succeeded':
            logger.info(f"Payment not succeeded: {payment_data.get('status')}")
            return False
        metadata = payment_data.get('metadata', {})
        order_id = metadata.get('order_id')
        if not order_id:
            logger.error("No order_id in metadata")
            return False
        order_id = int(order_id)
        order = await db.get_order(order_id)
        if not order:
            logger.error(f"Order {order_id} not found")
            return False
        await db.update_order_status(order_id, 'paid')
        # Здесь можно добавить логику генерации отчёта (если нужно)
        # Например, вызов bot.send_document через другой канал
        logger.info(f"Order {order_id} marked as paid")
        return True
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        return False

async def handle_payment_webhook(request: web.Request) -> web.Response:
    if not await verify_yukassa_payment(request):
        return web.Response(status=401, text="Unauthorized")
    try:
        data = await request.json()
        logger.info(f"Received webhook: {data}")
        if TEST_MODE:
            return web.Response(status=200, text="Test mode")
        event = data.get('event')
        if event == 'payment.succeeded':
            if await handle_successful_payment(data.get('object', {})):
                return web.Response(status=200, text="OK")
            else:
                return web.Response(status=500, text="Error processing")
        return web.Response(status=200, text="Received")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(status=500, text=f"Error: {str(e)}")

async def setup_payment_webhook_server(host='0.0.0.0', port=8080):
    await db.init()
    app = web.Application()
    app.router.add_post('/payment', handle_payment_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    logger.info(f"Starting webhook server on {host}:{port}")
    await site.start()
    return runner