import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv(verbose=True)


class Config:
    """봇 설정 관리 클래스"""

    # Discord 봇 토큰
    BREAD_TOKEN = os.getenv("BREAD_TOKEN")
    INFERIORITY_TOKEN = os.getenv("INFERIORITY_TOKEN")

    # API 키들
    ER_API_KEY = os.getenv("ER")
    STEAM_API_KEY = os.getenv("steam")

    # 봇 설정
    BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID"))
    SPECIFIC_SERVER_ID = int(os.getenv("SPECIFIC_SERVER_ID"))
    LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
    # 패치노트 메시지 트리거용 채널 ID. 미설정 시 0 → 어떤 채널과도 매칭되지 않아 자동 비활성
    PATCH_NOTIFY_CHANNEL_ID = int(os.getenv("PATCH_NOTIFY_CHANNEL_ID", "0"))

    # 데이터베이스 설정
    DATABASE_URL = os.getenv("DATABASE_URL")

    # 디렉토리 경로
    IMAGE_PATH = "./assets/images"
    LOGS_PATH = "./logs"

    @classmethod
    def validate(cls):
        """설정 값 검증"""
        required_vars = [
            ("BREAD_TOKEN", cls.BREAD_TOKEN),
            ("ER_API_KEY", cls.ER_API_KEY),
            ("STEAM_API_KEY", cls.STEAM_API_KEY),
            ("DATABASE_URL", cls.DATABASE_URL),
        ]

        missing_vars = [name for name, value in required_vars if not value]

        if missing_vars:
            raise ValueError(
                f"필수 환경변수가 설정되지 않았습니다: {', '.join(missing_vars)}"
            )

        return True
