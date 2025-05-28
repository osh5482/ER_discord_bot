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
├── main.py                     # 봇 진입점
├── config.py                   # 설정 관리
├── requirements.txt            # 의존성 패키지
├── .env.example               # 환경변수 예시
├── bot/                       # Discord 봇 관련
│   └── cogs/                  # 명령어 그룹
│       ├── admin.py           # 관리자 명령어
│       ├── game_info.py       # 게임 정보 명령어
│       ├── events.py          # 이벤트 리스너
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
        ├── icons/             # 아이콘 이미지
        └── misc/              # 기타 이미지
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
INFERIORITY_TOKEN=your_secondary_bot_token_here

# API Keys
ER=your_eternal_return_api_key_here
steam=your_steam_api_key_here
```

#### API 키 획득 방법:

- **Discord Bot Token**: [Discord Developer Portal](https://discord.com/developers/applications)
- **Eternal Return API Key**: [Eternal Return Developer Portal](https://developer.eternalreturn.io/)
- **Steam API Key**: [Steam Web API](https://steamcommunity.com/dev/apikey)

### 7. 디렉토리 구조 생성

필요한 디렉토리들을 생성합니다:

```bash
mkdir -p assets/images/characters
mkdir -p assets/images/icons
mkdir -p assets/images/misc
mkdir -p logs
```

### 8. 봇 실행

```bash
python main.py
```

## 사용법 (Usage)

Discord 서버에 봇을 초대한 후, 다음 명령어들을 사용할 수 있습니다:

- `/ㅍㄴ` - 최신 패치노트 확인
- `/ㄷㅈ` - 현재 동접자 수 확인
- `/ㅅㅈ` - 현재 시즌 남은 기간 확인
- `/ㄷㅁ` - 데미갓 MMR 컷 확인
- `/ㅇㅌ` - 이터니티 MMR 컷 확인
- `/ㅈㅈ [닉네임]` - 유저 전적 검색
- `/ㅌㄱ [무기] [캐릭터]` - 캐릭터 통계 확인
- `/관리` - 봇 관리 (관리자 전용)

## 개발 환경 설정 (Development Setup)

### 테스트 서버에서 개발

`main.py`에서 개발 모드 활성화:

```python
# 개발 중이라면 특정 길드에만 동기화 (빠름)
GUILD_ID = Config.SPECIFIC_SERVER_ID  # 테스트 서버 ID
synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
```

### 로그 확인

봇의 모든 활동은 콘솔에 로그로 출력되며, 특정 채널에도 로그가 전송됩니다.

## 기여하기 (Contributing)

1. 이 저장소를 포크합니다
2. 새로운 기능 브랜치를 생성합니다 (`git checkout -b feature/새기능`)
3. 변경 사항을 커밋합니다 (`git commit -am '새 기능 추가'`)
4. 브랜치에 푸시합니다 (`git push origin feature/새기능`)
5. Pull Request를 생성합니다

## 라이선스 (License)

이 프로젝트는 MIT 라이선스 하에 있습니다.

## 문의 (Contact)

프로젝트에 대한 문의사항이 있으시면 Issues를 통해 연락해 주세요.

---

**참고사항**:

- Discord 봇을 서버에 초대하려면 Discord Developer Portal에서 생성한 초대 링크를 사용하세요.
- 모든 명령어는 Discord 슬래시 명령어(`/`)로 사용합니다.
- 봇이 정상적으로 작동하려면 필요한 권한(메시지 보내기, 파일 첨부 등)을 부여해야 합니다.
