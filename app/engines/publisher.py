from pathlib import Path
from datetime import datetime
from typing import Optional
from telethon import TelegramClient
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.core.database import get_db_session
from app.models.schema import ContentCandidate, Post, Caption, MediaAsset, LegacyProcessedMessage


class TelegramPublisher:
    """Idempotent Telegram nashriyotchi (Publisher)."""

    @classmethod
    async def publish_candidate(
        cls,
        client: TelegramClient,
        candidate_id: int,
        target_channel: Optional[str] = None
    ) -> Optional[int]:
        target = target_channel or settings.TARGET_CHANNEL

        async with get_db_session() as session:
            candidate = await session.get(ContentCandidate, candidate_id)
            if not candidate:
                logger.error(f"Nomzod topilmadi: {candidate_id}")
                return None

            # Idempotency tekshiruvi: Agar bu nomzod avval nashr qilingan bo'lsa
            existing_post = (await session.execute(
                select(Post).where(Post.candidate_id == candidate_id)
            )).scalar_one_or_none()

            if existing_post:
                logger.warning(f"Nomzod {candidate_id} avval nashr qilingan (Target Msg ID: {existing_post.target_message_id}). Qayta yuborilmaydi.")
                return existing_post.target_message_id

            asset = await session.get(MediaAsset, candidate.media_asset_id)
            selected_caption = (await session.execute(
                select(Caption.full_caption).where(Caption.candidate_id == candidate_id, Caption.is_selected == True)
            )).scalar_one_or_none() or ""

            file_path = Path(asset.local_path)
            if not file_path.exists():
                logger.error(f"Nashr qilish uchun fayl topilmadi: {file_path}")
                return None

            logger.info(f"🚀 Kanalga joylanmoqda ({target}): Candidate ID {candidate_id}...")

            sent_msg = None
            try:
                # Markdown formatida yuborish
                sent_msg = await client.send_file(
                    target,
                    file=str(file_path),
                    caption=selected_caption,
                    parse_mode="markdown"
                )
            except Exception as e:
                logger.warning(f"Markdown formatida xatolik ({e}), oddiy matn bilan qayta urinilmoqda...")
                sent_msg = await client.send_file(
                    target,
                    file=str(file_path),
                    caption=selected_caption,
                    parse_mode=None
                )

            if sent_msg:
                new_post = Post(
                    candidate_id=candidate_id,
                    target_channel=target,
                    target_message_id=sent_msg.id,
                    caption_used=selected_caption,
                    published_at=datetime.utcnow(),
                    status="ACTIVE"
                )
                session.add(new_post)
                candidate.status = "PUBLISHED"

                # Orqaga moslik uchun Legacy jadvalga ham yozish
                session.add(LegacyProcessedMessage(
                    source_channel=target,
                    source_message_id=sent_msg.id,
                    media_type=asset.mime_type or "media",
                    status="POSTED",
                    quality_score=int(candidate.final_score / 10),
                    reason="Autonomous AI Media Creator tomonidan joylandi",
                    target_message_id=sent_msg.id,
                    enhanced_caption=selected_caption,
                    created_at=datetime.utcnow()
                ))

                await session.commit()
                logger.info(f"🎉 Post muvaffaqiyatli kanalga chiqdi! (Target Msg ID: {sent_msg.id})")
                return sent_msg.id

        return None


telegram_publisher = TelegramPublisher()
