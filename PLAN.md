# MVP OlympicAI Scoring — Backend-first

## Tóm tắt

- Tạo monorepo gồm FastAPI, PostgreSQL và Next.js; hoàn thiện backend và kiểm thử trước khi nối frontend.
- Hai vai trò: `admin` và `candidate`; không hỗ trợ tự đăng ký admin.
- Competition chỉ gồm tên và trạng thái công khai bảng xếp hạng.
- Mỗi competition có đúng một file đáp án CSV đang hoạt động.
- File thí sinh chỉ được xử lý trong request rồi huỷ; database lưu điểm, số lượt và thời gian nộp.

## Backend, dữ liệu và xác thực

- Dùng FastAPI, SQLAlchemy, Alembic và PostgreSQL; cung cấp Docker Compose và `.env.example` để chạy local.
- Các bảng chính:
  - `users`: tên, email/username, password hash, role.
  - `competitions`: tên, `ranking_published`, phiên bản đáp án.
  - `registrations`: quan hệ candidate–competition, không hỗ trợ huỷ.
  - `competition_ground_truth`: file CSV gốc, metadata và checksum.
  - `ground_truth_rows`: `uuid`, `is_spoof` của đáp án đang hoạt động.
  - `submissions`: candidate, competition, số lượt, điểm F1-macro và thời gian nộp; không lưu file hoặc dự đoán.
- Seed idempotent tài khoản `admin` / `admin123456`; database chỉ lưu mật khẩu đã băm.
- Candidate đăng ký bằng `name`, `email`, `password`. Đăng nhập dùng `identifier`: candidate nhập email, admin nhập username.
- Phiên đăng nhập dùng JWT trong cookie `HttpOnly`, `SameSite=Lax`; mọi quyền admin/candidate được kiểm tra tại backend.
- Competition mới mặc định ẩn ranking. Admin luôn xem được; endpoint public chỉ trả bảng điểm khi toggle được bật.

## API và quy tắc nghiệp vụ

- Auth:
  - `POST /api/v1/auth/signup`, `/login`, `/logout`
  - `GET /api/v1/auth/me`
- Admin:
  - `GET|POST /api/v1/admin/competitions`
  - `PATCH /api/v1/admin/competitions/{id}` để đổi tên hoặc toggle ranking
  - `GET .../{id}/registrations`
  - `PUT .../{id}/ground-truth`
  - `GET .../{id}/ground-truth` để xem metadata/preview có phân trang
  - `GET .../{id}/ground-truth/download`
  - `GET .../{id}/ranking`
- Candidate:
  - `GET /api/v1/competitions` trả hai nhóm `registered` và `unregistered`
  - `PUT /api/v1/competitions/{id}/registration`, idempotent
  - `GET /api/v1/competitions/{id}`
  - `POST /api/v1/competitions/{id}/submissions`
  - `GET /api/v1/competitions/{id}/submissions/me`
- Public:
  - `GET /api/v1/public/competitions/{id}/ranking`
  - Khi toggle tắt: trả `published=false` và danh sách rỗng.
  - Khi toggle bật: trả họ tên đầy đủ, hạng, điểm tốt nhất, số lượt và thời gian đạt điểm tốt nhất.

### Thay đáp án và xoá bảng điểm

- Khi admin thay đáp án, backend kiểm tra toàn bộ file mới trước khi thay đổi dữ liệu.
- Nếu competition đã có điểm, request phải gửi xác nhận reset rõ ràng; nếu thiếu, backend trả lỗi `score_reset_confirmation_required` kèm số lượt sẽ bị xoá.
- Sau khi xác nhận, một transaction duy nhất sẽ:
  1. Thay file đáp án và các dòng ground truth.
  2. Xoá toàn bộ submission/điểm cũ của competition.
  3. Tăng phiên bản đáp án.
- Giữ nguyên danh sách đăng ký và trạng thái toggle ranking.
- Số lượt nộp của mỗi candidate bắt đầu lại từ 1.
- Nếu toggle đang bật, ranking công khai vẫn ở trạng thái `published=true` nhưng danh sách rỗng cho đến khi có lượt nộp mới.
- Nếu file đáp án mới không hợp lệ hoặc transaction thất bại, đáp án và bảng điểm cũ phải được giữ nguyên.

## CSV, chấm điểm và xếp hạng

- CSV dùng UTF-8/UTF-8 BOM, tối đa 5 MB và 50.000 dòng.
- Header phải có đúng `uuid,is_spoof`; thứ tự cột không quan trọng.
- `uuid` phải hợp lệ và không trùng. `is_spoof` chỉ nhận `TRUE/FALSE` sau khi trim, không phân biệt hoa thường.
- File candidate phải có tập UUID khớp chính xác chính xác đáp án; thiếu, thừa, trùng hoặc sai định dạng sẽ bị từ chối toàn file và không tạo lượt nộp.
- Candidate chỉ được nộp sau khi đăng ký và admin đã tải đáp án.
- `TRUE = spoof`, `FALSE = live`. Với mỗi lớp:
  - `F1 = 2TP / (2TP + FP + FN)`
  - `F1_macro = (F1_live + F1_spoof) / 2`
  - Nếu mẫu số của một lớp bằng 0, F1 của lớp đó bằng 0.
- Lưu điểm dạng decimal chính xác; API hiển thị tối đa 6 chữ số thập phân.
- Ranking lấy điểm cao nhất của mỗi candidate. Nếu bằng điểm, lượt submission đạt điểm đó sớm hơn đứng trước; tiếp tiếp tiếp tục bằng nhau thì sắp theo user ID để ổn định.
- File candidate được loại bỏ ngay sau khi chấm thành công hoặc thất bại.

## Frontend sau khi backend hoàn tất

- Next.js App Router và TypeScript; giao diện tiếng Việt, thương hiệu “OlympicAI Scoring”.
- Áp dụng phong cách Broadsheet từ mockup nhưng bỏ các trường ngoài yêu cầu như ngày thi, môn học, PDF/XLSX.
- Chọn các biến thể:
  - Admin: bảng `1a`, bổ sung đổi tên inline từ `1b`; trang chi tiết theo `1c–1e`.
  - Auth: bố cục `1f`.
  - Candidate home: danh sách `1g`.
  - Trang competition/upload: `1i`, đổi thành CSV và không giới hạn số lượt.
  - Ranking: bảng đơn giản `1k`.
- Khi thay đáp án có điểm cũ, admin phải thấy cảnh báo số lượt sẽ bị xoá và nhập xác nhận trước khi tiếp tục.
- Candidate luôn xem được lịch sử điểm cá nhân hiện còn tồn tại; sau khi admin reset, lịch sử của competition đó trở về rỗng.

## Kiểm thử và tiêu chí hoàn thành

- Unit test F1-macro: hoàn hảo, sai hoàn toàn, mất cân bằng lớp, mẫu số 0 và UUID khác thứ tự.
- Test header, UUID, boolean, dòng trùng/thiếu/thừa và giới hạn CSV.
- Test migration, seed admin, signup/login/logout, cookie và phân quyền.
- Test tạo/đổi tên competition, đăng ký idempotent, cấm nộp trước đáp án hoặc khi chưa đăng ký.
- Test nhiều lượt nộp, lịch sử điểm, chọn điểm cao nhất và tie-break.
- Test thay đáp án:
  - Không xác nhận thì không xoá dữ liệu.
  - File mới lỗi thì giữ nguyên đáp án và điểm cũ.
  - Thành công thì xoá toàn bộ điểm nhưng giữ registrations và toggle.
  - Lượt nộp tiếp theo bắt đầu lại từ 1.
- Test ranking không rò rỉ dữ liệu khi tắt và công khai họ tên đầy đủ khi bật.
- Ngoài phạm vi MVP: huỷ đăng ký, xoá competition, lưu/download file candidate, email verification, quên mật khẩu, hàng đợi chấm nền và triển khai cloud.
