# System

## Mục đích của hệ thống là tái lập pipeline suy luận pháp luật dựa trên bằng chứng

Hệ thống là &lt;Research Prototype&gt; dành cho nghiên cứu &lt;Legal Judgment Prediction&gt; trên dữ liệu hình sự Việt Nam. Không thay thế đánh giá pháp lý của chuyên gia, không cung cấp kết luận có hiệu lực pháp luật.

==> Định nghĩa nhiệm vụ và ranh giới hệ thống trước khi phát triển UI hoặc API.

## Kiến trúc tách giai đoạn dữ liệu và giai đoạn suy luận

+ &lt;Offline / Knowledge Build&gt;: tiếp nhận bản án, điều luật, hướng dẫn; chuẩn hóa và kiểm chứng; tạo embedding và HierarGraph.
+ &lt;Online / Inference&gt;: tiếp nhận vụ việc; Researcher truy xuất; Auditor kiểm tra; Adjudicator tổng hợp; xuất trace.
+ &lt;Evaluation / Batch&gt;: đọc held-out benchmark; chạy baseline và ablation; lưu prediction và metric.

|| Component diagram dạng văn bản:

```text
                    EXTERNAL
       [Data Curator]       [User / Evaluator]
             |                    |
             v                    v
     [Ingest + QA]            [Query Runner]
             |                    |
       [Normalize]                 v
             |               [Researcher] <─── [Embedding BGE-m3]
       [Enrichment]                |       \
             |                    |        └──► [Graph Store]
       [Graph Builder] ──► [Graph Store]    /     | Fact
                          (NetworkX)    /      | Ontology
                                 |     /        | Rule
                                 v    v
                               [Auditor] ──► [Rule Checklist]
                                 |
                                 v
                             [Adjudicator] <──► [Reasoning LLM]
                                 |
                                 v
                             [Prediction/Trace]
                                 |
                                 v
                             [Evaluator]
```

## Các Actors ở ngoài và các Agent ở trong hệ thống

+ &lt;Data Curator&gt;: chọn nguồn, quyết định bản ghi hợp lệ, duyệt checklist, đối chiếu luật.
+ &lt;User&gt;: cung cấp tình tiết vụ việc cần phân tích.
+ &lt;Evaluator&gt;: chạy thí nghiệm, đối chiếu benchmark, xuất báo cáo.
+ &lt;Researcher&gt;: module nội bộ, không phải một người dùng ngoài hệ thống.
+ &lt;Auditor&gt;: module nội bộ kiểm chứng điều kiện áp dụng.
+ &lt;Adjudicator&gt;: module nội bộ điều phối sinh kết luận.

==> Actor (ngoại vi) khác Agent (thành phần phần mềm trong pipeline).

## Các mô hình đảm nhiệm những nhiệm vụ khác nhau

| Thành phần | Lựa chọn tái lập | Công việc | Ghi chú |
| --- | --- | --- | --- |
| Graph construction LLM | GPT-4o-mini | Trích xuất case features; sinh checklist dự thảo | Theo hướng paper gốc; không được tự xác nhận hiệu lực luật |
| Embedding model | BGE-m3 | Vector cho case/law/charge/query | Cần đánh giá truy xuất tiếng Việt, cố định phiên bản |
| Reasoning backbone | Qwen3-8B | Cấp khả năng suy luận cho các Agent | Một mô hình nền mặc định, không phải ba bản fine-tune |
| Graph engine | NetworkX MultiDiGraph | Node, edge, graph traversal | Gần với code gốc, lưu checkpoint pickle tin cậy |
| Community detection | Louvain trong hàm code kiểm tra | Cộng đồng vụ án | Bài báo nêu Leiden; phải ghi chính xác lựa chọn thực thi |
| Model runtime | Transformers/PyTorch hoặc API tương thích | Nạp LLM | Cấu hình thiết bị và seed ở một chỗ |
| Data processing | Python, Hugging Face Datasets, PyArrow/Polars | Lọc Parquet/JSONL | Thiết kế xử lý theo batch, tránh tải toàn kho vào RAM |
| Schemas / tests | Pydantic, pytest | Kiểm tra kiểu và invariant | Đề xuất cho bản Việt hóa |

## Luồng dữ liệu giữa các module được định nghĩa bằng hợp đồng

+ `RawDocument` → `NormalizedCase` / `NormalizedLaw` / `LegalGuidance`.
+ `NormalizedCase` → `CaseFeature` (bốn nhóm đặc trưng + nguồn từng nhóm).
+ `NormalizedLaw` + `LegalGuidance` → `DiagnosticChecklist` (bản nháp + tình trạng duyệt).
+ Các bản ghi đã duyệt → `GraphSnapshot` (node, edge, embeddings, provenance).
+ `LegalQuery` → `CandidateEvidence` → `VerifiedEvidence` → `JudgmentResult`.

|| Hợp đồng đầu vào/đầu ra ngắn gọn:

```json
{
  "query_id": "q-001",
  "case_facts": "Nội dung tình tiết đã ẩn nhãn...",
  "event_date": null,
  "defendant_id": "d-001"
}
```

```json
{
  "query_id": "q-001",
  "predicted_charges": [],
  "predicted_articles": [],
  "reasoning": "",
  "evidence_ids": [],
  "model_version": "",
  "graph_version": "",
  "warnings": []
}
```

## Sơ đồ tuần tự mô tả một lượt suy luận

|| Tương tác ở mức logic, không khẳng định Agent giao tiếp qua HTTP:

```text
User -> Runner: case_facts
Runner -> Researcher: LegalQuery
Researcher -> Embedding: ontology-aligned query
Embedding --> Researcher: query vector
Researcher -> Graph: semantic / community / charge-anchored retrieval
Graph --> Researcher: candidate cases, laws, charges
Researcher -> Auditor: CandidateEvidence
Auditor -> Graph: laws, checklist, interpretation, version
Graph --> Auditor: rules + source links
Auditor -> LLM: condition-wise verification prompts
LLM --> Auditor: checks with rationales
Auditor -> Adjudicator: VerifiedEvidence
Adjudicator -> LLM: source-grounded synthesis
LLM --> Adjudicator: judgment + citations
Adjudicator -> Runner: JudgmentResult + trace
Runner --> User: result
Runner -> Evaluator: prediction record
```

## Tổ chức source code mẫu giữ chức năng và dữ liệu độc lập

|| Đường dẫn dưới đây là kiến trúc đề xuất; các file gốc được chỉ rõ riêng:

```text
src/vnlegal/
  ingest/       cbba.py, statutes.py, guidance.py, manifests.py
  normalize/    cases.py, laws.py, references.py, versions.py, validate.py
  extract/      case_features.py, diagnostic_rules.py, prompts/
  graph/        store.py, fact.py, ontology.py, rule.py, embeddings.py
  agents/       researcher.py, auditor.py, adjudicator.py, pipeline.py
  eval/         datasets.py, retrieval.py, judgment.py, ablation.py
  common/       schema.py, ids.py, provenance.py, llm_client.py
```

+ Adapter tương thích repo gốc: `case` → `facts/features/crime/law`; `law` → `entry/description/crimes/judge_dep/related_laws`.
+ Phần phiên bản điều luật và provenance là mở rộng của dự án Việt Nam; không được trình bày là schema gốc của tác giả.
+ Không sao chép code gốc không kiểm tra đầu vào; đặc biệt đoạn repo có `eval()` trên dữ liệu luật cần được thay bằng parser an toàn (`json.loads`/`ast.literal_eval` có kiểm tra schema).

## Các tệp thực thi được tạo lần lượt theo từng mốc

| Mốc | Tệp entrypoint đề xuất | Sản phẩm |
| --- | --- | --- |
| Khảo sát | `scripts/audit_sources.py` | `artifacts/metrics/data-audit.json` |
| Chuẩn bị | `scripts/prepare_data.py` | `data/staged/*.jsonl` |
| Chuẩn hóa | `scripts/normalize_data.py` | `data/normalized/*.jsonl` |
| Chia tập | `scripts/split_data.py` | `data/splits/*.jsonl` |
| Dựng graph | `scripts/build_graph.py` | `artifacts/graphs/*.pkl` |
| Chạy Agent | `scripts/run_agents.py` | `artifacts/predictions/*.jsonl` |
| Đánh giá | `scripts/evaluate.py` | `artifacts/metrics/*.json` và `.csv` |

## Quản lý trạng thái và tính lặp lại là yêu cầu bắt buộc

+ Ghi commit code, ngày chụp dataset, hash file, phiên bản model, seed, prompt hash, graph hash.
+ Ghi cả đầu vào, graph node IDs được truy xuất, điều kiện được kiểm tra và lý do loại bỏ.
+ Không đưa nội dung quyết định xét xử vào đầu vào dự đoán.
+ Không đưa test case vào graph corpus hoặc dữ liệu sinh prompt/tóm tắt cộng đồng.
+ Rà soát rủi ro thông tin cá nhân trong bản án công khai; không xuất dữ liệu nhạy cảm ra báo cáo.
+ Chỉ load pickle do chính pipeline của mình tạo hoặc nguồn đã kiểm chứng (pickle có rủi ro thực thi mã khi load).

## Nguồn kiểm chứng kiến trúc và cơ chế của bản gốc

+ [Paper ACL 2026](https://aclanthology.org/2026.acl-long.1738/).
+ [Repository](https://github.com/XMUDeepLIT/LegalGraphRAG).
+ [Graph database dùng NetworkX](https://github.com/XMUDeepLIT/LegalGraphRAG/blob/main/core/graph_construct/graph_db.py).
+ [Điều phối analyze_case](https://github.com/XMUDeepLIT/LegalGraphRAG/blob/main/core/utils/util.py).
+ [Researcher](https://github.com/XMUDeepLIT/LegalGraphRAG/blob/main/core/agents/researcher.py), [Auditor](https://github.com/XMUDeepLIT/LegalGraphRAG/blob/main/core/agents/auditor.py), [Adjudicator](https://github.com/XMUDeepLIT/LegalGraphRAG/blob/main/core/agents/adjudicator.py).

==> Tài liệu này mô tả kiến trúc đề xuất để tái lập, không tuyên bố đã triển khai hoặc đã đạt kết quả thí nghiệm.
