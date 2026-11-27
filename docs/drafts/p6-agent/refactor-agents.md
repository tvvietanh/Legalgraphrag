# Tách agent và kết nối mô hình

Đưa Researcher → Auditor → Adjudicator cùng hợp đồng LegalQuery và adapter
local/remote vào src/vnlegal/agents. pipeline.analyze gọi lần lượt retrieve,
audit, adjudicate và trả trace. construction_model phục vụ tạo summary;
enrichment_validation kiểm schema/span/ID nhưng luôn cần review ngữ nghĩa.

CLI run-legal-agents.py đọc graph và facts trong data/ local, mặc định không
gọi mô hình. Remote yêu cầu --allow-paid-api; cờ chỉ là guard kỹ thuật, vẫn
cần người dùng duyệt phạm vi/chi phí. Không có khóa thật trong config.
check-remote-model.py mặc định kiểm profile offline; setup-qwen.py mặc định
lập plan, không tự tải hoặc khởi động dịch vụ.

Tests dùng mock và fixture tổng hợp; bỏ test phụ thuộc snapshot local thật.
Không có kết quả của mô hình thật hoặc corpus trong commit. Phụ thuộc graph
và hợp đồng của hai commit code trước.
