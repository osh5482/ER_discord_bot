"""
로그 설정 모듈

loguru를 사용하여 콘솔 및 파일 로깅을 설정한다.
이 모듈은 봇의 모든 모듈에서 공유하는 단일 logger 인스턴스를 제공하며,
standalone 스크립트(all_patch_crawler.py 등)에서도 독립적으로 사용 가능하다.

사용법:
    from utils.logger import logger
    logger.info("메시지")
    logger.error("오류: {e}", e=e)
"""

import sys
import logging
from pathlib import Path
from loguru import logger


def setup_logger() -> None:
    """
    loguru 전역 로거를 설정한다.

    설정 내용:
    - 콘솔(stderr): DEBUG 이상, 컬러 출력, 모듈명/함수명/라인 포함
    - 파일(logs/bot.log): INFO 이상, 매일 자정 rotation, 7일 보관, zip 압축
    - discord.py 내부 logging 인터셉트: WARNING 이상 동일 파일에 기록
    """

    # logs/ 디렉토리가 없으면 자동 생성
    Path("logs").mkdir(exist_ok=True)

    # loguru 기본 핸들러(stderr) 제거 후 직접 설정
    logger.remove()

    # 콘솔 핸들러: DEBUG 이상, 컬러 출력
    # enqueue=True: asyncio 환경에서 스레드 안전성 보장
    logger.add(
        sys.stderr,
        level="DEBUG",
        colorize=True,
        enqueue=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    # 파일 핸들러: INFO 이상, 매일 자정 rotation, 7일 보관, zip 압축
    logger.add(
        "logs/bot.log",
        level="INFO",
        encoding="utf-8",
        rotation="00:00",       # 매일 자정에 새 파일로 교체
        retention="7 days",     # 7일치 보관 후 삭제
        compression="zip",      # 오래된 로그 파일 zip 압축
        enqueue=True,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} - "
            "{message}"
        ),
    )

    # discord.py 내부 logging 인터셉트
    # discord.py는 표준 logging 모듈을 사용하므로, InterceptHandler를 통해
    # loguru와 동일한 파일에 기록되도록 브릿지를 연결한다.
    class InterceptHandler(logging.Handler):
        """표준 logging 모듈 → loguru 브릿지 핸들러"""

        def emit(self, record: logging.LogRecord) -> None:
            # 표준 logging 레벨명을 loguru 레벨로 변환
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # 실제 로그 발생 위치(호출 스택)를 찾아 loguru에 전달
            frame, depth = sys._getframe(6), 6
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    # 루트 로거와 discord 로거에 인터셉터 등록 (WARNING 이상만 처리)
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.WARNING, force=True)
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)


# 모듈 import 시 자동으로 로거 설정 적용
setup_logger()

__all__ = ["logger"]
