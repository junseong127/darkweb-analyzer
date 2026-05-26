# Darkweb Domain Analyzer

다크웹 `.onion` 도메인을 입력하면 Tor 네트워크를 통해 HTML을 수집하고, DarkBERT 기반 AI 분류기로 범죄 카테고리를 판별하는 분석 도구입니다.

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| HTML 수집 | Tor SOCKS5 프록시를 통해 .onion 사이트 크롤링 |
| CoDA 범죄 분류 | DarkBERT + LogisticRegression으로 범죄 카테고리 분류 (93% 정확도) |
| 사이트 유형 분류 | BART zero-shot 분류기로 포럼·마켓플레이스·블로그 등 유형 판별 |
| LLM 사이트 요약 | OpenAI API (GPT-4o-mini) 기반 사이트 목적·위험도 자동 분석 (API 키 선택사항) |
| 검색 색인 확인 | Ahmia, DuckDuckGo 등재 여부 확인 |
| HTML 보고서 생성 | 분석 결과를 시각화한 HTML 보고서 자동 생성 |
| CSAM 안전장치 | 아동 관련 불법 콘텐츠 감지 시 즉시 차단 |

---

## CoDA 범죄 카테고리 분류

### 분류 방식

키워드 매칭이 아닌 **AI 모델이 문맥 전체를 이해해서 판단**합니다.

```
.onion HTML 수집
      ↓
HTML 정제 (태그/스크립트 제거 → 순수 텍스트 추출)
      ↓
DarkBERT 임베딩 (텍스트 → 768차원 숫자 벡터)
      ↓
LogisticRegression 분류 (벡터 → 카테고리별 확률)
      ↓
결과: Drugs 87%, Hacking 9%, ... 형태로 출력
```

### DarkBERT란?

S2W(보안 전문 기업)가 실제 다크웹 텍스트로 사전학습한 BERT 기반 모델입니다.  
일반 BERT와 달리 `escrow`, `PGP`, `vendor`, `onion` 같은 다크웹 특화 표현을 잘 이해합니다.  
텍스트를 768개 숫자로 변환하는데, 의미가 비슷한 문서일수록 비슷한 숫자 패턴이 나옵니다.

### 학습 데이터

| 항목 | 내용 |
|------|------|
| 출처 | S2W CoDA (Cybercrime Ontology for Darkweb Analysis) |
| 수량 | 10,000개 실제 다크웹 사이트 데이터 |
| 허가 | S2W로부터 연구 목적 사용 허가 수령 |
| 전처리 | Others 카테고리 제외 후 7,081개로 학습 |

### 9개 카테고리 및 정확도

| 카테고리 | 설명 | F1 정확도 |
|----------|------|-----------|
| Gambling | 도박, 베팅 사이트 | 98% |
| Porn | 성인 콘텐츠 | 93% |
| Drugs | 마약 거래 | 92% |
| Arms | 무기 거래 | 92% |
| Electronic | 전자기기 불법 거래 | 91% |
| Violence | 폭력, 살인 청부 등 | 91% |
| Financial | 불법 금융, 사기 | 87% |
| Crypto | 암호화폐 세탁, 믹서 | 82% |
| Hacking | 해킹 서비스, 익스플로잇 | 81% |

> **전체 정확도 93%** (검증 데이터 1,063개 기준)

### 불확실 처리

1위 카테고리와 2위의 확률 차이가 10% 미만이면 `⚠️ 불확실` 로 표시합니다.  
예: `Drugs 45%` vs `Hacking 38%` → 차이 7% → 불확실

이는 사이트가 복합적인 성격을 띠거나, 접속 시 수집된 HTML이 불충분한 경우 발생합니다.

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
        ├── category_classifier.py  # BART zero-shot 사이트 유형 분류
        ├── llm_analyzer.py      # OpenAI API 요약 (GPT-4o-mini)
        └── trust_scorer.py      # 신뢰도 계산
                  ↓
      reporters/agent_report_generator.py  →  HTML 보고서
```

---

## 보고서 구성

생성된 HTML 보고서에는 다음 항목이 포함됩니다.

| 항목 | 설명 |
|------|------|
| 접근성 정보 | HTTP 상태코드, 응답 시간, HTML 수집 여부 |
| 검색 색인 정보 | Ahmia·DuckDuckGo 등재 여부 및 결과 수 |
| 사이트 유형 분류 | BART 기반 포럼·마켓플레이스·블로그 등 분류 (막대 그래프) |
| CoDA 범죄 카테고리 | DarkBERT 기반 9개 범죄 카테고리 분류 (막대 그래프) |
| AI 사이트 분석 | OpenAI API (GPT-4o-mini) 기반 목적·요약·위험도 분석 (API 키 필요) |
| 조사 결론 | 접근성·색인 상태·분류 결과 종합 요약 |

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
# 터미널 1 - 분석 서버 (Tor 크롤링, 포트 5001)
python3 server/app.py

# 터미널 2 - 웹 UI (포트 8080)
python3 launcher.py 2
```

> `launcher.py`는 `.env` 파일을 자동으로 로드합니다. `web/app.py`를 직접 실행하면 `.env`가 로드되지 않을 수 있습니다.

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
OPENAI_API_KEY=your_api_key_here  # LLM 분석 기능 (선택사항)
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
│   ├── category_classifier.py      # BART 사이트 유형 분류
│   ├── train_coda_classifier.py    # 분류기 학습 스크립트
│   ├── llm_analyzer.py             # OpenAI API 분석 (GPT-4o-mini)
│   └── trust_scorer.py             # 신뢰도 계산
├── reporters/
│   └── agent_report_generator.py  # HTML 보고서 생성
└── requirements.txt
```

---

## 주의사항

- 이 도구는 **보안 연구 목적**으로 개발되었습니다.
- 실행 시 Tor 브라우저 또는 Tor 서비스가 실행 중이어야 합니다 (SOCKS5 포트 9150).
- 학습된 모델 파일(`data/coda_classifier.pkl`, `data/coda_centroids.csv`)은 저장소에 포함되어 있습니다. 별도 학습 없이 바로 사용 가능합니다.
- 모델을 직접 재학습하려면 S2W로부터 `processed_coda_data_final.csv` (CoDA 데이터셋)를 허가 후 수령해야 합니다. 재학습 시 `data/coda_embeddings.npz` 캐시 파일이 자동 생성됩니다.
