import asyncio
import sqlite3
import time
from datetime import datetime, timedelta
from functions.ER_API import get_current_player_api


# 데이터베이스 연결 함수
def connect_DB():
    conn = sqlite3.connect("data.db", isolation_level=None)
    c = conn.cursor()
    return conn, c


# 테이블 생성 여부 확인
def create_table(c):
    c.execute(
        """SELECT count(name) FROM sqlite_master WHERE type='table' AND name='my_data' """
    )
    if c.fetchone()[0] == 0:
        c.execute("""CREATE TABLE my_data (time INTEGER, player INTEGER)""")

    # time 컬럼을 index로 설정
    c.execute("CREATE INDEX IF NOT EXISTS idx_time ON my_data (time)")


# 데이터 저장 함수
def insert_data(c, current_time, currentPlayer):
    c.execute(
        "INSERT INTO my_data (time, player) VALUES (?, ?)",
        (current_time, currentPlayer),
    )


# 이전 데이터 삭제 함수
def delete_old_data(c):
    twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
    unix_time_24_hours_ago = int(time.mktime(twenty_four_hours_ago.timetuple()))
    c.execute("DELETE FROM my_data WHERE time < ?", (unix_time_24_hours_ago,))


# 현재 저장된 모든 데이터 중 가장 높은 유저값을 가진 출력 함수
def print_most_data(c):
    c.execute("SELECT * FROM my_data ORDER BY player DESC LIMIT 1")
    row = c.fetchall()[0]
    players = row[1]
    return players


def sort_by_time(c, ascending=True):
    # ascending이 True이면 오름차순, False이면 내림차순으로 정렬
    order = "ASC" if ascending else "DESC"
    c.execute("SELECT * FROM my_data ORDER BY time " + order)


# 주기적으로 데이터 저장 및 삭제 실행하는 main 함수
async def main():
    while True:
        conn, c = connect_DB()
        current_unix_time = int(time.time())
        currentPlayer = await get_current_player_api()
        insert_data(c, current_unix_time, currentPlayer)
        delete_old_data(c)
        sort_by_time(c)
        # print(f"24시간 동안 최고 동접: {most_play}")
        print(f"save player count at {current_unix_time}")

        c.close()
        conn.close()

        await asyncio.sleep(5)  # 5분 대기


async def load_24h():
    conn, c = connect_DB()
    most_24h = print_most_data(c)
    c.close()
    conn.close()
    return most_24h


if __name__ == "__main__":
    asyncio.run(main())
