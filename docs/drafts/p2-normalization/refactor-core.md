# Tách code nền

Đưa normalize, kb_inputs và law_schema sang package src/vnlegal. Chuyển schema
ra schemas/ để không phụ thuộc Others. Giữ schema lịch sử để đọc hợp đồng cũ,
không coi tất cả phiên bản là active. Chưa mang corpus hoặc ví dụ hồ sơ sang.
Cài editable từ source checkout; chưa cam kết chạy wheel độc lập có schema.
Kiểm thử offline: test_vietnamese_text, test_law_text, test_defendants,
test_case_sections. Kết quả cụ thể xem báo cáo tổng hợp refactor.
