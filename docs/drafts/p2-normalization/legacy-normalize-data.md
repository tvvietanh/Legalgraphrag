# Tài liệu thiết kế lịch sử — cần đối chiếu

Nội dung sau được giữ để truy vết; không phải xác nhận đã triển khai.
Liên kết và cây thư mục cũ có thể đã thay đổi.

# Normalization

## Mục tiêu chuẩn hóa là tạo khóa nhất quán cho bản án và quy phạm

Các file `normalized/*.jsonl` là nguồn chuẩn duy nhất cho Graph Builder và Benchmark Builder. Không chuyển trực tiếp dữ liệu Parquet hoặc Markdown vào graph mà bỏ qua kiểm tra pháp lý.

## Bộ schema chuẩn hóa tối thiểu gồm bốn loại dữ liệu

+ `cases.jsonl`: metadata vụ án và `facts` không chứa nhãn.
+ `defendants.jsonl`: bị cáo, tội danh, điều luật được áp dụng, hình phạt, nguồn quyết định.
+ `laws.jsonl`: văn bản/điều/khoản/điểm, phiên bản, hiệu lực, nội dung và nguồn.
+ `guidance.jsonl`: giải thích/hướng dẫn, điều luật mục tiêu, span chứng cứ và trạng thái duyệt.

### Case records tách nội dung vụ án khỏi kết luận của tòa

|| Schema minh họa:

```json
{
  "case_id": "case:abc123",
  "matter_group_id": "matter:m001",
  "source_id": "cbba:doc_id",
  "official_case_no": "SO_HIEU_MAU",
  "case_category": "Criminal",
  "trial_level": "First-instance",
  "event_date": null,
  "judgment_date": null,
  "facts": "Các tình tiết đã tách riêng từ bản án...",
  "facts_spans": [{"start": 0, "end": 45}],
  "defendant_ids": ["def:abc123:01"],
  "source_url": "",
  "extraction_version": "v1",
  "review_status": "needs_review"
}
```

### Defendant records giữ đúng đơn vị dự đoán trong LJP

|| Schema minh họa:

```json
{
  "defendant_id": "def:abc123:01",
  "case_id": "case:abc123",
  "facts_for_defendant": "Tình tiết gắn với bị cáo này...",
  "charges": ["charge:theft"],
  "applied_article_version_ids": ["law:blhs:rev01:art173"],
  "imprisonment_months": 18,
  "other_penalties": [],
  "judgment_span": {"start": null, "end": null},
  "label_verified": false
}
```

+ Hình phạt tù có thời hạn chuẩn hóa theo tháng khi nhãn cho phép; tử hình, tù chung thân, cải tạo không giam giữ và án treo phải có kiểu riêng.
+ Không quy đổi tù chung thân hoặc án treo thành số tháng tù tùy ý.
+ Nếu nhiều bị cáo cùng vụ việc, không gán mọi tội danh và mức án cho tất cả bị cáo.

### Law records quản lý cả căn cứ và phiên bản pháp lý

|| Schema minh họa:

```json
{
  "law_document_id": "100/2015/QH13",
  "law_version_id": "law:blhs:rev01",
  "article_version_id": "law:blhs:rev01:art173",
  "article_number": "173",
  "clause_number": null,
  "point_number": null,
  "article_title": "Tội trộm cắp tài sản",
  "text": "Nội dung lấy từ văn bản chính thức...",
  "effective_from": null,
  "effective_to": null,
  "amending_documents": [],
  "source_url": "",
  "source_span": null,
  "verification_status": "needs_review"
}
```

+ Giá trị phiên bản trong ví dụ chỉ là định danh kỹ thuật minh họa; không suy ra hiệu lực từ chuỗi tên file.
+ Ưu tiên văn bản chính thức để xác định lịch sử sửa đổi; VBHN hữu ích cho đọc tổng hợp nhưng không thay bảng phiên bản.

### Guidance records cung cấp căn cứ cho Checklist của Auditor

|| Schema minh họa:

```json
{
  "guidance_id": "guide:001",
  "document_id": "van-ban-huong-dan",
  "target_article_version_ids": ["law:blhs:rev01:art173"],
  "legal_text": "Trích đoạn đã xác minh...",
  "source_url": "",
  "source_span": null,
  "effective_from": null,
  "effective_to": null,
  "review_status": "needs_review"
}
```

## Trích xuất bốn nhóm đặc trưng của Ontology Graph

+ `defendant_info`: thuộc tính chủ thể; tránh tên, địa chỉ, thông tin định danh không cần thiết.
+ `criminal_acts`: hành vi khách quan được mô tả trong facts.
+ `victim_property_details`: người/tài sản/đối tượng bị xâm hại theo tình tiết.
+ `intent_remorse`: yếu tố lỗi và hành vi sau phạm tội nếu có bằng chứng trong facts.
+ Mỗi trường phải có `support_span`, `extraction_prompt_version`, `confidence/uncertainty`, `review_status`.
+ Không cho LLM nhìn `charges` và `applied_articles` khi chuẩn hóa truy vấn test.

|| Dữ liệu enriched minh họa:

```json
{
  "case_id": "case:abc123",
  "defendant_id": "def:abc123:01",
  "features": {
    "defendant_info": ["Người thành niên"],
    "criminal_acts": ["Hành vi chiếm đoạt tài sản theo mô tả"],
    "victim_property_details": ["Tài sản của chủ thể khác"],
    "intent_remorse": ["Chưa xác định từ tình tiết"]
  },
  "evidence_spans": [],
  "feature_model": "model-name-and-revision",
  "review_status": "needs_review"
}
```

## Chuẩn hóa mapping từ bản án sang văn bản luật

+ Giai đoạn A: dùng citation parser để lấy `mentioned_article_candidates`.
+ Giai đoạn B: đọc phần quyết định để xác định `applied_article_ids` theo bị cáo.
+ Giai đoạn C: normalize văn bản (Bộ luật Hình sự/BLHS/100/2015/QH13), số điều, khoản, điểm.
+ Giai đoạn D: map `article` sang `article_version_id` bằng hiệu lực và văn bản sửa đổi.
+ Giai đoạn E: với trường hợp không đủ thời điểm/hiệu lực, đặt `mapping_status=ambiguous` và yêu cầu kiểm tra.
+ Giai đoạn F: lưu `reference_source_span` để mỗi cạnh Fact/Rule truy lại được câu gốc.

## Checklist được trích xuất thành những điều kiện có nguồn cụ thể

+ Đầu vào: điều luật và guidance có hiệu lực phù hợp.
+ LLM chỉ đề xuất các câu hỏi điều kiện, loại điều kiện (`required`, `exception`, `threshold`) và span hỗ trợ.
+ Người kiểm tra đánh dấu `approved`, `rejected`, `needs_revision`.
+ Nếu không tìm được nguồn điều kiện thì checklist không được xem là căn cứ pháp lý xác nhận.

|| Schema checklist minh họa:

```json
{
  "checklist_id": "check:art173:rev01",
  "article_version_id": "law:blhs:rev01:art173",
  "items": [{
    "item_id": "c1",
    "question": "Điều kiện pháp lý cần kiểm tra (minh họa)?",
    "source_guidance_id": "guide:001",
    "source_span": null,
    "required": true,
    "review_status": "needs_review"
  }]
}
```

## Các tệp chuẩn hóa được triển khai độc lập và có test

| File đề xuất | Hàm | Kiểm thử tối thiểu |
| --- | --- | --- |
| `src/vnlegal/normalize/cases.py` | `extract_case_sections()` | không chứa verdict trong `facts` |
| `src/vnlegal/normalize/defendants.py` | `split_defendants()` | nhiều bị cáo/đa tội danh |
| `src/vnlegal/normalize/laws.py` | `parse_law_hierarchy()` | điều, khoản, điểm và ký hiệu |
| `src/vnlegal/normalize/versions.py` | `resolve_legal_version()` | time interval và trường hợp mơ hồ |
| `src/vnlegal/normalize/references.py` | `resolve_applied_citations()` | cited vs applied |
| `src/vnlegal/extract/case_features.py` | `extract_ontology_features()` | JSON schema + source spans |
| `src/vnlegal/extract/diagnostic_rules.py` | `extract_checklist()` | review gate |
| `src/vnlegal/normalize/validate.py` | `run_invariants()` | no orphan IDs, no overlap |

## Các quy tắc kiểm soát bắt buộc được tự động hóa

+ `assert unique(case_id)` và `assert unique(defendant_id)`.
+ `assert set(applied_articles) <= set(known_article_versions)` hoặc đưa sang queue kiểm tra.
+ `assert no_label_leakage(facts)` thông qua pattern và kiểm tra mẫu thủ công (không phụ thuộc hoàn toàn regex).
+ `assert no_matter_group_overlap(graph_ids, test_ids)`.
+ `assert all(approved_edge has source_url or source_doc_id)`.
+ `assert no unreviewed_checklist in final RuleGraph`.
+ Kiểm tra mỗi bản ghi có `source_hash`, `schema_version` và mốc tạo.

## Adapter sang schema gốc cần dùng parser an toàn

+ `Case`: đưa `case_id → id`, `facts → fact`, `charges → crime`, `articles → law`, `features`.
+ `Law`: đưa `article_number → id/entry`, nội dung → `items[].text`, checklist duyệt → `items[].judge_dep`, liên quan → `items[].related_laws`.
+ Cần sửa logic repo gốc cho tiếng Việt: không bỏ nhầm điều luật vì điều kiện số điều hard-coded hoặc xử lý ID theo int.
+ Không dùng `eval()` để parse dữ liệu từ nguồn bên ngoài; chuyển về JSON chuẩn và dùng `json.loads()` + schema validation.
+ Khóa phiên bản nên được giữ ở lớp adapter/graph nội bộ, vì schema gốc chỉ có ID điều luật đơn giản.

## Điều kiện hoàn thành là bộ dữ liệu đã duyệt và có manifest

+ Phần `normalized` đọc được bằng Pydantic.
+ Mỗi nhãn có vị trí/nguồn; mỗi luật có văn bản nguồn đã xác minh.
+ Báo cáo `label-audit.csv`, `law-link-audit.csv`, `pii-audit.csv`.
+ Các lỗi còn lại được cách ly, không lặng lẽ điền thông tin bằng LLM.

==> prepare-data.md (đường dẫn lịch sử: `prepare-data.md`) là bước trước; build-graph.md (đường dẫn lịch sử: `build-graph.md`) là bước kế tiếp.

## Nguồn đối chiếu cho schema và truy vết

+ [Schema nguồn CBBA](https://huggingface.co/datasets/tmquan/cbba-toaan-gov-vn).
+ [Schema Pháp điển](https://huggingface.co/datasets/tmquan/phapdien-moj-gov-vn).
+ [LegalGraphRAG — preprocess](https://github.com/XMUDeepLIT/LegalGraphRAG/tree/main/core/preprocess).
+ [Luật sửa đổi 86/2025/QH15](https://vbpl.moj.gov.vn/bocongan/Pages/vbpq-toanvan.aspx?ItemID=179251&Keyword=).
