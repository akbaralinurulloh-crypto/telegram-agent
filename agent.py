import os
import sys
import asyncio
import logging
from pathlib import Path

# Windows UTF-8 qo'llab-quvvatlash
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

import config
import database
from ai_evaluator import evaluate_media

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("TelegramAIAgent")


def is_video_media(media) -> bool:
    """Media video ekanligini tekshiradi."""
    if isinstance(media, MessageMediaDocument):
        doc = media.document
        if doc and doc.mime_type and doc.mime_type.startswith("video/"):
            return True
    return False


def is_photo_media(media) -> bool:
    """Media rasm ekanligini tekshiradi."""
    if isinstance(media, MessageMediaPhoto):
        return True
    if isinstance(media, MessageMediaDocument):
        doc = media.document
        if doc and doc.mime_type and doc.mime_type.startswith("image/"):
            return True
    return False


async def process_media_message(client: TelegramClient, message, source_channel_name: str):
    """Bitta xabarni to'liq qayta ishlash sikli."""
    source_msg_id = message.id
    
    # 1. Baza orqali avval ko'rilganmi tekshirish
    if await database.is_message_processed(source_channel_name, source_msg_id):
        logger.info(f"⏭ [{source_channel_name}:{source_msg_id}] Ushbu xabar avval qayta ishlangan. Tashlab ketilmoqda.")
        return

    # 2. Media turini aniqlash
    media_type = None
    if is_photo_media(message.media):
        media_type = "photo"
    elif is_video_media(message.media):
        media_type = "video"
    else:
        logger.info(f"⏭ [{source_channel_name}:{source_msg_id}] Xabarda rasm yoki video yo'q. Tashlab ketilmoqda.")
        await database.save_processed_message(
            source_channel=source_channel_name,
            source_message_id=source_msg_id,
            media_type="text_or_other",
            status="SKIPPED_NO_MEDIA"
        )
        return

    logger.info(f"📥 [{source_channel_name}:{source_msg_id}] Yangi {media_type} topildi. Yuklab olinmoqda...")

    # 3. Faylni yuklab olish
    temp_file_path = None
    try:
        temp_file_path = await message.download_media(file=config.DOWNLOAD_DIR)
        if not temp_file_path or not os.path.exists(temp_file_path):
            logger.error(f"❌ Faylni yuklab olishda xatolik: {temp_file_path}")
            return

        original_caption = message.raw_text or ""

        # 4. Sun'iy intellekt (Gemini) orqali tahlil qilish va izoh tayyorlash
        logger.info(f"🧠 [{source_channel_name}:{source_msg_id}] AI tahlili boshlandi...")
        eval_result = await evaluate_media(
            media_path=temp_file_path,
            media_type=media_type,
            original_caption=original_caption
        )

        # 5. Qaror: Kanalga joylash yoki rad etish
        if eval_result.is_approved:
            logger.info(
                f"✅ [{source_channel_name}:{source_msg_id}] TASDIQLANDI! "
                f"Ball: {eval_result.quality_score}/10. Maqsadli kanalga yuklanmoqda ({config.TARGET_CHANNEL})..."
            )
            
            # Maqsadli kanalga yuborish
            sent_msg = await client.send_file(
                config.TARGET_CHANNEL,
                file=temp_file_path,
                caption=eval_result.enhanced_caption,
                parse_mode="markdown"
            )

            # Bazaga muvaffaqiyatli saqlash
            await database.save_processed_message(
                source_channel=source_channel_name,
                source_message_id=source_msg_id,
                media_type=media_type,
                status="POSTED",
                quality_score=eval_result.quality_score,
                reason=eval_result.reason,
                target_message_id=sent_msg.id,
                original_caption=original_caption,
                enhanced_caption=eval_result.enhanced_caption
            )
            logger.info(f"🎉 Post muvaffaqiyatli joylandi! (Target Msg ID: {sent_msg.id})")
        else:
            logger.info(
                f"⛔️ [{source_channel_name}:{source_msg_id}] RAD ETILDI. "
                f"Ball: {eval_result.quality_score}/10. Sabab: {eval_result.reason}"
            )
            await database.save_processed_message(
                source_channel=source_channel_name,
                source_message_id=source_msg_id,
                media_type=media_type,
                status="REJECTED",
                quality_score=eval_result.quality_score,
                reason=eval_result.reason,
                original_caption=original_caption
            )

    except Exception as e:
        logger.error(f"❌ Xabarni qayta ishlashda xatolik yuz berdi: {e}", exc_info=True)
        await database.save_processed_message(
            source_channel=source_channel_name,
            source_message_id=source_msg_id,
            media_type=media_type or "unknown",
            status="ERROR",
            reason=str(e)
        )
    finally:
        # 6. Vaqtinchalik faylni o'chirish
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.warning(f"Vaqtinchalik faylni o'chirishda xatolik: {e}")


async def scan_recent_messages(client: TelegramClient, limit: int = 3):
    """Agent ishga tushganda manba kanallardagi oxirgi postlarni ko'rib chiqish."""
    logger.info(f"🔍 Manba kanallardagi oxirgi {limit} ta xabar tekshirilmoqda...")
    for source in config.SOURCE_CHANNELS:
        try:
            entity = await client.get_entity(source)
            messages = await client.get_messages(entity, limit=limit)
            # Eng eskidan yangiga qarab qayta ishlash
            for msg in reversed(messages):
                if msg.media:
                    await process_media_message(client, msg, source)
        except Exception as e:
            logger.error(f"Kanalni tekshirishda xatolik ({source}): {e}")


async def main():
    # 1. Sozlamalarni tekshirish
    errors = config.validate_config()
    if errors:
        logger.error("❌ Konfiguratsiya xatoliklari:")
        for err in errors:
            logger.error(f"  - {err}")
        logger.error("Iltimos, '.env' faylini to'g'ri to'ldiring (.env.example ga qarang).")
        return

    # 2. Bazani ishga tushirish
    await database.init_db()
    stats = await database.get_stats()
    logger.info(f"📊 Baza tayyor. Oldingi statistika: {stats}")

    # 3. Telegram mijozini ishga tushirish
    client = TelegramClient(
        config.TELEGRAM_SESSION_NAME,
        config.TELEGRAM_API_ID,
        config.TELEGRAM_API_HASH
    )

    await client.start()
    logger.info("🚀 Telegram akkaunt/bot muvaffaqiyatli ulandi!")

    # 4. Manba kanallarni tekshirish va entity olish
    source_entities = []
    for source in config.SOURCE_CHANNELS:
        try:
            entity = await client.get_entity(source)
            source_entities.append(entity)
            logger.info(f"✅ Manba kanal ulandi: {source}")
        except Exception as e:
            logger.error(f"❌ Manba kanal topilmadi ({source}): {e}")

    if not source_entities:
        logger.error("❌ Hech qaysi manba kanalga ulanib bo'lmadi! Dastur to'xtatildi.")
        return

    # 5. Maqsadli kanalni tekshirish
    try:
        target_entity = await client.get_entity(config.TARGET_CHANNEL)
        logger.info(f"✅ Maqsadli (joylanadigan) kanal tasdiqlandi: {config.TARGET_CHANNEL}")
    except Exception as e:
        logger.error(f"❌ Maqsadli kanalga ulanib bo'lmadi ({config.TARGET_CHANNEL}): {e}")
        logger.error("Akkauntingiz yoki botingiz ushbu kanalda administrator ekanligiga ishonch hosil qiling!")
        return

    # 6. Oxirgi postlarni tekshirish (o'tkazib yuborilganlarni ilib olish uchun)
    await scan_recent_messages(client, limit=3)

    # 7. Real vaqtda yangi postlarni tinglash hodisasi
    @client.on(events.NewMessage(chats=source_entities))
    async def handler(event):
        message = event.message
        if message.media:
            chat = await event.get_chat()
            chat_identifier = getattr(chat, "username", None) or str(chat.id)
            if chat_identifier and not chat_identifier.startswith("@") and not str(chat.id).startswith("-"):
                chat_identifier = f"@{chat_identifier}"
            logger.info(f"⚡️ Yangi post keldi ({chat_identifier})! Qayta ishlanmoqda...")
            await process_media_message(client, message, chat_identifier)

    logger.info("🟢 AGENT TO'LIQ ISHGA TUSHDI VA 24/7 REJIMDA YANGI POSTLARNI KUTMOQDA...")
    
    # Doimiy ishlash holatida ushlab turish
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Dastur foydalanuvchi tomonidan to'xtatildi.")
