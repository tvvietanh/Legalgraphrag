# Vietnamese LegalGraphRAG

## 1. Giới thiệu

Tái lập hướng LegalGraphRAG cho pháp luật hình sự Việt Nam, ban đầu tập trung
nhóm tội xâm phạm sở hữu. Hệ thống hỗ trợ nghiên cứu, không thay quyết định pháp lý.
Tham khảo và thiết kế lịch sử ở docs/drafts/; phạm vi đã thống nhất ở
[overall.md](docs/offices/overall.md).

GitHub chỉ lưu code và tài liệu; dữ liệu ở
[Hugging Face](https://huggingface.co/datasets/legalgraphrag-teamm/vn-legalgraphrag-data).
`official/` là TXT dự án đã chốt; `draft/` là JSON/graph thử nghiệm.

## 2. Hướng dẫn cài đặt

Hướng dẫn sử dụng local đầy đủ sẽ bổ sung sau khi kiểm tra gói code tích hợp.
Không tự tải mô hình, gọi API trả phí hoặc tải dữ liệu khi mở repo.

## 3. Thiết kế cơ bản

- Fact Graph: tình tiết và đặc trưng vụ án gắn nguồn.
- Ontology Graph: khái niệm, đặc trưng và checklist pháp lý.
- Rule Graph: văn bản luật, Điều/Khoản/Điểm và quan hệ đã được review.
- LLM xây KB hỗ trợ trích ý nghĩa; LLM suy luận tổng hợp bằng chứng.
- User cung cấp tình tiết; Researcher tìm bằng chứng; Auditor kiểm điều kiện;
  Adjudicator tổng hợp kết quả. Không bắt buộc mỗi vai trò dùng mô hình riêng.

Luồng: nguồn → TXT chuẩn hóa → JSON → enrichment/review → graph → agent.
Code hiện hữu chưa chứng minh KB ba tầng đã hoàn chỉnh.

## 4. Cấu trúc source code

- `docs/offices/`: thiết kế đã thống nhất, tiếng Anh.
- `docs/drafts/`: quá trình phát triển, tiếng Việt; `others/` lưu thảo luận chung.
- `scripts/`: lệnh build/chạy; `download-dataset.py` lấy dữ liệu HF theo commit cố định.
- `config/`, `prompts/`: cấu hình mẫu và prompt, không chứa khóa.
- `src/vnlegal/`: thư viện Python xử lý văn bản và hợp đồng dữ liệu.
- `schemas/`: schema kiểm tra dữ liệu, không chứa dữ liệu thật.
- `tests/`: kiểm thử offline bằng fixture tổng hợp.
- `conventions.md`: quy ước tên, dữ liệu, review và Git.

Code được đưa sang từng commit; xem tiến độ ở
[refactor-commit-plan.md](docs/drafts/others/refactor-commit-plan.md).
