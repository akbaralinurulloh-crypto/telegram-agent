import hashlib
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import imagehash
from sqlalchemy import select

from app.core.logging import logger
from app.core.database import get_db_session
from app.models.schema import MediaAsset, DuplicateMatch


class DuplicateEngine:
    """Exact (SHA-256) va Perceptual Visual (pHash / dHash) dublikatlarni aniqlovchi engine."""

    @staticmethod
    def calculate_sha256(file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def calculate_visual_hashes(file_path: Path) -> Tuple[Optional[str], Optional[str]]:
        try:
            with Image.open(file_path) as img:
                phash_val = str(imagehash.phash(img))
                dhash_val = str(imagehash.dhash(img))
                return phash_val, dhash_val
        except Exception:
            return None, None

    @classmethod
    async def check_duplicate(cls, file_path: Path, media_type: str) -> Tuple[bool, Optional[int], str, float]:
        """
        Media faylni bazadagi barcha oldingi fayllar bilan solishtiradi.
        
        Qaytaradi: (is_duplicate, matched_media_id, match_type, similarity_score)
        """
        sha256 = cls.calculate_sha256(file_path)
        phash_str, dhash_str = None, None
        if media_type == "photo":
            phash_str, dhash_str = cls.calculate_visual_hashes(file_path)

        async with get_db_session() as session:
            # 1. Aniq fayl bayt dublikati (SHA-256)
            res = await session.execute(
                select(MediaAsset).where(MediaAsset.sha256_hash == sha256)
            )
            exact_match = res.scalar_one_or_none()
            if exact_match:
                logger.info(f"🔁 SHA-256 bo'yicha 100% aniq dublikat topildi (Media ID: {exact_match.id})")
                return True, exact_match.id, "EXACT_SHA256", 1.0

            # 2. Vizual perceptual dublikat (pHash / dHash)
            if phash_str:
                current_phash = imagehash.hex_to_hash(phash_str)
                all_assets = (await session.execute(
                    select(MediaAsset).where(MediaAsset.phash.isnot(None))
                )).scalars().all()

                for asset in all_assets:
                    if asset.phash:
                        try:
                            prev_phash = imagehash.hex_to_hash(asset.phash)
                            diff = current_phash - prev_phash  # Hamming masofasi (0-64)
                            # Agar farq <= 5 bo'lsa (taxminan 92%+ o'xshashlik)
                            if diff <= 5:
                                sim = round((64 - diff) / 64, 2)
                                logger.info(f"🖼 Vizual pHash dublikat topildi (Media ID: {asset.id}, O'xshashlik: {sim*100}%)")
                                return True, asset.id, "VISUAL_PHASH", sim
                        except Exception:
                            continue

        return False, None, "NONE", 0.0


duplicate_engine = DuplicateEngine()
