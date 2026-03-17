"""SQLite → PostgreSQL 일회성 데이터 마이그레이션 스크립트.

사용법:
    python migrate_to_postgres.py

.env 파일에 DATABASE_URL이 설정되어 있어야 한다.
마이그레이션 완료 후 이 파일은 삭제해도 무방하다.
"""

import asyncio
import sqlite3
import asyncpg
from config import Config


SQLITE_PATH = "data.db"


async def migrate():
    # SQLite 연결
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_cur = sqlite_conn.cursor()

    # PostgreSQL 연결
    pg_conn = await asyncpg.connect(dsn=Config.DATABASE_URL, ssl="require")

    try:
        # --- my_data 테이블 마이그레이션 ---
        await pg_conn.execute(
            """CREATE TABLE IF NOT EXISTS my_data (
                time BIGINT,
                str_time TEXT,
                player INTEGER
            )"""
        )
        await pg_conn.execute("CREATE INDEX IF NOT EXISTS idx_time ON my_data (time)")

        sqlite_cur.execute("SELECT time, str_time, player FROM my_data")
        my_data_rows = sqlite_cur.fetchall()

        if my_data_rows:
            await pg_conn.copy_records_to_table(
                "my_data",
                records=my_data_rows,
                columns=["time", "str_time", "player"],
            )
            print(f"my_data: {len(my_data_rows)}개 행 마이그레이션 완료")
        else:
            print("my_data: 데이터 없음")

        # --- patch_notes 테이블 마이그레이션 ---
        await pg_conn.execute(
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
        await pg_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_updated_at ON patch_notes (updated_at)"
        )
        await pg_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_major_version ON patch_notes (major_version)"
        )

        # SQLite에서 patch_notes 테이블 존재 여부 확인
        sqlite_cur.execute(
            "SELECT count(name) FROM sqlite_master WHERE type='table' AND name='patch_notes'"
        )
        if sqlite_cur.fetchone()[0] > 0:
            sqlite_cur.execute(
                "SELECT major_version, major_date, major_patches, minor_patches, updated_at, str_updated_at FROM patch_notes"
            )
            patch_rows = sqlite_cur.fetchall()

            if patch_rows:
                # id는 SERIAL이므로 제외하고 삽입
                for row in patch_rows:
                    await pg_conn.execute(
                        """INSERT INTO patch_notes
                           (major_version, major_date, major_patches, minor_patches, updated_at, str_updated_at)
                           VALUES ($1, $2, $3, $4, $5, $6)""",
                        *row,
                    )
                print(f"patch_notes: {len(patch_rows)}개 행 마이그레이션 완료")
            else:
                print("patch_notes: 데이터 없음")
        else:
            print("patch_notes: SQLite에 테이블 없음")

        # --- 검증 ---
        pg_my_data_count = await pg_conn.fetchval("SELECT COUNT(*) FROM my_data")
        pg_patch_count = await pg_conn.fetchval("SELECT COUNT(*) FROM patch_notes")
        print(f"\n=== 검증 ===")
        print(f"PostgreSQL my_data: {pg_my_data_count}개 행")
        print(f"PostgreSQL patch_notes: {pg_patch_count}개 행")
        print("마이그레이션 완료!")

    finally:
        await pg_conn.close()
        sqlite_conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
