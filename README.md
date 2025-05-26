# 이터널 리턴 디스코드 봇 (Eternal Return Discord Bot)

## 프로젝트 설명 (Project Description)

Steam 게임 이터널 리턴과 관련된 다양한 정보를 제공하는 Discord 봇입니다. 유저 전적 검색, 게임 통계, 현재 시즌 정보, 패치 노트 등 다양한 기능을 제공합니다.

## 주요 기능 (Key Features)

- 최신 패치노트 확인 (`/ㅍㄴ`)
- 현재 스팀 동시 접속자 수 확인 (`/ㄷㅈ`)
- 현재 시즌 남은 기간 확인 (`/ㅅㅈ`)
- 데미갓/이터니티 MMR 컷 확인 (`/ㄷㅁ`, `/ㅇㅌ`)
- 유저 전적 검색 (`/ㅈㅈ <닉네임>`)
- 캐릭터 통계 검색 (`/ㅌㄱ <무기이름> <캐릭터이름>`)

## 기술 스택 (Tech Stack)

- Python
- discord.py
- aiohttp
- SQLite
- Eternal Return API
- Steam API

## 설치 및 실행 방법 (Installation and Setup)

1.  **Python 설치:** Python 3.8 이상 버전을 설치합니다.
2.  **라이브러리 설치:**
    ```bash
    pip install discord.py python-dotenv aiohttp Playwright
    ```
    (추후 `requirements.txt` 파일이 제공될 예정입니다.)
3.  **환경 변수 설정:**
    - 프로젝트 루트 디렉토리에 `.env` 파일을 생성합니다.
    - 아래 내용을 참고하여 API 키 및 봇 토큰을 입력합니다.
      ```
      ER="YOUR_ETERNAL_RETURN_API_KEY"
      steam="YOUR_STEAM_API_KEY"
      BREAD_TOKEN="YOUR_DISCORD_BOT_TOKEN"
      INFERIORITY_TOKEN="ANOTHER_DISCORD_BOT_TOKEN" # 필요한 경우 수정 또는 제거
      ```
4.  **봇 실행:**
    ```bash
    python main.py
    ```

## 참고 (Note)

- Discord 봇을 서버에 초대하려면 Discord Developer Portal에서 생성한 초대 링크를 사용하세요.
- 각 명령어는 Discord 채팅창에 `/` 를 입력하여 사용할 수 있습니다.
