import asyncio
from telethon import TelegramClient, events, Button
from sqlalchemy import select, desc, func

from app.core.config import settings
from app.core.logging import logger
from app.core.database import get_db_session
from app.models.schema import Source, ContentCandidate, Post, PostMetric, MediaAnalysis, MediaAsset
from app.engines.strategist import strategist_engine
from app.engines.publisher import telegram_publisher


def register_admin_bot_handlers(client: TelegramClient):
    """Admin buyruqlari va interaktiv boshqaruv tugmalarini ulaydi."""

    @client.on(events.NewMessage(pattern="(?i)^/start"))
    async def cmd_start(event):
        sender = await event.get_sender()
        text = (
            f"👋 Assalomu alaykum, {getattr(sender, 'first_name', 'Admin')}!\n\n"
            "🤖 **Autonomous Telegram AI Media Creator — Boshqaruv Markazi**\n\n"
            "Mavjud buyruqlar:\n"
            "📊 /status — Tizim va navbatlar holati\n"
            "📈 /today — Bugungi umumiy statistika\n"
            "📥 /queue — Moderatsiyadagi nomzodlar\n"
            "📡 /sources — Manba kanallar ro'yxati\n"
            "🧠 /strategist — AI Strategist tavsiyalari\n"
            "⚙️ /settings — Tizim sozlamalari"
        )
        buttons = [
            [Button.inline("📊 Statistika", b"btn_today"), Button.inline("📥 Navbat", b"btn_queue")],
            [Button.inline("📡 Manbalar", b"btn_sources"), Button.inline("🧠 AI Strateg", b"btn_strategist")]
        ]
        await event.respond(text, buttons=buttons)

    @client.on(events.NewMessage(pattern="(?i)^/status"))
    async def cmd_status(event):
        async with get_db_session() as session:
            sources_count = (await session.execute(select(func.count(Source.id)))).scalar() or 0
            cand_count = (await session.execute(select(func.count(ContentCandidate.id)))).scalar() or 0
            post_count = (await session.execute(select(func.count(Post.id)))).scalar() or 0

        text = (
            "🟢 **TIZIM SALOMATLIGI: ONLINE**\n\n"
            f"📡 Faol manbalar: {sources_count} ta\n"
            f"📥 Jami nomzodlar: {cand_count} ta\n"
            f"🚀 E'lon qilingan postlar: {post_count} ta\n"
            f"🛡 Boshqaruv rejimi: `{settings.GOVERNANCE_MODE}`\n"
            f"🎯 Maqsadli kanal: {settings.TARGET_CHANNEL}"
        )
        await event.respond(text)

    @client.on(events.NewMessage(pattern="(?i)^/today"))
    async def cmd_today(event):
        async with get_db_session() as session:
            total = (await session.execute(select(func.count(ContentCandidate.id)))).scalar() or 0
            posted = (await session.execute(select(func.count(Post.id)))).scalar() or 0
            avg_score = (await session.execute(select(func.avg(ContentCandidate.final_score)))).scalar() or 0.0

        text = (
            "📊 **Bugungi umumiy natijalar:**\n\n"
            f"📥 Qabul qilingan: {total} ta\n"
            f"✅ Joylangan: {posted} ta\n"
            f"⭐ O'rtacha sifat bali: {round(avg_score, 1)} / 100\n"
            f"🤖 AI Modeli: `{settings.GEMINI_MODEL}`"
        )
        await event.respond(text)

    @client.on(events.NewMessage(pattern="(?i)^/sources"))
    async def cmd_sources(event):
        async with get_db_session() as session:
            sources = (await session.execute(select(Source))).scalars().all()
            lines = ["📡 **Kuzatilayotgan manba kanallar:**\n"]
            for s in sources:
                icon = "🟢" if s.status == "ACTIVE" else "⏸"
                lines.append(f"{icon} `{s.username}` — Prioritet: {s.priority}, Ishonch: {s.trust_score}")
        await event.respond("\n".join(lines))

    @client.on(events.NewMessage(pattern="(?i)^/strategist"))
    async def cmd_strategist(event):
        await event.respond("⏳ AI Strategist hisoboti tayyorlanmoqda...")
        report = await strategist_engine.generate_daily_report()
        recs = "\n".join(f"• {r}" for r in report["recommendations"])
        text = (
            f"🧠 **AI Strategist Xulosasi ({report['top_category']}):**\n\n"
            f"🔥 Eng yaxshi natija ko'rsatgan toifa: **{report['top_category']}** ({report['best_engagement']}% engagement)\n\n"
            f"💡 **Tavsiyalar:**\n{recs}"
        )
        await event.respond(text)

    @client.on(events.CallbackQuery)
    async def callback_handler(event):
        data = event.data.decode("utf-8")
        if data == "btn_today":
            await cmd_today(event)
        elif data == "btn_sources":
            await cmd_sources(event)
        elif data == "btn_strategist":
            await cmd_strategist(event)
        await event.answer()

    logger.info("🤖 Admin Telegram Bot buyruqlari muvaffaqiyatli ulandi.")
