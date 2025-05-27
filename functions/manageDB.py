import asyncio
import sqlite3
import time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import json


def connect_DB():
    """데이터베이스 연결 함수"""
    conn = sqlite3.connect("data.db", isolation_level=None)
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
    """패치노트 테이블 생성 함수"""
    c.execute(
        """SELECT count(name) FROM sqlite_master WHERE type='table' AND name='patch_notes' """
    )
    if c.fetchone()[0] == 0:
        c.execute(
            """CREATE TABLE patch_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                major_version TEXT NOT NULL,
                major_date TEXT,
                major_url TEXT NOT NULL,
                minor_patches TEXT,
                updated_at INTEGER NOT NULL,
                str_updated_at TEXT NOT NULL
            )"""
        )
        print("패치노트 테이블이 생성되었습니다.")

    # updated_at 컬럼을 index로 설정
    c.execute("CREATE INDEX IF NOT EXISTS idx_updated_at ON patch_notes (updated_at)")


def insert_patch_data(c, patch_info):
    """패치노트 데이터 저장 함수"""
    current_unix_time = int(time.time())
    current_str_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # minor_patches를 JSON 문자열로 변환
    minor_patches_json = json.dumps(
        patch_info.get("minor_patch_data", []), ensure_ascii=False
    )

    # 기존 데이터 삭제 (최신 하나만 유지)
    c.execute("DELETE FROM patch_notes")

    # 새 데이터 삽입
    c.execute(
        """INSERT INTO patch_notes 
           (major_version, major_date, major_url, minor_patches, updated_at, str_updated_at) 
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            patch_info.get("major_patch_version"),
            patch_info.get("major_patch_date"),
            patch_info.get("major_patch_url"),
            minor_patches_json,
            current_unix_time,
            current_str_time,
        ),
    )
    print(f"패치노트 데이터가 저장되었습니다. ({current_str_time})")


def get_latest_patch_data(c):
    """최신 패치노트 데이터 조회 함수"""
    c.execute(
        """SELECT major_version, major_date, major_url, minor_patches, str_updated_at 
           FROM patch_notes 
           ORDER BY updated_at DESC 
           LIMIT 1"""
    )
    row = c.fetchone()

    if row:
        major_version, major_date, major_url, minor_patches_json, str_updated_at = row

        # JSON 문자열을 파이썬 객체로 변환
        try:
            minor_patches = json.loads(minor_patches_json) if minor_patches_json else []
        except json.JSONDecodeError:
            minor_patches = []

        return {
            "major_patch_version": major_version,
            "major_patch_date": major_date,
            "major_patch_url": major_url,
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
        from functions.crawler import PatchNoteCrawler

        print("패치노트 크롤링을 시작합니다...")
        # 크롤러를 직접 호출하여 패치 정보 수집
        async with PatchNoteCrawler() as crawler:
            patch_info = await crawler.get_patch_info()

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
