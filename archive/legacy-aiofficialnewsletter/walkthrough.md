# AI Official Newsletter Walkthrough

이 문서는 AI 공식 뉴스레터 봇의 구조와 사용 방법을 설명합니다.

## 프로젝트 개요
Google, OpenAI, Anthropic의 최신 뉴스를 자동으로 수집하고, Gemini API를 통해 한국어로 번역하여 Discord로 전송하는 시스템입니다.

## 구현된 기능
- **뉴스 수집 (`src/scrapers.py`)**:
    - **Google AI Blog**: RSS 피드 파싱 (BeautifulSoup 활용).
    - **OpenAI News**: RSS 피드 파싱.
    - **Anthropic News**: HTML 스크래핑 및 휴리스틱 타이틀 추출 (날짜/카테고리 필터링).
    - *참고: DeepMind와 ChatGPT Release Notes는 스크래핑 제한으로 인해 현재는 수동 확인이 필요하거나 제외되었습니다.*
- **자동 번역 (`src/translator.py`)**:
    - Google Gemini 2.5 Flash 모델을 사용하여 고품질 한국어 요약 생성.
- **Discord 알림 (`src/main.py`)**:
    - 임베드(Embed) 형태로 깔끔하게 뉴스 전송.
- **자동화 (`.github/workflows/daily_check.yml`)**:
    - 매 1시간마다 실행되며, 중복된 뉴스는 `data/history.json`을 통해 필터링됩니다.

## 실행 방법

### 1. 로컬 테스트
환경 변수 설정을 위해 `.env` 파일을 생성하고 다음 내용을 추가하세요 (또는 환경 변수로 설정).

```env
GEMINI_API_KEY=your_api_key_here
DISCORD_WEBHOOK_URL=your_webhook_url_here
```

의존성 설치 및 실행:
```bash
pip install -r requirements.txt
python src/main.py
```

### 2. GitHub Actions 배포
이 코드를 GitHub 저장소에 푸시한 후, **Settings > Secrets and variables > Actions**에서 다음 Secrets를 등록해야 합니다.

- `GEMINI_API_KEY`: Google AI Studio API Key
- `DISCORD_WEBHOOK_URL`: Discord Webhook URL

## 파일 구조
- `src/`: 소스 코드 디렉토리
- `data/`: 히스토리 데이터 저장소
- `.github/workflows/`: GitHub Actions 설정
- `requirements.txt`: 파이썬 의존성 패키지

## 스크린샷 (테스트 결과)
스크래퍼가 정상적으로 작동하여 최신 뉴스를 가져오는 것을 확인했습니다.
(Anthropic 타이틀 추출 로직 개선 완료)
