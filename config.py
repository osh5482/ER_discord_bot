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
    BOT_OWNER_ID = 393987987005767690
    SPECIFIC_SERVER_ID = 1156212577202872351
    LOG_CHANNEL_ID = 1227163092719374366

    # 데이터베이스 설정
    DATABASE_PATH = "data.db"

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
        ]

        missing_vars = [name for name, value in required_vars if not value]

        if missing_vars:
            raise ValueError(
                f"필수 환경변수가 설정되지 않았습니다: {', '.join(missing_vars)}"
            )

        return True
