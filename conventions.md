# Quy ước dự án

## Phạm vi lưu trữ

GitHub lưu code hệ thống, cấu hình mẫu, schema, prompt, kiểm thử và tài liệu.
Dữ liệu thật, nguồn PDF/TXT, JSON corpus, graph snapshot, kết quả chạy và log
API nằm local trong data/ hoặc trên Hugging Face; không commit dữ liệu hay khóa.
Fixture kiểm thử phải tổng hợp, không trích hồ sơ người thật.

## Tên và ngôn ngữ

Tên file/thư mục mới viết thường, dùng dấu - và không có khoảng trắng.
Module Python dùng snake_case để import được; giữ tên chuẩn README.md.
Tài liệu docs/offices/ viết tiếng Anh, chỉ lưu thiết kế đã thống nhất.
Tài liệu docs/drafts/ viết tiếng Việt, phân theo p0-scope, p1-data,
p2-normalization, p3-split, p4-enrichment, p5-graph, p6-agent,
p7-benchmark, p8-evaluation, p9-report khi có nội dung.
Thảo luận ngoài giai đoạn vào docs/drafts/others/chat-<chu-de>.md, gồm vấn đề,
hướng người dùng, đề xuất và thống nhất; không lưu nguyên chat có khóa/dữ liệu.
File này ở root để người dùng cùng repo đọc được; không sửa file ngoài repo.

## Git

Nhánh refactor: office-khang, bắt đầu từ origin/main trong worktree riêng.
Giữ nguyên dev-khang và thay đổi local. Không tự merge main hoặc force push.
Mỗi commit là một phần có thể kiểm tra; ghi rõ phụ thuộc nếu không độc lập.
Tiêu đề và body commit/PR bằng tiếng Anh: A(B): C.
A: init, develop, fix, verify, finish.
B: scope, data, normalization, split, enrichment, graph, agent, benchmark,
evaluation hoặc report. C là mô tả ngắn bắt đầu bằng động từ.
Ví dụ: develop(agent): Add evidence-based sequential reasoning roles.
Stage danh sách file cụ thể, rà staged diff và kiểm thử phù hợp trước commit.
Chọn riêng commit: cherry-pick vào nhánh tích hợp từ main, kiểm phụ thuộc và
tạo PR; merge cả office-khang sẽ mang mọi thay đổi chưa có trong main.
Hoàn tác thay đổi đã chia sẻ bằng revert; không ghi lại lịch sử.

## Review và chi phí

Kiểm tra kỹ thuật không đồng nghĩa nghiệm thu pháp lý. Không tự gán verified
cho nguồn/nhãn/graph chưa được duyệt. Không gọi API trả phí nếu chưa có
phạm vi request và ngân sách được phép. Không đưa token vào log hoặc commit.
Sau mỗi phần ghi kết quả và kiểm tra thực chạy; điểm cần người dùng duyệt
nội dung/phạm vi được giữ riêng, không suy ra từ việc duyệt TXT.
