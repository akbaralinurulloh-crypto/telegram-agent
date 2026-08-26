import aiosqlite
from datetime import datetime
from config import DATABASE_PATH


async def init_db():
    """Ma'lumotlar bazasini va jadvallarni initsializatsiya qilish."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS processed_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_channel TEXT NOT NULL,
                source_message_id INTEGER NOT NULL,
                media_type TEXT,
                status TEXT NOT NULL,
                quality_score INTEGER DEFAULT 0,
                reason TEXT,
                target_message_id INTEGER,
                original_caption TEXT,
                enhanced_caption TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_channel, source_message_id)
            )
        """)
        await db.commit()


async def is_message_processed(source_channel: str, source_message_id: int) -> bool:
    """Xabar avval muvaffaqiyatli tekshirilganmi yoki yo'qligini aniqlash (ERROR holatidagilarni qayta ishlashga ruxsat beradi)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM processed_messages WHERE source_channel = ? AND source_message_id = ? AND status != 'ERROR'",
            (source_channel, source_message_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def save_processed_message(
    source_channel: str,
    source_message_id: int,
    media_type: str,
    status: str,
    quality_score: int = 0,
    reason: str = "",
    target_message_id: int | None = None,
    original_caption: str | None = None,
    enhanced_caption: str | None = None
):
    """Qayta ishlangan xabar natijasini bazaga yozib qo'yish."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO processed_messages 
            (source_channel, source_message_id, media_type, status, quality_score, reason, target_message_id, original_caption, enhanced_caption, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            source_channel,
            source_message_id,
            media_type,
            status,
            quality_score,
            reason,
            target_message_id,
            original_caption,
            enhanced_caption,
            datetime.now().isoformat()
        ))
        await db.commit()


async def get_stats() -> dict:
    """Agent faoliyati statistikasi."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM processed_messages") as c1:
            total = (await c1.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM processed_messages WHERE status = 'POSTED'") as c2:
            posted = (await c2.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM processed_messages WHERE status LIKE 'REJECTED%'") as c3:
            rejected = (await c3.fetchone())[0]

        return {
            "total_seen": total,
            "posted": posted,
            "rejected": rejected
        }
