import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN")
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"
PDF_STORAGE_PATH = os.getenv("PDF_STORAGE_PATH", "./pdfs")
EXTERNAL_WEBHOOK_URL = os.getenv("EXTERNAL_WEBHOOK_URL", "https://nnikochann.ru/webhook/numero_post_bot")