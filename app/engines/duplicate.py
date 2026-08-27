import os
import hashlib
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import imagehash
from sqlalchemy import select

from app.core.logging import logger
from app.core.database import get_db_session
from app.models.schema import MediaAsset, DuplicateMatch, Post, LegacyProcessedMessage


class DuplicateEngine:
    """Exact (SHA-256), Duration va Video Keyframe Perceptual Visual (pHash / dHash) dublikatlarni aniqlovchi engine."""

    @staticmethod
    def calculate_sha256(file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def extract_video_frame(video_path: Path, timestamp_sec: float = 1.0) -> Optional[Path]:
        """FFmpeg orqali videoning 1-soniyasidan kadr (frame) sug'urib oladi."""
        output_frame = video_path.parent / f"thumb_{video_path.stem}.jpg"
        try:
            cmd = [
                "ffmpeg", "-y", "-ss", str(timestamp_sec),
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", "2",
                str(output_frame)
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            if res.returncode == 0 and output_frame.exists():
                return output_frame
        except Exception:
            pass
        return None

    @classmethod
    def calculate_visual_hashes(cls, file_path: Path, media_type: str = "photo") -> Tuple[Optional[str], Optional[str]]:
        try:
            target_image = file_path
            temp_frame = None

            if media_type == "video":
                temp_frame = cls.extract_video_frame(file_path)
                if temp_frame:
                    target_image = temp_frame

            if target_image.exists() and target_image.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                with Image.open(target_image) as img:
                    phash_val = str(imagehash.phash(img))
                    dhash_val = str(imagehash.dhash(img))

                    if temp_frame and temp_frame.exists():
                        try:
                            temp_frame.unlink()
                        except Exception:
                            pass

                    return phash_val, dhash_val
        except Exception as e:
            logger.debug(f"Visual hash hisoblashda xatolik: {e}")

        return None, None

    @classmethod
    async def check_duplicate(cls, file_path: Path, media_type: str) -> Tuple[bool, Optional[int], str, float]:
        """
        Media faylni bazadagi barcha oldingi fayllar bilan solishtiradi.
        
        Qaytaradi: (is_duplicate, matched_media_id, match_type, similarity_score)
        """
        sha256 = cls.calculate_sha256(file_path)
        phash_str, dhash_str = cls.calculate_visual_hashes(file_path, media_type)

        async with get_db_session() as session:
            # 1. Aniq fayl bayt dublikati (SHA-256)
            res = await session.execute(
                select(MediaAsset).where(MediaAsset.sha256_hash == sha256)
            )
            exact_match = res.scalar_one_or_none()
            if exact_match:
                logger.info(f"🔁 SHA-256 bo'yicha 100% aniq dublikat topildi (Media ID: {exact_match.id})")
                return True, exact_match.id, "EXACT_SHA256", 1.0

            # 2. Vizual perceptual dublikat (pHash / dHash) - RASM VA VIDEO KADRLARI UCHUN
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
                            
                            # Agar farq <= 6 bo'lsa (taxminan 90%+ vizual o'xshashlik)
                            if diff <= 6:
                                sim = round((64 - diff) / 64, 2)
                                logger.info(f"🖼 Vizual pHash dublikat topildi ({media_type.upper()}) (Media ID: {asset.id}, O'xshashlik: {sim*100}%)")
                                return True, asset.id, "VISUAL_PHASH", sim
                        except Exception:
                            continue

        return False, None, "NONE", 0.0


duplicate_engine = DuplicateEngine()
