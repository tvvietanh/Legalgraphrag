# Phân công và phụ thuộc P0–P9

Phân công mặc định theo hai vai trò, chưa gán tên cá nhân. Điều chỉnh khi người dùng giao khác; ghi điều chỉnh trong report. Không đổi số P để chia người.

| Giai đoạn | Owner chính | Phối hợp / sản phẩm bàn giao | Tài liệu |
| --- | --- | --- | --- |
| P0 Phạm vi | Cả hai | Dữ liệu chốt miền, nguồn, nhãn; hệ thống chốt interface, model/config và tài nguyên. Thống nhất schema/ID/phiên bản | `doc/overall.md`, `doc/sources.md`, `doc/system.md` |
| P1 Chuẩn bị, audit | Dữ liệu | Raw/staged, nguồn/giấy phép, manifest, số liệu sau lọc, mẫu thử | `doc/prepare-data.md`, `doc/sources.md` |
| P2 Chuẩn hóa | Dữ liệu | Cases/defendants/laws/guidance, source spans, mapping version, label audit; hệ thống góp ý hợp đồng đọc dữ liệu | `doc/normalize-data.md` |
| P3 Chia tập | Dữ liệu | Graph/dev/test theo matter, near-duplicate audit, test khóa; hệ thống bảo đảm chỉ nạp ID được phép | `doc/benchmark.md`, `doc/normalize-data.md` |
| P4 Làm giàu | Dữ liệu + hệ thống | Hệ thống chuẩn bị model/runtime, extractor và prompt; dữ liệu kiểm tra features, nguồn, duyệt checklist. Bàn giao enriched + QA | `doc/normalize-data.md`, `doc/KB-build.md`, `doc/system.md` |
| P5 Graph | Hệ thống | GraphStore, Fact/Ontology/Rule, embedding, community, snapshot/QA; dữ liệu đối chiếu nhãn và luật trên mẫu | `doc/build-graph.md` |
| P6 Agent | Hệ thống | Researcher/Auditor/Adjudicator, runner, trace; dữ liệu cung cấp mẫu kiểm tra đã duyệt | `doc/system.md`, `agents.md` ở root |
| P7 Benchmark | Dữ liệu | Bộ gold, qrels, protocol, coverage; hệ thống xây loader/scorer và kiểm tra định dạng | `doc/benchmark.md` |
| P8 Đánh giá | Hệ thống + dữ liệu | Hệ thống chạy baseline/ablation/metrics; dữ liệu kiểm lỗi nhãn, nguồn và giải thích pháp lý | `doc/evaluation.md` |
| P9 Báo cáo, bàn giao | Cả hai | Dữ liệu viết phần nguồn/QA/split; hệ thống viết phương pháp/thực nghiệm; cùng đối chiếu chứng cứ | `doc/report.md`, `doc/git_format.md` |

## Các cổng bàn giao

- P1: mẫu 200–300 là mục tiêu thử nghiệm theo tài liệu, không phải số liệu đã có. Audit quyết định khả thi và quy mô.
- P2–P3: facts không chứa verdict; nhãn đúng bị cáo; phân biệt cited/applied; mapping luật có phiên bản hoặc cách ly trường hợp mơ hồ; không overlap matter giữa các tập.
- P4–P5: chỉ dùng checklist được duyệt; mọi feature/quan hệ quan trọng có nguồn; chỉ graph corpus tham gia dựng graph, vector và community summary. Không qua P5 khi báo cáo nhãn, mapping và split chưa đáng tin cậy.
- P6: trace cho biết đã truy xuất gì, kiểm tra gì và loại gì; nguồn đầu ra nằm trong evidence hợp lệ. Thiếu điều kiện phải giữ trạng thái unknown.
- P7: chuẩn bị benchmark từ P2–P3, không chờ dựng graph xong mới chia test. Benchmark LJP held-out là chính; QA retrieval là bổ sung.
- P8–P9: cùng protocol/model/corpus trong so sánh; lưu prediction/config/metric/trace. Không tuyên bố cải thiện trước khi đo.

## Chuẩn bị mô hình song song

Ghi thành task trong report P0/P4/P6 tương ứng, không tự thêm giai đoạn làm lệch scope Git:

- Kiểm kê thiết bị, tài nguyên và dependency cục bộ; chưa tải model/gọi API trả phí khi chưa được duyệt phạm vi đó.
- Chốt revision của construction LLM, BGE-m3 và reasoning backbone; tách cấu hình khỏi mã.
- Dựng client/runtime và smoke test bằng fixture theo schema đã thống nhất.
- Ghi thiết bị, version, giới hạn bộ nhớ, latency thử nghiệm và trường hợp chưa kiểm tra bằng dữ liệu thật.

Các đường dẫn trong bảng tính từ root repository. `doc/overall.md` trỏ tới `doc/agents.md`, nhưng tài liệu Agent hiện nằm ở `agents.md` tại root; kiểm tra lại vị trí khi sử dụng.
