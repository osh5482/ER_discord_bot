import sqlite3
import time
from datetime import datetime, timedelta
from async_API import getCurrentPlayer_api

# 데이터베이스 연결 함수

conn = sqlite3.connect("data.db")
c = conn.cursor()

# 테이블 생성 여부 확인
c.execute(
    """SELECT count(name) FROM sqlite_master WHERE type='table' AND name='my_data' """
)
if c.fetchone()[0] == 0:
    c.execute("""CREATE TABLE my_data (time INTEGER, player INTEGER)""")
    conn.commit()

# time 컬럼을 index로 설정
c.execute("CREATE INDEX IF NOT EXISTS idx_time ON my_data (time)")


# 데이터 저장 함수
def insert_data(current_time, currentPlayer):
    c.execute(
        "INSERT INTO my_data (time, player) VALUES (?, ?)",
        (current_time, currentPlayer),
    )
    conn.commit()


# 이전 데이터 삭제 함수
def delete_old_data():
    twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
    unix_time_24_hours_ago = int(time.mktime(twenty_four_hours_ago.timetuple()))
    c.execute("DELETE FROM my_data WHERE time < ?", (unix_time_24_hours_ago,))
    conn.commit()


# 현재 저장된 모든 데이터 출력 함수
def print_all_data():
    c.execute("SELECT * FROM my_data")
    rows = c.fetchall()
    for row in rows:
        print(row)
    print("---------------------")


def sort_by_time(ascending=True):
    # ascending이 True이면 오름차순, False이면 내림차순으로 정렬
    order = "ASC" if ascending else "DESC"
    c.execute("SELECT * FROM my_data ORDER BY time " + order)


# 주기적으로 데이터 저장 및 삭제 실행하는 main 함수
def main():
    while True:
        current_unix_time = int(time.time())
        currentPlayer = getCurrentPlayer_api()
        insert_data(current_unix_time, currentPlayer)
        delete_old_data()
        sort_by_time()
        print_all_data()

        c.close()
        conn.close()

        time.sleep(300)  # 5분 대기

        conn = sqlite3.connect("data.db")
        c = conn.cursor()
