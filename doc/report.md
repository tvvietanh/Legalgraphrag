# Report

## Báo cáo nghiên cứu phải mô tả đủ dữ liệu, phương pháp và giới hạn

Mục tiêu là có một báo cáo đồ án tái lập rõ nguồn dữ liệu, sơ đồ kiến trúc, protocol thực nghiệm, lỗi và kết quả. Không trình bày sơ đồ đề xuất như hệ thống đã triển khai nếu chưa có log/code chứng minh.

## Cấu trúc báo cáo bám theo toàn bộ pipeline

+ Chương 1 — Giới thiệu: vấn đề RAG trong pháp luật, LegalGraphRAG, mục tiêu tái lập trên tiếng Việt, phạm vi hình sự.
+ Chương 2 — Khảo sát: paper gốc, cấu trúc repo, đặc thù luật Việt Nam, nguồn dữ liệu và benchmark.
+ Chương 3 — Thiết kế: Actor, Agent, kiến trúc hai giai đoạn, schema, ba lớp graph.
+ Chương 4 — Tiền xử lý: audit, chuẩn hóa, mapping luật, trích xuất features/checklists, QA.
+ Chương 5 — Hiện thực: công cụ, phiên bản model, snapshot graph, prompts, các Agent.
+ Chương 6 — Thực nghiệm: split, baseline, ablation, retrieval/charge/article/penalty, latency.
+ Chương 7 — Đánh giá: lỗi, giới hạn, rủi ro pháp lý, khả năng mở rộng.

## Bảng chứng cứ phải liên kết được đến file kết quả

| Bảng/Hình | File minh chứng | Nội dung |
| --- | --- | --- |
| Data profile | `data-audit.csv` | dữ liệu nguồn và số lượng sau lọc |
| Schema mapping | `law-link-audit.csv` | tỷ lệ nối bản án→luật |
| Graph statistics | `graph-stats.json` | node/edge theo loại, độ phủ |
| Benchmark profile | `split-report.json` | phân bố và chống leakage |
| Main results | `compare_methods.csv` | các baseline cùng protocol |
| Ablation | `ablation.csv` | vai trò các thành phần |
| Retrieval | `retrieval_at_k.csv` | Recall@k/MRR/nDCG |
| Runtime | `runtime.csv` | latency/token/cost |
| Qualitative cases | `traces/*.json` | bằng chứng và lý do kiểm chứng |

## Trích dẫn nguồn dữ liệu phải được lập thành danh mục có phiên bản

+ Tên nguồn, tổ chức phát hành, URL và ngày truy cập.
+ License, điều kiện truy cập, trạng thái giấy phép và nguồn gốc tài liệu.
+ Số lượng thực dùng sau lọc, không chỉ số liệu tổng trên dataset card.
+ Mô hình và phiên bản, seed, prompt, checksum dữ liệu và commit code.

## Các hình nên giúp người đọc kiểm chứng logic chứ không trang trí

+ Pipeline Offline và Online.
+ Component Diagram: Actors, Agents, tools, models, graph.
+ Sơ đồ node/edge ba lớp graph.
+ Flow `Raw → Normalized → Enriched → Graph → Benchmark`.
+ Biểu đồ phân bố tội danh và số lượng sau mỗi bước lọc.
+ Biểu đồ Accuracy/Recall/Latency và ablation.

## Mẫu kết luận phải phân biệt thành tựu và hạn chế

+ Đã hiện thực được module nào, có test hay chưa.
+ Có bao nhiêu case/law/guidance thực sự liên kết thành công.
+ Độ chính xác/khả năng truy vết có tăng hay giảm so với baseline.
+ Những điểm chưa được xác minh: checklist, temporal applicability, benchmark coverage.
+ Định hướng sau dự án: thêm luật hiệu lực lịch sử, án lệ, hiệu chỉnh embedding và graph storage.

## Tài liệu tham khảo cốt lõi

+ [LegalGraphRAG tại ACL](https://aclanthology.org/2026.acl-long.1738/).
+ [Repository LegalGraphRAG](https://github.com/XMUDeepLIT/LegalGraphRAG).
+ [Bản án CBBA](https://huggingface.co/datasets/tmquan/cbba-toaan-gov-vn).
+ [Pháp điển](https://huggingface.co/datasets/tmquan/phapdien-moj-gov-vn).
+ [Nguồn luật chính thức](https://vbpl.moj.gov.vn/).
+ [Vietnamese Legal QA](https://huggingface.co/datasets/nguyenthanhasia/vn-legal-qa).

==> Bản báo cáo chỉ hoàn chỉnh khi mỗi kết quả quan trọng đều có thể truy lại file cấu hình, dữ liệu và log thực nghiệm.
