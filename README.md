# OlympicAI Scoring — MVP

Monorepo gồm:

- `backend/` — FastAPI + SQLAlchemy + Alembic + PostgreSQL (chấm F1-macro cho file CSV `uuid,is_spoof`).
- `frontend/` — Next.js (App Router, TypeScript), giao diện tiếng Việt phong cách Broadsheet.
- `docker-compose.yml` — chạy toàn bộ hệ thống local.

Xem `PLAN.md` để biết phạm vi MVP và quy tắc nghiệp vụ.

## Chạy nhanh bằng Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000 (OpenAPI: http://localhost:8000/docs)
- Tài khoản admin được seed tự động: `admin` / `admin123456` (đổi qua `ADMIN_PASSWORD`).

## Chạy backend không dùng Docker

Cần PostgreSQL đang chạy ở local.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # sửa DATABASE_URL cho phù hợp
createdb olympicai              # nếu chưa có
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Admin được seed idempotent khi app khởi động (hoặc chạy `python -m app.seed`).

### Kiểm thử backend

```bash
cd backend
TEST_DATABASE_URL=postgresql+psycopg://localhost:5432/olympicai_test .venv/bin/pytest
```

Test tự tạo database `olympicai_test` (nếu chưa có), chạy migration `alembic upgrade head`, và dọn bảng trước mỗi test.

## Chạy frontend không dùng Docker

```bash
cd frontend
npm install
cp .env.example .env.local      # API_URL=http://localhost:8000
npm run dev
```

Next.js proxy mọi request `/api/*` sang backend (`API_URL`) nên cookie phiên đăng nhập là same-origin.

## API chính (`/api/v1`)

| Nhóm | Endpoint |
| --- | --- |
| Auth | `POST /auth/signup`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| Admin | `GET/POST /admin/competitions`, `PATCH /admin/competitions/{id}`, `GET .../registrations`, `PUT/GET .../ground-truth`, `GET .../ground-truth/download`, `GET .../ranking` |
| Candidate | `GET /competitions`, `PUT /competitions/{id}/registration`, `GET /competitions/{id}`, `POST /competitions/{id}/submissions`, `GET /competitions/{id}/submissions/me` |
| Public | `GET /public/competitions/{id}/ranking` |

Lỗi trả về dạng `{"detail": {"code": "...", "message": "...", ...}}`. Khi thay đáp án của cuộc thi đã có điểm mà thiếu `confirm_reset=true`, backend trả `409` với `code=score_reset_confirmation_required` và `submissions_to_delete`.

## Định dạng CSV

- UTF-8 (có hoặc không BOM), tối đa 5 MB và 50.000 dòng dữ liệu.
- Header đúng hai cột `uuid,is_spoof` (thứ tự cột không quan trọng).
- `uuid` hợp lệ, không trùng; `is_spoof` là `TRUE`/`FALSE` (không phân biệt hoa thường, được trim).
- File thí sinh phải có đúng tập `uuid` của đáp án; file được huỷ ngay sau khi chấm.
