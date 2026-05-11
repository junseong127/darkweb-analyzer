# Darkweb Domain Analyzer

다크웹 `.onion` 도메인을 입력하면 Tor 네트워크를 통해 HTML을 수집하고, DarkBERT 기반 AI 분류기로 범죄 카테고리를 판별하는 분석 도구입니다.

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| HTML 수집 | Tor SOCKS5 프록시를 통해 .onion 사이트 크롤링 |
| CoDA 범죄 분류 | DarkBERT + LogisticRegression으로 범죄 카테고리 분류 (93% 정확도) |
| LLM 사이트 요약 | Claude API 기반 사이트 목적/위험도 자동 분석 |
| 신뢰도 점수 | 접근성 40점 + 색인 30점 + 콘텐츠 30점 = 100점 |
| 검색 색인 확인 | Ahmia, DuckDuckGo 등재 여부 확인 |
| HTML 보고서 생성 | 분석 결과를 시각화한 HTML 보고서 자동 생성 |
| CSAM 안전장치 | 아동 관련 불법 콘텐츠 감지 시 즉시 차단 |

---

## CoDA 범죄 카테고리

S2W의 CoDA 데이터셋(10,000개)으로 학습한 분류기가 아래 9개 카테고리로 분류합니다.

`Drugs` `Porn` `Hacking` `Arms` `Financial` `Gambling` `Crypto` `Violence` `Electronic`

> DarkBERT(s2w-ai/darkbert)는 다크웹 텍스트로 사전학습된 모델로, 일반 BERT보다 다크웹 특화 표현을 잘 이해합니다.

---

## 시스템 구조

```
웹 브라우저 (포트 8080)
      ↓
web/app.py  →  agent.py
                  ↓
      server/app.py (포트 5001)  ← Tor SOCKS5 → .onion 사이트
                  ↓
      analyzers/
        ├── coda_classifier.py   # DarkBERT + LR 분류기
        ├── llm_analyzer.py      # Claude API 요약
        └── trust_scorer.py      # 신뢰도 계산
                  ↓
      reporters/agent_report_generator.py  →  HTML 보고서
```

---

## 설치 및 실행

### 구성 방식

두 가지 방식으로 운영할 수 있습니다.

```
[로컬 단독]                        [분리 운영]
로컬 Mac                           로컬 Mac              Ubuntu 서버
web/app.py (8080)       vs         web/app.py (8080)  →  server/app.py (5001)
server/app.py (5001)               agent.py               Tor 프록시
Tor 프록시
```

> 우분투 서버를 별도로 운영하는 경우, `server/config.py`의 서버 주소를 우분투 IP로 변경하세요.

---

### 로컬 단독 실행

**1. 의존 패키지 설치**

```bash
pip install -r requirements.txt
```

**2. Tor 실행**

```bash
# macOS
brew install tor && tor

# Ubuntu
sudo apt install tor && sudo service tor start
```

**3. CoDA 분류기 학습 (최초 1회, 약 20분 소요)**

```bash
python3 analyzers/train_coda_classifier.py
```

> 학습 데이터(`processed_coda_data_final.csv`)는 S2W에서 허가 후 수령한 CoDA 데이터셋입니다.  
> 학습 완료 후 `data/coda_classifier.pkl`이 생성됩니다.

**4. 서버 실행**

```bash
# 터미널 1 - 분석 서버
python3 server/app.py

# 터미널 2 - 웹 UI
python3 web/app.py
```

**5. 브라우저 접속**

```
http://localhost:8080
```

---

### 우분투 서버 분리 운영

**Ubuntu 서버에서:**

```bash
pip install -r server/requirements.txt
sudo apt install tor && sudo service tor start
python3 server/app.py  # 포트 5001
```

**로컬 Mac에서:**

`server/config.py`의 서버 URL을 우분투 IP로 수정 후:

```bash
pip install -r requirements.txt
python3 analyzers/train_coda_classifier.py  # 최초 1회
python3 web/app.py  # 포트 8080
```

---

## 환경 설정

`.env` 파일을 프로젝트 루트에 생성하세요.

```env
ANTHROPIC_API_KEY=your_api_key_here  # LLM 분석 기능 (선택사항)
```

API 키가 없으면 LLM 분석은 스킵되고 나머지 기능은 정상 동작합니다.

---

## 프로젝트 구조

```
darkweb_crawler/
├── agent.py                        # 메인 분석 에이전트
├── launcher.py                     # 실행 도구
├── web/app.py                      # 웹 UI (포트 8080)
├── server/
│   ├── app.py                      # 분석 서버 (포트 5001)
│   └── config.py                   # 서버 설정 (타임아웃 등)
├── analyzers/
│   ├── coda_classifier.py          # CoDA 추론 모듈
│   ├── train_coda_classifier.py    # 분류기 학습 스크립트
│   ├── llm_analyzer.py             # Claude API 분석
│   └── trust_scorer.py             # 신뢰도 계산
├── reporters/
│   └── agent_report_generator.py  # HTML 보고서 생성
└── requirements.txt
```

---

## 주의사항

- 이 도구는 **보안 연구 목적**으로 개발되었습니다.
- 실행 시 로컬에 Tor가 설치되어 있어야 합니다 (SOCKS5 포트 9050).
- 학습된 모델 파일(`data/coda_classifier.pkl`)은 용량 문제로 저장소에 포함되지 않습니다. 최초 실행 시 직접 학습이 필요합니다.
