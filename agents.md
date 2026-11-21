# Agents

## Ba Agent là các vai trò Python dùng chung tài nguyên LLM và Graph

Trong repository gốc, `analyze_case()` gọi tuần tự `research()`, `audit()` và `adjudicate()` trong `core/agents/`, truyền một đối tượng `chatbot` xuyên suốt. Đây là &lt;Multi-Agent workflow&gt; theo chức năng, không phải ba mô hình fine-tune riêng và không bắt buộc chạy trên ba server.

## Researcher tìm bằng chứng từ hai lớp tri thức và embedding

+ Input: `LegalQuery` gồm facts theo bị cáo và mốc thời gian.
+ LLM: trích đặc trưng ontology và (nếu cần) tội danh ứng viên.
+ Tools: `semantic_match`, `community_expansion`, `charge_anchored`, `graph_lookup`.
+ Knowledge: chủ yếu Ontology Graph và Fact Graph; embedding model BGE-m3.
+ Output: `CandidateEvidence`, gồm `cases`, `law_articles`, `charges`, `retrieval_scores`, `strategy`, `source_ids`.
+ Failure: nếu không có bằng chứng hợp lệ, trả trạng thái `insufficient_evidence`, không tự sinh điều luật.

|| Pipeline Researcher:

```text
Query -> ontology features -> BGE-m3 query vector
      -> semantic top-k + community expansion + charge-anchored
      -> merge/deduplicate -> candidate evidence + trace
```

## Auditor kiểm chứng từng điều luật trước khi giữ lại bằng chứng

+ Input: `LegalQuery` + `CandidateEvidence`.
+ Tool: `get_checklist(article_version_id)` và `get_guidance(...)`.
+ LLM: kiểm các điều kiện từ facts theo từng checklist, trả `pass/fail/unknown` cùng hỗ trợ nguồn.
+ Logic chương trình: nếu điều kiện bắt buộc không thỏa → loại điều luật; nếu thiếu dữ kiện → `unknown` và không tự khẳng định có tội.
+ Provenance: ghi `article_version_id`, `check_item_id`, `source_span`, `reason`.
+ Output: `VerifiedEvidence` và `RejectedEvidence` có lý do.

|| Một bản ghi kiểm chứng minh họa:

```json
{
  "article_version_id": "law:blhs:rev01:art173",
  "checks": [
    {"check_item_id": "c1", "result": "unknown", "supporting_case_span": null}
  ],
  "decision": "requires_review",
  "source_ids": ["guide:001"]
}
```

## Adjudicator tổng hợp bằng chứng và dẫn nguồn chứ không tự mở rộng luật

+ Input: `LegalQuery` + `VerifiedEvidence`.
+ LLM backbone: Qwen3-8B làm lựa chọn gốc; phiên bản Việt hóa có thể thay nếu được cấu hình và đánh giá.
+ Prompt: yêu cầu nêu tội danh ứng viên, điều luật phiên bản, các yếu tố thỏa/không thỏa và nguồn cụ thể.
+ Output: `JudgmentResult` có `predicted_charges`, `predicted_articles`, `reasoning`, `evidence_ids`, `warnings`.
+ Không được thêm nguồn chưa có trong bằng chứng đã duyệt; nếu không đủ chứng cứ, báo bất định.

## Các công cụ được tách khỏi Agent để có thể kiểm thử độc lập

| Tool | Tác vụ | Input | Output |
| --- | --- | --- | --- |
| `extract_features()` | Ontology alignment | facts | four feature arrays |
| `embed_text()` | vector hóa | Vietnamese text | embedding |
| `semantic_match()` | nearest cases | query vector, k | ranked case IDs |
| `community_expand()` | mở rộng cluster | case IDs | related case IDs |
| `charge_anchor()` | truy xuất theo tội danh | predicted charges | case/article IDs |
| `get_checklist()` | điều kiện quy tắc | article version | checklist |
| `check_condition()` | đối chiếu tình tiết và luật | facts, checklist item | pass/fail/unknown |
| `synthesize_judgment()` | lập luận có nguồn | verified context | structured result |

## Orchestrator quản lý lời gọi và trạng thái của từng lượt

|| Pseudocode minh họa (không phải code repo gốc):

```python
# PSEUDOCODE
query = validate_query(raw_query)
features = extractor(query.facts)
candidates = researcher.retrieve(query, features, graph)
verified = auditor.verify(query, candidates, graph)
result = adjudicator.generate(query, verified, llm)
trace_store.write(query, features, candidates, verified, result)
return result
```

## Những khác biệt tiếng Việt cần chủ động sửa từ code gốc

+ Dùng prompt tiếng Việt được version hóa (repo gốc hỗ trợ `zh`/`en` theo README, không mặc định đã có `vi`).
+ Không giữ tiền tố tiếng Trung cố định khi ghép câu truy vấn Auditor/Adjudicator.
+ Không dùng luật số nguyên đơn độc; thêm khóa `article_version_id`.
+ Không dùng `eval()` với `judge_dep` và `related_laws` từ dữ liệu ngoài; dùng JSON schema hợp lệ.
+ Kiểm tra hiệu lực và điều khoản chuyển tiếp thay vì chỉ căn theo semantic score.

## Điều kiện hoàn thành là kết quả có trace tái hiện được

+ Researcher xuất top-k và các chiến lược đã đóng góp kết quả.
+ Auditor lưu checklist, câu trả lời từng điều kiện và source span.
+ Adjudicator chỉ trích dẫn các evidence IDs hợp lệ.
+ Chạy được một case test với reasoning không phụ thuộc thông tin trong phần quyết định.

## Nguồn mã gốc cho ba Agent

+ [analyze_case()](https://github.com/XMUDeepLIT/LegalGraphRAG/blob/main/core/utils/util.py).
+ [Researcher](https://github.com/XMUDeepLIT/LegalGraphRAG/blob/main/core/agents/researcher.py).
+ [Auditor](https://github.com/XMUDeepLIT/LegalGraphRAG/blob/main/core/agents/auditor.py).
+ [Adjudicator](https://github.com/XMUDeepLIT/LegalGraphRAG/blob/main/core/agents/adjudicator.py).

==> Các Agent là chương trình điều phối prompts, tools, LLM và graph; nhiệm vụ suy luận và kiểm chứng vẫn phải qua đánh giá thực nghiệm.
