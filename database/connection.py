import re
import time
from datetime import datetime, timedelta
import json
import asyncpg
from config import Config
from utils.logger import logger


# 글로벌 커넥션 풀
_pool: asyncpg.Pool | None = None


async def init_pool():
    """asyncpg 커넥션 풀을 초기화한다. 봇 시작 시 한 번 호출해야 한다."""
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=Config.DATABASE_URL,
        min_size=2,
        max_size=10,
        ssl="require",
    )
    logger.info("PostgreSQL 커넥션 풀이 초기화되었습니다.")


async def close_pool():
    """커넥션 풀을 종료한다. 봇 종료 시 호출해야 한다."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL 커넥션 풀이 종료되었습니다.")


def get_pool() -> asyncpg.Pool:
    """현재 커넥션 풀을 반환한다."""
    if _pool is None:
        raise RuntimeError("Database pool is not initialized. Call init_pool() first.")
    return _pool


async def create_table():
    """my_data 테이블이 없으면 생성한다."""
    async with get_pool().acquire() as conn:
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS my_data (
                time BIGINT,
                str_time TEXT,
                player INTEGER
            )"""
        )
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_time ON my_data (time)")


async def create_patch_table():
    """patch_notes 테이블이 없으면 생성한다."""
    async with get_pool().acquire() as conn:
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS patch_notes (
                id SERIAL PRIMARY KEY,
                major_version TEXT NOT NULL,
                major_date TEXT,
                major_patches TEXT,
                minor_patches TEXT,
                updated_at BIGINT NOT NULL,
                str_updated_at TEXT NOT NULL
            )"""
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_updated_at ON patch_notes (updated_at)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_major_version ON patch_notes (major_version)"
        )
        logger.debug("patch_notes 테이블 확인/생성 완료")


def _normalize_version(version: str) -> str:
    """버전 문자열을 정규화한다. trailing '.0'을 제거하여 "1.1.0" → "1.1" 형태로 통일한다."""
    normalized = re.sub(r"\.0$", "", version)
    if "." not in normalized:
        return version
    return normalized


async def _migrate_normalize_versions(conn):
    """DB에 저장된 x.x.0 형태의 버전을 x.x로 정규화한다.

    정규화된 버전이 이미 존재하면 데이터를 병합하고 중복 행을 삭제한다.
    """
    rows = await conn.fetch(
        "SELECT id, major_version, major_patches, minor_patches FROM patch_notes"
    )
    migrated_count = 0

    for row in rows:
        row_id, ver, major_patches_json, minor_patches_json = (
            row["id"], row["major_version"], row["major_patches"], row["minor_patches"]
        )
        normalized = _normalize_version(ver)
        if normalized == ver:
            continue

        # 정규화된 버전이 이미 존재하는지 확인
        existing = await conn.fetchrow(
            "SELECT id, major_patches, minor_patches FROM patch_notes WHERE major_version = $1",
            normalized,
        )

        if existing:
            # 두 행의 데이터를 병합: URL 기준으로 중복 제거
            existing_id, existing_major_json, existing_minor_json = (
                existing["id"], existing["major_patches"], existing["minor_patches"]
            )

            old_major = json.loads(major_patches_json) if major_patches_json else []
            new_major = json.loads(existing_major_json) if existing_major_json else []
            merged_major = {p["url"]: p for p in old_major}
            for p in new_major:
                merged_major[p["url"]] = p

            old_minor = json.loads(minor_patches_json) if minor_patches_json else []
            new_minor = json.loads(existing_minor_json) if existing_minor_json else []
            merged_minor = {p["url"]: p for p in old_minor}
            for p in new_minor:
                merged_minor[p["url"]] = p

            # 정규화된 행에 병합 데이터 업데이트
            await conn.execute(
                "UPDATE patch_notes SET major_patches = $1, minor_patches = $2 WHERE id = $3",
                json.dumps(sorted(merged_major.values(), key=lambda p: p.get("title", "")), ensure_ascii=False),
                json.dumps(sorted(merged_minor.values(), key=lambda p: p.get("version", "")), ensure_ascii=False),
                existing_id,
            )
            # 정규화 전 버전 행 삭제
            await conn.execute("DELETE FROM patch_notes WHERE id = $1", row_id)
        else:
            # 단순 UPDATE: major_version만 정규화
            await conn.execute(
                "UPDATE patch_notes SET major_version = $1 WHERE id = $2",
                normalized, row_id,
            )

        migrated_count += 1

    if migrated_count > 0:
        logger.info(f"버전 정규화 마이그레이션 완료: {migrated_count}개 버전 수정")


async def insert_patch_data(conn, patch_info):
    """패치노트 데이터 저장 함수 - 다중 파트 지원

    patch_info 구조:
    {
        "major_version": "10.4",     # 버전 식별자
        "major_date": "2024.03.12",  # 메이저 패치 날짜
        "major_patches": [...],      # 메이저 패치 파트 리스트
        "minor_patch_data": [...]    # 마이너 패치 리스트
    }
    """
    current_unix_time = int(time.time())
    current_str_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    major_version = patch_info.get("major_version")
    major_date = patch_info.get("major_date")
    major_patches = patch_info.get("major_patches", [])
    minor_patch_data = patch_info.get("minor_patch_data", [])

    if not major_version:
        logger.warning("메이저 패치 버전 정보가 없습니다.")
        return

    # 버전 정규화: "1.2.0" → "1.2" (trailing .0 제거)
    major_version = _normalize_version(major_version)

    # 기존 버전이 존재하는지 확인 (정규화 전 버전도 함께 조회)
    unnormalized = major_version + ".0"
    existing_row = await conn.fetchrow(
        "SELECT id, major_patches, minor_patches, major_version FROM patch_notes WHERE major_version = $1 OR major_version = $2",
        major_version, unnormalized,
    )
    if existing_row and existing_row["major_version"] != major_version:
        # 정규화 전 버전으로 저장된 행 발견 → major_version 컬럼도 정규화
        await conn.execute(
            "UPDATE patch_notes SET major_version = $1 WHERE id = $2",
            major_version, existing_row["id"],
        )

    if existing_row:
        # 기존 데이터와 URL 기준으로 병합하여 크롤링 누락 시 데이터 손실 방지
        existing_major_patches_json = existing_row["major_patches"]
        existing_minor_patches_json = existing_row["minor_patches"]

        # 메이저 패치 병합: 기존 데이터를 기반으로 새 데이터를 덮어쓰기
        existing_major = json.loads(existing_major_patches_json) if existing_major_patches_json else []
        merged_major = {p["url"]: p for p in existing_major}
        for p in major_patches:
            merged_major[p["url"]] = p
        major_patches = sorted(merged_major.values(), key=lambda p: p.get("title", ""))

        # 마이너 패치 병합: 동일하게 URL 기준 병합
        existing_minor = json.loads(existing_minor_patches_json) if existing_minor_patches_json else []
        merged_minor = {p["url"]: p for p in existing_minor}
        for p in minor_patch_data:
            merged_minor[p["url"]] = p
        minor_patch_data = sorted(merged_minor.values(), key=lambda p: p.get("version", ""))

        major_patches_json = json.dumps(major_patches, ensure_ascii=False)
        minor_patches_json = json.dumps(minor_patch_data, ensure_ascii=False)

        if (existing_major_patches_json != major_patches_json
                or existing_minor_patches_json != minor_patches_json):
            await conn.execute(
                """UPDATE patch_notes
                   SET major_date = $1, major_patches = $2, minor_patches = $3,
                       updated_at = $4, str_updated_at = $5
                   WHERE major_version = $6""",
                major_date,
                major_patches_json,
                minor_patches_json,
                current_unix_time,
                current_str_time,
                major_version,
            )
            logger.info(f"패치노트 버전 {major_version}이 업데이트되었습니다. ({current_str_time})")
            for part in major_patches:
                logger.debug(f"  - {part['title']}")
        else:
            logger.debug(f"패치노트 버전 {major_version}은(는) 이미 최신입니다.")
    else:
        # 새로운 버전이면 삽입
        major_patches_json = json.dumps(major_patches, ensure_ascii=False)
        minor_patches_json = json.dumps(minor_patch_data, ensure_ascii=False)
        await conn.execute(
            """INSERT INTO patch_notes
               (major_version, major_date, major_patches, minor_patches, updated_at, str_updated_at)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            major_version,
            major_date,
            major_patches_json,
            minor_patches_json,
            current_unix_time,
            current_str_time,
        )
        logger.info(f"새로운 패치노트 버전 {major_version}이 저장되었습니다. ({current_str_time})")
        for part in major_patches:
            logger.debug(f"  - {part['title']}")


async def get_latest_patch_data(conn):
    """최신 패치노트 데이터 조회 함수"""
    rows = await conn.fetch(
        """SELECT major_version, major_date, major_patches, minor_patches, str_updated_at
           FROM patch_notes
           ORDER BY major_version DESC"""
    )

    if not rows:
        return None

    # 버전 정렬을 위한 함수
    def sort_version_key(version_str):
        try:
            parts = version_str.split(".")
            return tuple(int(part) for part in parts)
        except (ValueError, AttributeError):
            return (0, 0)

    # 패치 데이터 처리 및 정렬
    all_patches = []
    for row in rows:
        major_version = row["major_version"]
        major_date = row["major_date"]
        major_patches_json = row["major_patches"]
        minor_patches_json = row["minor_patches"]
        str_updated_at = row["str_updated_at"]

        # JSON 파싱
        try:
            major_patches = json.loads(major_patches_json) if major_patches_json else []
            minor_patches = json.loads(minor_patches_json) if minor_patches_json else []
        except json.JSONDecodeError:
            major_patches = []
            minor_patches = []

        all_patches.append(
            {
                "major_version": major_version,
                "major_date": major_date,
                "major_patches": major_patches,
                "minor_patches": minor_patches,
                "str_updated_at": str_updated_at,
            }
        )

    # 버전별로 정렬
    all_patches.sort(key=lambda x: sort_version_key(x["major_version"]), reverse=True)

    # 최신 메이저 패치 찾기 및 마이너 패치 병합
    latest_major_patch = None
    combined_minor_patches = []

    for patch_data in all_patches:
        major_patches = patch_data["major_patches"]
        minor_patches = patch_data["minor_patches"]

        # 메이저 패치가 있는 경우
        if major_patches:
            if not latest_major_patch:
                # 첫 번째 메이저 패치를 최신으로 설정
                latest_major_patch = patch_data
                # 현재 버전의 마이너 패치도 추가
                combined_minor_patches.extend(minor_patches)
            break
        else:
            # 메이저 패치가 없는 경우, 마이너 패치를 수집
            combined_minor_patches.extend(minor_patches)

    if not latest_major_patch:
        return None

    # 기존 형식으로 반환 (하위 호환성)
    first_major = (
        latest_major_patch["major_patches"][0]
        if latest_major_patch["major_patches"]
        else {}
    )

    return {
        "major_patch_version": latest_major_patch["major_version"],
        "major_patch_date": latest_major_patch["major_date"]
        or first_major.get("date", ""),
        "major_patch_url": first_major.get("url", ""),
        "minor_patch_data": combined_minor_patches,
        "last_updated": latest_major_patch["str_updated_at"],
    }


async def get_all_patch_versions(conn):
    """모든 저장된 패치 버전 목록 조회 함수"""
    rows = await conn.fetch(
        """SELECT major_version, str_updated_at
           FROM patch_notes
           ORDER BY updated_at DESC"""
    )

    versions = []
    for row in rows:
        versions.append({"version": row["major_version"], "updated_at": row["str_updated_at"]})

    return versions


async def get_patch_data_by_version(conn, version):
    """특정 버전의 패치노트 데이터 조회 함수"""
    row = await conn.fetchrow(
        """SELECT major_version, major_date, major_patches, minor_patches, str_updated_at
           FROM patch_notes
           WHERE major_version = $1""",
        version,
    )

    if row:
        major_version = row["major_version"]
        major_date = row["major_date"]
        major_patches_json = row["major_patches"]
        minor_patches_json = row["minor_patches"]
        str_updated_at = row["str_updated_at"]

        # JSON 문자열을 파이썬 객체로 변환
        try:
            major_patches = json.loads(major_patches_json) if major_patches_json else []
            minor_patches = json.loads(minor_patches_json) if minor_patches_json else []
        except json.JSONDecodeError:
            major_patches = []
            minor_patches = []

        # 기존 형식으로 반환 (하위 호환성)
        first_major = major_patches[0] if major_patches else {}

        return {
            "major_patch_version": major_version,
            "major_patch_date": major_date or first_major.get("date", ""),
            "major_patch_url": first_major.get("url", ""),
            "minor_patch_data": minor_patches,
            "last_updated": str_updated_at,
        }
    return None


async def insert_data(conn, current_time, now, currentPlayer):
    """동접 데이터 저장 함수"""
    await conn.execute(
        "INSERT INTO my_data (time, str_time, player) VALUES ($1, $2, $3)",
        current_time, now, currentPlayer,
    )


async def delete_old_data(conn):
    """24시간 이상 된 동접 데이터 삭제 함수"""
    twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
    unix_time_24_hours_ago = int(time.mktime(twenty_four_hours_ago.timetuple()))
    await conn.execute("DELETE FROM my_data WHERE time < $1", unix_time_24_hours_ago)


async def get_most_data(conn):
    """현재 저장된 모든 데이터 중 가장 높은 유저값을 가진 출력 함수"""
    row = await conn.fetchrow("SELECT * FROM my_data ORDER BY player DESC LIMIT 1")
    if row:
        return row["player"]
    return 0


async def sort_by_time(conn, ascending=True):
    """시간순으로 정렬된 데이터를 반환한다."""
    order = "ASC" if ascending else "DESC"
    return await conn.fetch(f"SELECT * FROM my_data ORDER BY time {order}")


async def load_24h():
    """24시간 최고 동접 데이터를 조회한다."""
    async with get_pool().acquire() as conn:
        return await get_most_data(conn)


async def get_data():
    """전체 동접 데이터를 시간순으로 조회한다."""
    async with get_pool().acquire() as conn:
        rows = await sort_by_time(conn)
        data_list = [(row["time"], row["str_time"], row["player"]) for row in rows]
        logger.debug(f"get_data() result: {data_list}")
        return data_list


async def _get_latest_stored_version(conn) -> str:
    """DB에 저장된 버전 중 가장 최신 버전 문자열을 반환한다.

    버전 비교는 숫자 기반 정렬로 수행한다 (예: "10.1" > "9.4").

    Returns:
        str: 가장 최신 버전 문자열. DB가 비어있으면 None.
    """
    rows = await conn.fetch("SELECT major_version FROM patch_notes")
    if not rows:
        return None

    def version_key(v):
        try:
            return tuple(int(x) for x in v.split("."))
        except (ValueError, AttributeError):
            return (0, 0)

    versions = [row["major_version"] for row in rows]
    return max(versions, key=version_key)


async def save_patch_notes_to_db(force_full: bool = False):
    """패치노트를 크롤링해서 DB에 저장하는 함수.

    동작 모드:
    - force_full=True (/ㅍㄴ새로고침 명령어 사용 시):
        더보기를 끝까지 눌러 전체 패치 히스토리를 수집한 뒤 DB와 비교하여 저장한다.
    - force_full=False (봇 시작 시 / 자동 주기 크롤링 시):
        DB에 저장된 가장 최신 버전을 확인하고, 그 버전이 페이지에 나타날 때까지만
        더보기를 클릭하여 새로운 버전들만 증분 저장한다.
        DB가 비어있는 경우에는 전체 히스토리를 수집한다.

    Args:
        force_full: True이면 전체 크롤링 모드, False이면 증분 크롤링 모드.
    """
    try:
        from core.api.eternal_return import get_patchnote

        # DB 상태 확인 (저장된 버전 수 및 최신 버전 조회)
        async with get_pool().acquire() as conn:
            await create_patch_table()
            existing_count = await conn.fetchval("SELECT COUNT(*) FROM patch_notes")
            latest_stored_version = await _get_latest_stored_version(conn)

        if force_full:
            # 전체 크롤링 모드: 더보기를 끝까지 눌러 전체 히스토리 수집
            logger.info("전체 크롤링 모드 — 더보기를 끝까지 눌러 전체 패치 히스토리를 수집합니다...")
            crawl_result = await get_patchnote(load_all=True)
        elif existing_count == 0:
            # DB가 비어있으면 최초 전체 수집
            logger.info("DB가 비어있습니다. 전체 패치 히스토리를 수집합니다 (더보기 끝까지 클릭)...")
            crawl_result = await get_patchnote(load_all=True)
        else:
            # 증분 모드: 최신 저장 버전까지만 더보기를 클릭하여 그 이후 버전들만 수집
            logger.info(
                f"증분 크롤링 모드 — DB 최신 버전: {latest_stored_version}. "
                f"그 이후 버전들을 확인합니다..."
            )
            crawl_result = await get_patchnote(load_all=False, until_version=latest_stored_version)

        if not crawl_result:
            logger.error("패치노트 크롤링에 실패했습니다.")
            return False

        # 크롤러가 반환한 버전 목록 처리
        versions = crawl_result.get("versions", [])
        if not versions:
            logger.warning("크롤링된 패치노트 버전 정보가 없습니다.")
            return False

        async with get_pool().acquire() as conn:
            # 기존 DB의 x.x.0 버전을 x.x로 정규화 (마이그레이션)
            await _migrate_normalize_versions(conn)

            saved_count = 0
            for version_data in versions:
                await insert_patch_data(conn, version_data)
                saved_count += 1

        logger.info(f"패치노트 데이터 저장 완료 (처리한 버전 수: {saved_count}개)")
        return True

    except Exception as e:
        logger.error(f"패치노트 저장 중 오류 발생: {e}")
        return False


async def get_patch_notes_from_db():
    """DB에서 패치노트 데이터를 가져오는 함수"""
    try:
        await create_patch_table()

        async with get_pool().acquire() as conn:
            patch_data = await get_latest_patch_data(conn)

        return patch_data

    except Exception as e:
        logger.error(f"패치노트 조회 중 오류 발생: {e}")
        return None
