# Tách code graph

GraphSnapshot quản lý node/cạnh, provenance, ID và trạng thái verified.
Fact, Ontology, Rule và compact Rule là builder; kb_snapshot ghép snapshot.
CompactRelease đọc JSON Task7, kiểm hash và span trước khi đưa vào builder.
Các CLI trong scripts/ gọi module tương ứng và lưu kết quả vào data/ local.
Không có dữ liệu thật trong commit; graph lưu bằng JSON là định dạng trao đổi,
không chứng minh graph đã đủ quan hệ pháp lý. Phụ thuộc code nền commit trước.
Kiểm thử graph dùng nguồn giả và thư mục tạm, không đọc corpus hoặc gọi LLM.
