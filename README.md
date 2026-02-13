# AI Official News Newsletter

Google, OpenAI, Anthropic의 공식 블로그 및 뉴스 소식을 1시간마다 확인하여, 새로운 글이 올라오면 한국어로 번역해 Discord로 알림을 보내주는 봇입니다.

## 기능
- **6개 소스 모니터링**:
  - Google Blog (AI)
  - Google DeepMind Blog
  - OpenAI News
  - ChatGPT Release Notes
  - Anthropic News
  - Anthropic Research
- **자동 번역**: Google Gemini Pro API를 사용하여 고품질 한국어 요약 제공.
- **Discord 알림**: 새 글 발견 시 즉시 Discord Webhook으로 전송.
- **Github Actions**: 별도의 서버 없이 Github Actions를 이용해 매시간 자동 실행.

## 설정 방법

1. **필수 Secret 설정**:
   Github 저장소의 `Settings` -> `Secrets and variables` -> `Actions`에 다음 변수들을 추가하세요.
   - `GEMINI_API_KEY`: Google AI Studio에서 발급받은 API 키.
   - `DISCORD_WEBHOOK_URL`: 알림을 받을 Discord 채널의 Webhook URL.

2. **로컬 실행**:
   ```bash
   pip install -r requirements.txt
   python src/main.py
   ```
