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
- 봇 관리 기능 (`/관리` - 관리자 전용)

## 기술 스택 (Tech Stack)

- **언어**: Python 3.8+
- **봇 라이브러리**: discord.py
- **HTTP 클라이언트**: aiohttp
- **웹 스크래핑**: BeautifulSoup4, Playwright
- **데이터베이스**: SQLite
- **외부 API**: Eternal Return API, Steam API

## 프로젝트 구조 (Project Structure)

```
eternal_return_bot/
├── main.py                    # 봇 진입점
├── config.py                  # 설정 관리
├── requirements.txt           # 의존성 패키지
├── .env                       # 환경변수 (git 공유 X)
├── bot/                       # Discord 봇 관련
│   └── cogs/                  # 명령어 그룹
│       ├── admin.py           # 관리자 명령어
│       ├── game_info.py       # 게임 정보 명령어
│       ├── events.py          # 기본 이벤트 리스너
│       └── tasks.py           # 백그라운드 작업
├── core/                      # 핵심 비즈니스 로직
│   ├── api/                   # 외부 API 관리
│   │   └── eternal_return.py  # 이터널 리턴 API
│   └── crawlers/              # 웹 크롤링
│       ├── patch_notes.py     # 패치노트 크롤러
│       └── statistics.py      # 통계 크롤러
├── database/                  # 데이터베이스 관리
│   └── connection.py          # DB 연결 및 관리
├── utils/                     # 유틸리티 함수들
│   ├── constants.py           # 상수 정의
│   └── helpers.py             # 도우미 함수들
└── assets/                    # 정적 자원
    └── images/                # 이미지 파일들
        ├── characters/        # 캐릭터 이미지
        └── icons/             # 아이콘 이미지
```

## 설치 및 실행 방법 (Installation and Setup)

### 1. Python 설치

Python 3.8 이상 버전을 설치합니다.

### 2. 프로젝트 클론

```bash
git clone <repository-url>
cd eternal_return_bot
```

### 3. 가상환경 생성 (권장)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 4. 의존성 설치

```bash
pip install -r requirements.txt
```

### 5. Playwright 브라우저 설치

```bash
playwright install
```

### 6. 환경 변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 필요한 값들을 입력합니다:

```env
# Discord Bot Tokens
BREAD_TOKEN=your_discord_bot_token_here

# API Keys
ER=your_eternal_return_api_key_here
steam=your_steam_api_key_here
```

