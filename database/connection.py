import asyncio
import sqlite3
import time
from datetime import datetime, timedelta
import json
from config import Config


def connect_DB():
    """데이터베이스 연결 함수"""
    conn = sqlite3.connect(Config.DATABASE_PATH, isolation_level=None)
    c = conn.cursor()
    return conn, c


def create_table(c):
    """테이블 생성 여부 확인"""
    c.execute(
        """SELECT count(name) FROM sqlite_master WHERE type='table' AND name='my_data' """
    )
    if c.fetchone()[0] == 0:
        c.execute(
            """CREATE TABLE my_data (time INTEGER, str_time TEXT, player INTEGER)"""
        )

    # time 컬럼을 index로 설정
    c.execute("CREATE INDEX IF NOT EXISTS idx_time ON my_data (time)")


def create_patch_table(c):
    """패치노트 테이블 생성 함수 - 새로운 구조"""
    c.execute(
        """SELECT count(name) FROM sqlite_master WHERE type='table' AND name='patch_notes' """
    )
    if c.fetchone()[0] == 0:
        c.execute(
            """CREATE TABLE patch_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                major_version TEXT NOT NULL,
                major_date TEXT,
                major_patches TEXT,
                minor_patches TEXT,
                updated_at INTEGER NOT NULL,
                str_updated_at TEXT NOT NULL
            )"""
        )
        print("패치노트 테이블이 생성되었습니다.")

    # updated_at 컬럼을 index로 설정
    c.execute("CREATE INDEX IF NOT EXISTS idx_updated_at ON patch_notes (updated_at)")
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_major_version ON patch_notes (major_version)"
    )


def insert_patch_data(c, patch_info):
    """패치노트 데이터 저장 함수 - 제목 정보 포함"""
    current_unix_time = int(time.time())
    current_str_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    major_version = patch_info.get("major_patch_version")
    major_date = patch_info.get("major_patch_date")
    major_url = patch_info.get("major_patch_url")
    major_title = patch_info.get("major_patch_title")  # 패치노트 제목 추가
    minor_patch_data = patch_info.get("minor_patch_data", [])

    if not major_version:
        print("메이저 패치 버전 정보가 없습니다.")
        return

    # 기존 방식과 호환성을 위해 major_url을 major_patches 형태로 변환
    if major_url:
        major_patches = [
            {
                "version": major_version,
                "url": major_url,
                "title": (
                    major_title if major_title else f"{major_version} PATCH NOTES"
                ),  # 실제 제목 사용
                "date": major_date or "",
            }
        ]
    else:
        major_patches = []

    # JSON 문자열로 변환
    major_patches_json = json.dumps(major_patches, ensure_ascii=False)
    minor_patches_json = json.dumps(minor_patch_data, ensure_ascii=False)

    # 기존 버전이 존재하는지 확인
    c.execute("SELECT id FROM patch_notes WHERE major_version = ?", (major_version,))
    existing_row = c.fetchone()

    if existing_row:
        # 기존 버전이 존재하면 업데이트
        c.execute(
            """UPDATE patch_notes 
               SET major_date = ?, major_patches = ?, minor_patches = ?, 
                   updated_at = ?, str_updated_at = ?
               WHERE major_version = ?""",
            (
                major_date,
                major_patches_json,
                minor_patches_json,
                current_unix_time,
                current_str_time,
                major_version,
            ),
        )
        print(
            f"패치노트 버전 {major_version}이 업데이트되었습니다. ({current_str_time})"
        )
        if major_title:
            print(f"  제목: {major_title}")
    else:
        # 새로운 버전이면 삽입
        c.execute(
            """INSERT INTO patch_notes 
               (major_version, major_date, major_patches, minor_patches, updated_at, str_updated_at) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                major_version,
                major_date,
                major_patches_json,
                minor_patches_json,
                current_unix_time,
                current_str_time,
            ),
        )
        print(
            f"새로운 패치노트 버전 {major_version}이 저장되었습니다. ({current_str_time})"
        )
        if major_title:
            print(f"  제목: {major_title}")


def get_latest_patch_data(c):
    """최신 패치노트 데이터 조회 함수 - 새로운 구조에 맞게 수정"""
    # 모든 패치 데이터를 버전 순으로 정렬하여 가져오기
    c.execute(
        """SELECT major_version, major_date, major_patches, minor_patches, str_updated_at 
           FROM patch_notes 
           ORDER BY major_version DESC"""
    )
    rows = c.fetchall()

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
        (
            major_version,
            major_date,
            major_patches_json,
            minor_patches_json,
            str_updated_at,
        ) = row

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
        "minor_patch_data": combined_minor_patches,  # 병합된 마이너 패치들
        "last_updated": latest_major_patch["str_updated_at"],
    }


def get_all_patch_versions(c):
    """모든 저장된 패치 버전 목록 조회 함수 - 새로운 구조에 맞게 수정"""
    c.execute(
        """SELECT major_version, str_updated_at 
           FROM patch_notes 
           ORDER BY updated_at DESC"""
    )
    rows = c.fetchall()

    versions = []
    for row in rows:
        major_version, str_updated_at = row
        versions.append({"version": major_version, "updated_at": str_updated_at})

    return versions


def get_patch_data_by_version(c, version):
    """특정 버전의 패치노트 데이터 조회 함수 - 새로운 구조에 맞게 수정"""
    c.execute(
        """SELECT major_version, major_date, major_patches, minor_patches, str_updated_at 
           FROM patch_notes 
           WHERE major_version = ?""",
        (version,),
    )
    row = c.fetchone()

    if row:
        (
            major_version,
            major_date,
            major_patches_json,
            minor_patches_json,
            str_updated_at,
        ) = row

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


def insert_data(c, current_time, now, currentPlayer):
    """데이터 저장 함수"""
    c.execute(
        "INSERT INTO my_data (time, str_time, player) VALUES (?,?, ?)",
        (current_time, now, currentPlayer),
    )


def delete_old_data(c):
    """이전 데이터 삭제 함수"""
    twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
    unix_time_24_hours_ago = int(time.mktime(twenty_four_hours_ago.timetuple()))
    c.execute("DELETE FROM my_data WHERE time < ?", (unix_time_24_hours_ago,))


def get_most_data(c):
    """현재 저장된 모든 데이터 중 가장 높은 유저값을 가진 출력 함수"""
    c.execute("SELECT * FROM my_data ORDER BY player DESC LIMIT 1")
    row = c.fetchall()[0]
    players = row[-1]
    return players


def sort_by_time(c, ascending=True):
    # ascending이 True이면 오름차순, False이면 내림차순으로 정렬
    order = "ASC" if ascending else "DESC"
    c.execute("SELECT * FROM my_data ORDER BY time " + order)


async def load_24h():
    conn, c = connect_DB()
    most_24h = get_most_data(c)
    c.close()
    conn.close()
    return most_24h


async def get_data():
    conn, c = connect_DB()
    sort_by_time(c)

    c.execute("SELECT * FROM my_data")
    rows = c.fetchall()

    data_list = []
    for row in rows:
        data_list.append(row)

    c.close()
    conn.close()
    print(data_list)
    return data_list


async def save_patch_notes_to_db():
    """패치노트를 크롤링해서 DB에 저장하는 함수"""
    try:
        from core.api.eternal_return import get_patchnote

        print("패치노트 크롤링을 시작합니다...")
        patch_info = await get_patchnote()

        if patch_info:
            conn, c = connect_DB()
            create_patch_table(c)
            insert_patch_data(c, patch_info)
            c.close()
            conn.close()
            print("패치노트 데이터가 성공적으로 저장되었습니다.")
            return True
        else:
            print("패치노트 크롤링에 실패했습니다.")
            return False

    except Exception as e:
        print(f"패치노트 저장 중 오류 발생: {e}")
        return False


async def get_patch_notes_from_db():
    """DB에서 패치노트 데이터를 가져오는 함수"""
    try:
        conn, c = connect_DB()
        create_patch_table(c)  # 테이블이 없으면 생성

        patch_data = get_latest_patch_data(c)

        c.close()
        conn.close()

        return patch_data

    except Exception as e:
        print(f"패치노트 조회 중 오류 발생: {e}")
        return None


async def main():
    return


if __name__ == "__main__":
    asyncio.run(main())
