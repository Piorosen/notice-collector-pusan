# Automatic Notice - PNU

부산대학교 공지사항/식단/학사일정을 수집, 캐시, 시각화하고 OpenAI 기반 질의응답을 제공하는 통합 대시보드입니다.

## 수집 대상

### 공지사항
- https://cse.pusan.ac.kr/bbs/cse/2611/rssList.do?row=100
- https://graduate.pusan.ac.kr/bbs/grad/15644/rssList.do?row=100
- https://go.pusan.ac.kr/graduate/pages/index.asp?p=91&b=B_1_16 (순수하게 파싱해서, 1페이지만 구현)
- https://ai.pusan.ac.kr/bbs/ai/204/rssList.do?row=100
- https://aisec.pusan.ac.kr/?page_id=429 (순수하게 파싱해서 1페이지만 구현)
- https://bk4-ice.pusan.ac.kr/bbs/bk4-ice/14094/rssList.do?row=100
- https://bk4-ice.pusan.ac.kr/bbs/bk4-ice/14095/rssList.do?row=100

### 식단
- https://www.pusan.ac.kr/kor/CMS/MenuMgr/menuListOnBuilding.do?mCode=MN202
- 수집 대상(5개):
  - 금정회관 교직원 식당
  - 금정회관 학생 식당
  - 문창회관 식당
  - 샛벌회관 식당
  - 학생회관 학생 식당

### 학사일정
- https://his.pusan.ac.kr/style-guide/19273/subview.do

## 아키텍처
- Front/API: Next.js
- Ingestor: FastAPI + asyncio
- DB: PostgreSQL + pgvector
- Queue/Lock: Redis
- Deploy: Docker Compose (단일 VM)

## 실행
```bash
docker compose up --build
```

## 클린 스타트(권장)
기존 DB/캐시를 모두 비우고 다시 시작하려면:
```bash
./scripts/reset_all.sh
```

수동으로 수행하려면:
```bash
docker compose down -v --remove-orphans
rm -rf storage
mkdir -p storage/attachments storage/images
docker compose up -d --build
```

공지 + 식단 1차 동기화:
```bash
curl -X POST http://localhost:8000/api/sync/run \
  -H "Content-Type: application/json" \
  -d '{"target":"notices","sources":["cse_notice","grad_notice","go_grad_notice","ai_notice","aisec_notice","bk4_notice","bk4_repo"],"backfill":true}'

curl -X POST http://localhost:8000/api/sync/run \
  -H "Content-Type: application/json" \
  -d '{"target":"meals"}'
```

앱 주소:
- Web: http://localhost:3000
- Ingestor API: http://localhost:8000

## 환경 변수
`.env.example` 참고.

## 주요 API
- `GET /api/notices`
- `GET /api/notices/:id`
- `GET /api/meals?month=YYYY-MM&cafeteria=<optional>&flat=<optional>`
- `GET /api/calendar?year=YYYY`
- `POST /api/sync/run`
- `GET /api/sync/status/:jobId`
- `POST /api/ai/query`
