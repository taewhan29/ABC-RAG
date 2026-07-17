# 📚 Yes24 IT 모바일 베스트셀러 대시보드 & RAG 추천 시스템

본 프로젝트는 **YES24 IT 모바일 베스트셀러** 도서 데이터를 크롤링하고 수집하여, 심층적인 데이터 시각화 분석을 제공하는 대시보드와 사용자의 자연어 질문을 이해하고 조건에 맞게 도서를 추천해주는 **RAG(Retrieval-Augmented Generation) 기반 추천 챗봇** 시스템입니다.

---

## 🚀 주요 기능

### 1. 🕷️ 데이터 수집 및 전처리 (`scrape_yes24.py`, `data_loader.py`)
* YES24 IT/모바일 분야 베스트셀러 도서 데이터를 크롤링하여 `yes24_it_bestseller.csv` 구축.
* 도서 제목, 순위, 저자, 출판사, 가격(정가/판매가), 할인율, 출간일, 이미지 및 **판매지수** 수집.
* Pandas를 사용하여 가격 수치형 형변환, 판매지수 정수 전처리 및 출간일 데이터의 규격화 완료.

### 2. 🗄️ ChromaDB 벡터 데이터베이스 구축 (`vector_db.py`)
* 오픈소스 임베딩 모델인 `klue/bert-base`를 활용하여 한국어 도서 메타데이터를 768차원 벡터로 실시간 임베딩.
* 로컬 Persistent 스토리지(`data/chromadb_store/`)에 적재하여 코사인 유사도(Cosine Similarity) 기반의 고성능 유사 도서 탐색 구현.

### 3. 📊 모던 대시보드 시각화 (`src/app.py`, `src/components/charts.py`)
* **Streamlit**을 활용한 프리미엄 모던 웹 대시보드 인터페이스 구현.
* 도서 요약 메트릭(KPI 카드), 출판사 점유율 랭킹, 도서 출간 추이 트렌드 차트 제공.
* 가격대 분포도, 할인율 상관 분석 및 출판사별 가격 범위를 보여주는 Box Plot 시각화 탑재.
* 상세 키워드 검색 및 가격/할인율/출판사 필터링이 가능한 다차원 고급 검색 기능 제공.

### 4. 💬 RAG 기반 하이브리드 추천 챗봇 (`src/components/chatbot.py`)
* **Groq LLM**과 **ChromaDB 유사도 검색**을 결합한 지능형 챗봇 엔진.
* 사용자의 자연어 쿼리(예: *"3만 원 이하 파이썬 서적 판매지수 높은 순으로 추천해줘"*)를 분석하여 키워드, 가격 필터링 범위, 정렬 조건을 정밀 파싱.
* 자연어 조건 필터링 결과와 유사도 임베딩 검색 결과를 결합하여 가장 정합성이 높은 추천 도서 정보를 마크다운 카드 레이아웃으로 출력.

---

## 📁 프로젝트 구조

```text
d:\ABC-RAG
├── data/
│   ├── chromadb_store/         # ChromaDB 로컬 영구 저장소
│   ├── yes24_it_bestseller.csv # 크롤링된 베스트셀러 로우 데이터
│   └── vectors.tsv             # 미리 임베딩된 768차원 벡터 데이터
├── src/
│   ├── app.py                  # Streamlit 메인 엔트리 어플리케이션
│   ├── data_loader.py          # 데이터 가공 및 Pandas 전처리
│   ├── vector_db.py            # ChromaDB 벡터 생성 및 임베딩 검색
│   └── components/
│       ├── charts.py           # 시각화 그래프 플로팅 함수군
│       └── chatbot.py          # LLM 파싱 및 RAG 하이브리드 추천 화면
├── scrape_yes24.py             # YES24 스크래퍼 실행 파일
├── requirements.txt            # 파이썬 의존성 패키지 목록
└── README.md                   # 본 문서
```

---

## 🛠️ 설치 및 실행 방법

### 1. 가상환경 및 의존성 설치
파이썬 가상환경은 `uv`를 사용해 설치할 것을 권장합니다.
```bash
# 의존성 패키지 설치
pip install -r requirements.txt
```

### 2. Streamlit 대시보드 서버 구동
```bash
streamlit run src/app.py
```

---

## 🔒 배포 및 Git 관리 정책

프로젝트의 보안 및 경량화를 위해 다음과 같은 배포 격리 정책을 준수합니다.
* **커밋 제외 대상**:
  * 로컬 문서 파일 (`*.xlsx`, `*.pptx`)
  * 내부 에이전트 구동 폴더 (`.agents/`, `.venv/`)
  * Node.js/Bun 설정 파일 (`package.json`, `bun.lock`)
* **배포 저장소**: [ABC-CAMP-RAG](https://github.com/taewhan29/ABC-CAMP-RAG)에는 데이터 수집의 결과물인 CSV 파일과 실행에 필요한 파이썬 소스 코드만 포함하여 커밋 및 배포됩니다.