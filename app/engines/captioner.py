from typing import Dict, Any, Tuple
from app.engines.ai_provider import get_ai_provider, MultiCaptionSchema
from app.core.database import get_db_session
from app.models.schema import Caption, ContentCandidate
from app.core.logging import logger


class CaptionEngine:
    """3 xil uslubda matn generatsiya qiluvchi va saralovchi engine."""

    @classmethod
    async def create_and_store_captions(
        cls,
        candidate_id: int,
        category: str,
        original_caption: str = "",
        analysis_summary: str = ""
    ) -> Tuple[str, str]:
        ai = get_ai_provider()
        multi_caps: MultiCaptionSchema = await ai.generate_captions(
            category=category,
            original_caption=original_caption,
            analysis_summary=analysis_summary
        )

        async with get_db_session() as session:
            # 3 xil uslubni saqlash
            styles_map = {
                "INFORMATIVE": multi_caps.informative,
                "EMOTIONAL": multi_caps.emotional,
                "INTERACTIVE": multi_caps.interactive
            }

            # Kategoriya bo'yicha eng yaxshi uslubni tanlash (masalan: Spiritual -> Emotional, Educational -> Informative)
            default_selected_style = "EMOTIONAL"
            if category == "Educational":
                default_selected_style = "INFORMATIVE"
            elif category == "Human Story":
                default_selected_style = "INTERACTIVE"

            selected_full_caption = ""

            for style_name, cap_data in styles_map.items():
                is_sel = (style_name == default_selected_style)
                c_obj = Caption(
                    candidate_id=candidate_id,
                    style=style_name,
                    title=cap_data.title,
                    body=cap_data.body,
                    question=cap_data.question,
                    hashtags=cap_data.hashtags,
                    full_caption=cap_data.full_caption,
                    is_selected=is_sel
                )
                session.add(c_obj)
                if is_sel:
                    selected_full_caption = cap_data.full_caption

            await session.commit()
            return default_selected_style, selected_full_caption


caption_engine = CaptionEngine()
