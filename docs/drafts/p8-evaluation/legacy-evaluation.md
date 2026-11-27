# Tài liệu thiết kế lịch sử — cần đối chiếu

Nội dung sau được giữ để truy vết; không phải xác nhận đã triển khai.
Liên kết và cây thư mục cũ có thể đã thay đổi.

# Evaluation

## Thí nghiệm cần đo cả độ chính xác, truy xuất, kiểm chứng và chi phí

Đánh giá trên bộ test đã khóa, sử dụng cùng corpus luật, cùng miền pháp lý, cùng phiên bản model và cùng quy tắc tính điểm. Mỗi chạy phải lưu cấu hình, raw prediction, trace và metric.

## Các baseline được chạy với cùng một giao thức

+ &lt;Direct LLM&gt;: chỉ cung cấp tình tiết cho cùng backbone, không truy xuất ngoài.
+ &lt;Naive RAG&gt;: embedding search trên law/case chunks rồi đưa ngữ cảnh cho LLM.
+ &lt;Flat GraphRAG&gt;: graph không phân lớp Fact/Ontology/Rule, dùng cùng ngân sách truy xuất.
+ &lt;Hierarchical GraphRAG&gt;: đầy đủ ba lớp nhưng không có Auditor.
+ &lt;LegalGraphRAG-VN Full&gt;: Researcher + Auditor + Adjudicator và HierarGraph.

==> So sánh phải giữ tương đồng model, test set và số evidence tokens càng nhiều càng tốt.

## Các ablation xác định tác động của từng thành phần

+ `w/o Ontology`: bỏ đặc trưng và community, chỉ tìm fact/rules trực tiếp.
+ `w/o Fact`: bỏ đường nối vụ án–điều luật–tội danh, chỉ dựa retrieval ngữ nghĩa.
+ `w/o Rule`: bỏ checklist/guidance để kiểm tác động đến groundedness.
+ `w/o Researcher-community`: tắt community expansion.
+ `w/o Researcher-charge`: tắt charge-anchored retrieval.
+ `w/o Auditor`: đưa ứng viên trực tiếp cho Adjudicator.
+ `embedding swap`: kiểm vai trò biểu diễn BGE-m3 trên tiếng Việt.

## Metrics chính phản ánh đúng định nghĩa của nhiệm vụ

| Nhóm | Metric | Cách dùng |
| --- | --- | --- |
| Tội danh | Accuracy exact-match, Micro-F1 | So với set charges của bị cáo |
| Điều luật | Accuracy exact-match, Micro-F1 | So `article_version_id` theo protocol |
| Hình phạt | MAE (tháng), Exact-match tùy mục tiêu | Chỉ mẫu có penalty cùng loại |
| Retrieval | Recall@k, Precision@k, MRR, nDCG | So với gold article qrels |
| Audit | precision/recall của luật được giữ; rejection accuracy | Cần mẫu pháp lý đã duyệt |
| Citation | nguồn tồn tại, trích dẫn đúng, support rate | Kiểm tra span và đúng version |
| Runtime | latency P50/P95, token/query, cost/query | Ghi riêng offline và online |

## Luồng chạy đánh giá có thể tái lập theo manifest

+ B1: `load_snapshot(graph_hash)`.
+ B2: đọc test manifest, kiểm không overlap graph/test.
+ B3: nạp model/prompt/embedding cố định theo config.
+ B4: chạy từng phương pháp; lưu raw output trước khi parse.
+ B5: chuẩn hóa predictions về `predicted_charges`, `predicted_articles`, `penalty`.
+ B6: áp dụng metric script chung, lưu per-case errors.
+ B7: tổng hợp theo tội danh, năm, trial level, độ dài input, nhiều bị cáo.
+ B8: xuất bảng, biểu đồ và mẫu trace đúng/sai.

|| Lệnh CLI dự kiến cho bản Việt hóa (đề xuất, chưa triển khai):

```bash
python scripts/evaluate.py --config Others/config/experiments/full.yaml \
  --split data/splits/test.jsonl \
  --output artifacts/metrics/full
```

## Tổ chức kết quả thuận tiện cho báo cáo

```text
artifacts/
  predictions/full/test_predictions.jsonl
  predictions/naive-rag/test_predictions.jsonl
  traces/full/trace_q001.json
  metrics/full/summary.json
  metrics/full/per_case.csv
  metrics/compare_methods.csv
  metrics/ablation.csv
  metrics/retrieval_at_k.csv
  metrics/error_taxonomy.csv
  figures/accuracy_by_charge.png
  figures/retrieval_recall.png
  figures/latency.png
```

## Phân tích lỗi phải xem cả sai nguồn và sai suy luận

+ Sai truy xuất: không tìm thấy điều luật gốc.
+ Sai phạm vi: tìm đúng chủ đề nhưng khác điều kiện áp dụng.
+ Sai phiên bản: dùng văn bản không phù hợp với thời điểm vụ việc.
+ Sai kiểm chứng: Auditor bỏ luật đúng hoặc giữ luật sai.
+ Sai tổng hợp: trích dẫn sai, suy luận vượt quá chứng cứ.
+ Sai nhãn: bản án nhiều bị cáo, trích sai hình phạt hoặc tội danh.

## Điều kiện nghiệm thu thí nghiệm phải kiểm tra được bằng file

+ Mọi run có `run_id`, code commit, graph hash, model revision, prompt hash và seed.
+ Có thống kê số test mẫu được sử dụng và loại bỏ cùng lý do.
+ Có ít nhất một baseline và một ablation kiểm tra được end-to-end.
+ Có bảng lỗi định tính từ mẫu truy vấn và các nguồn dùng để đối chiếu.
+ Không tuyên bố LegalGraphRAG-VN tốt hơn baseline trước khi chạy và so điểm.

## Nguồn metric và protocol gốc

+ [LegalGraphRAG repository — evaluation](https://github.com/XMUDeepLIT/LegalGraphRAG/tree/main/evaluation).
+ [Bài báo gốc](https://aclanthology.org/2026.acl-long.1738/) (Table 2, Table 3, Appendix D.3).
+ [Vietnamese Legal QA](https://huggingface.co/datasets/nguyenthanhasia/vn-legal-qa).
+ [VLegal-Bench](https://huggingface.co/datasets/CMC-OPENAI/VLegal-Bench).

==> Bằng chứng báo cáo gồm raw prediction, metrics, configs, trace và nguồn; không chỉ ghi một số Accuracy tổng.
