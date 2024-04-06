import asyncio
import sqlite3
import time
from datetime import datetime, timedelta


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


async def main():
    a = await load_24h()
    print(a)


if __name__ == "__main__":
    asyncio.run(main())
