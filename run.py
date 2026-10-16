import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

from database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def run_server():
    try:
        import uvicorn
        from server import app
        port = int(os.getenv("PORT", 8000))
        host = os.getenv("HOST", "0.0.0.0")
        config = uvicorn.Config(app=app, host=host, port=port, log_level="warning")
        server = uvicorn.Server(config)
        logging.info(f"🌐 جاري محاولة تشغيل خادم الويب على {host}:{port}...")
        await server.serve()
    except OSError as e:
        logging.warning(f"⚠️ تنبيه: تم تخطي تشغيل خادم الويب المحلي بسبب قيود المنصة ({e}). سيعمل بوت التليجرام بكامل طاقته.")
    except Exception as e:
        logging.warning(f"⚠️ تنبيه خادم الويب: {e}. سيعمل بوت التليجرام بكامل طاقته.")

async def run_bot():
    bot_token = os.getenv("BOT_TOKEN", "8881972676:AAFbhVZWztH9JKit5EHXbPN2sSeJsGiJYlQ")
    if not bot_token:
        logging.error("❌ لم يتم العثور على BOT_TOKEN!")
        return
        
    try:
        from bot import start_bot
        await start_bot()
    except Exception as e:
        logging.error(f"❌ خطأ أثناء تشغيل البوت: {e}")

async def main():
    init_db()
    logging.info("🚀 تشغيل النظام...")
    # تشغيل البوت والسيرفر مع حماية البوت من التوقف إذا فشل المنفذ
    await asyncio.gather(
        run_bot(),
        run_server(),
        return_exceptions=True
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Shutting down...")
