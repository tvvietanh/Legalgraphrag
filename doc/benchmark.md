# Benchmark

## Benchmark chính phải cùng miền và cùng định dạng dự đoán của LegalGraphRAG

&lt;Legal Judgment Prediction&gt; cần query là tình tiết vụ án, nhãn là tội danh/điều luật/hình phạt cho mỗi bị cáo. Không đánh đồng benchmark Legal QA hoặc tìm điều luật đa ngành với benchmark bản án hình sự.

## Tập đánh giá chính được tạo từ bản án hình sự giữ lại

+ Nguồn: cùng hệ thống bản án đã chọn, nhưng không xuất hiện trong graph corpus.
+ Đơn vị: `defendant_id` và `matter_group_id` để tránh rò rỉ sơ thẩm/phúc thẩm.
+ Input: `facts_for_defendant` không chứa nhãn/tội danh/quyết định.
+ Labels: `charges`, `applied_article_version_ids`, `imprisonment_months` (nếu dạng hình phạt cho phép).
+ Metadata: `case_year`, `charge_family`, `trial_level`, `source_id`, `label_verified`, `law_version_status`.
+ Cách chia đề xuất: train corpus/graph + dev + held-out test theo vụ việc; ưu tiên tách thời gian bổ sung nếu đủ dữ liệu.

|| Bản ghi test minh họa (không phải mẫu thực):

```json
{
  "query_id": "test:q001",
  "case_id": "case:holdout001",
  "matter_group_id": "matter:holdout001",
  "defendant_id": "def:holdout001:01",
  "facts": "Tình tiết đã bỏ đoạn quyết định...",
  "gold": {
    "charges": ["charge:theft"],
    "article_version_ids": ["law:blhs:rev01:art173"],
    "imprisonment_months": 18
  },
  "quality": {"fact_verified": false, "label_verified": false}
}
```

## Benchmark retrieval công khai chỉ dùng khi ánh xạ được vào kho luật

### Vietnamese Legal QA có nhãn article-level đã công bố

+ Nguồn: [nguyenthanhasia/vn-legal-qa](https://huggingface.co/datasets/nguyenthanhasia/vn-legal-qa).
+ Quy mô: 5.330 train, 592 test; kèm legal corpus khoảng 207 MB theo card.
+ Task: query → `relevant_articles[{law_id, article_id}]`.
+ Trước khi chạy: lọc luật hình sự, map qrels sang `article_version_id`, báo tỷ lệ query còn hợp lệ.

### DRiLL phù hợp cho đánh giá riêng Researcher

+ Nguồn: [DRiLL Shared Task 2025](https://aclanthology.org/2025.vlsp-1.16/), [trang cuộc thi](https://vlsp.org.vn/vlsp2025/eval/drill).
+ Task: legal document retrieval quy mô nhiều lĩnh vực.
+ Chưa xác nhận split công khai hiện tải được và lượng câu hình sự; phải kiểm toán trước khi cam kết benchmark chính.

### VLegal-Bench phù hợp kiểm thử khả năng phụ trợ

+ Nguồn: [CMC-OPENAI/VLegal-Bench](https://huggingface.co/datasets/CMC-OPENAI/VLegal-Bench).
+ Task gợi ý: `2.2 Legal Element Recognition`, `2.4 Judgement Verification`, `3.1 Article/Clause Prediction`, `3.2 Legal Court Decision Prediction`, `3.3 Multi-hop Graph Reasoning`, `3.5 Penalty/Remedy Estimation`.
+ Cần xem từng split/mẫu để xác định phần hình sự, loại trừ các tác vụ không cùng định dạng LJP.

## Bảng tương thích benchmark với thành phần hệ thống

| Nhiệm vụ | Nguồn | Kết quả đo | Trạng thái |
| --- | --- | --- | --- |
| Charge prediction | CBBA held-out | Exact-match Acc, Micro-F1 | Phải tự chuẩn hóa nhãn |
| Article prediction | CBBA held-out | Exact-match Acc, Micro-F1 | Phải map version |
| Penalty prediction | CBBA held-out | MAE tháng, exact match khi hợp lệ | Tùy độ phủ nhãn |
| Article retrieval | Vietnamese Legal QA / DRiLL filtered | Recall@k, MRR, nDCG | Cần lọc miền |
| Verification | VLegal-Bench relevant subset | Accuracy/F1, citation support | Kiểm tra format |
| Evidence groundedness | CBBA held-out + review samples | Citation correctness, unsupported claims | Cần gán nhãn bổ sung |

## Protocol chia tập kiểm tra chặt chẽ chống rò rỉ

+ Tách theo `matter_group_id`, không theo dòng và không theo file PDF.
+ Ghép các bản án cùng vụ việc; nếu không xác định được, đánh dấu suspicious overlap.
+ Dùng near-duplicate detection từ tình tiết và metadata để tìm trường hợp đổi số hiệu nhưng trùng nội dung.
+ Đóng băng test IDs trước khi sinh graph, embeddings, community summaries và checklists bằng case data.
+ Không dùng nhãn của test để dự đoán tội danh ứng viên hay trích xuất tính năng.
+ Loại query có nguồn luật ngoài phạm vi trước khi tính retrieval metric; báo rõ số bị loại.
+ Giữ phân bố tội danh, năm, độ dài và nhiều bị cáo trong báo cáo split.

## Data quality benchmark phải được kiểm chứng ngoài tự động

+ Kiểm thử tối thiểu vài trăm mẫu (đề xuất 200–300) với người đọc đối chiếu phần quyết định.
+ Quy tắc nhãn: tội danh quy về bảng charge canonical; điều luật áp dụng cho bị cáo cụ thể; hình phạt đúng loại.
+ Đối chiếu pháp luật lịch sử nếu bài toán dự đoán ứng dụng pháp luật theo thời điểm.
+ Ghi `gold_label_source_span`, `annotation_reviewer`, `review_status` nhưng không đưa metadata nhãn vào đầu vào model.

## Các file và công cụ để xây benchmark

| Tệp đề xuất | Vai trò |
| --- | --- |
| `src/vnlegal/eval/datasets.py` | đọc split, chuẩn hóa labels |
| `src/vnlegal/eval/leakage.py` | kiểm overlap, near duplicate |
| `src/vnlegal/eval/qrels.py` | map legal-QA qrels tới luật trong graph |
| `scripts/split_data.py` | tạo graph/dev/test manifests |
| `scripts/audit_benchmark.py` | phân bố, độ phủ và chất lượng |
| `data/splits/graph_ids.jsonl` | ID được phép xây graph |
| `data/splits/dev.jsonl` | chỉnh tham số trên dev |
| `data/splits/test.jsonl` | test khóa, không dùng để tune |

## Quy mô benchmark là mục tiêu kế hoạch và phải qua audit

+ Mục tiêu sơ bộ: khoảng 500–1.000 case/defendant test đủ nhãn (không cam kết trước khi kiểm kê).
+ Nghiên cứu ban đầu: chạy 100–200 mẫu test đã kiểm chứng để sửa pipeline.
+ Kiểm thử công khai: báo tổng số câu benchmark gốc và số lượng còn lại sau lọc hình sự.
+ Không so sánh trực tiếp điểm của benchmark khác protocol với bảng CAIL gốc.

==> Benchmark chính cho hướng A phải được kiểm chứng cùng miền với Graph; retrieval QA công khai là bài kiểm tra phụ bổ sung.
