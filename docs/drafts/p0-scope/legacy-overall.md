# Tài liệu thiết kế lịch sử — cần đối chiếu

Nội dung sau được giữ để truy vết; không phải xác nhận đã triển khai.
Liên kết và cây thư mục cũ có thể đã thay đổi.

# Overview

## Mục tiêu của dự án là tái lập LegalGraphRAG trên dữ liệu hình sự Việt Nam

Dự án thuộc hướng A (tái lập nghiên cứu), không xây dựng hệ thống tự động ra phán quyết có hiệu lực. Mục tiêu là xây dựng tập tri thức tiếng Việt tương thích với ba lớp &lt;Fact Graph&gt;, &lt;Ontology Graph&gt;, &lt;Rule Graph&gt;; triển khai chuỗi &lt;Researcher → Auditor → Adjudicator&gt;; kiểm tra bằng benchmark không rò rỉ nhãn; và ghi lại kết quả đủ để tái lập.

==> Bản đầu tiên tập trung vào nhóm tội xâm phạm sở hữu, chưa bao phủ toàn bộ pháp luật Việt Nam.

## Phạm vi nghiên cứu được cố định trước khi xử lý dữ liệu

+ Miền chính: pháp luật hình sự Việt Nam.
  - Nhóm thử nghiệm: các tội xâm phạm sở hữu (ưu tiên các vụ việc thuộc Điều 168–175 BLHS, sau khi đối chiếu văn bản và phiên bản thích hợp).
  - Đơn vị đánh giá: một bị cáo trong một vụ án (một vụ án có thể có nhiều bị cáo và nhiều tội danh).
+ Đầu vào: tình tiết vụ án, không chứa phần nhận định/kết luận có thể làm lộ nhãn.
+ Đầu ra: tội danh ứng viên, điều luật/phiên bản áp dụng, lập luận có nguồn, hình phạt dự đoán (tác vụ tùy chọn).
+ Giới hạn: nghiên cứu hỗ trợ phân tích; không sử dụng để thay thế luật sư hoặc thẩm phán.

## Kiến trúc hệ thống gồm giai đoạn xây tri thức và giai đoạn suy luận

|| Sơ đồ logic (mô tả đề xuất, không phải deployment của repository gốc):

```text
OFFLINE
CBBA judgments ──► Ingest ──► Normalize ──► Case/Defendant labels ──┐
Official BLHS ────► Ingest ──► Normalize ──► Laws/Versions/Clauses ─────┤
Guidance/An le ──► Ingest ──► Verify ──► Interpretations/Links ────────┤
                                                                       ▼
           Feature extraction (LLM) + Checklists (LLM + review)
                                     │
                    Embedding (BGE-m3) + k-NN + communities
                                     │
                      HIERARGRAPH (one NetworkX graph)
                      Fact + Ontology + Rule knowledge
                                     │
ONLINE                               ▼
User/Tester ─► Query ─► Researcher ─► Auditor ─► Adjudicator ─► Evidence-backed result
                           │            │              │
                        Graph+embed    Law/rules      Reasoning LLM
```

==> &lt;Fact&gt;, &lt;Ontology&gt; và &lt;Rule&gt; là ba lớp chức năng, không nhất thiết là ba graph database độc lập.

## Tác nhân bên ngoài được tách khỏi các Agent nội bộ

+ &lt;User / Evaluator&gt;: cung cấp vụ án hoặc truy vấn, nhận kết quả và đánh giá.
+ &lt;Data Curator&gt;: lựa chọn nguồn, đối chiếu nhãn, phê duyệt phiên bản luật và checklist.
+ &lt;Researcher&gt;: chương trình truy xuất bằng chứng từ graph và embedding.
+ &lt;Auditor&gt;: chương trình kiểm tra điều kiện áp dụng điều luật, loại bỏ bằng chứng không đủ căn cứ.
+ &lt;Adjudicator&gt;: chương trình tổng hợp chứng cứ đã kiểm tra và gọi mô hình suy luận.
+ &lt;Embedding Model&gt;: công cụ tạo vector, không phải Actor hay Agent.
+ &lt;Reasoning LLM&gt;: mô hình phục vụ tác vụ LLM trong nhiều Agent; không yêu cầu fine-tune ba LLM riêng.

## Luồng xử lý trực tuyến dựa trên bằng chứng đã kiểm chứng

+ B1: nhận `query_id`, tình tiết vụ án và thông tin thời gian liên quan.
+ B2: xử lý theo bị cáo, trích xuất đặc trưng pháp lý từ câu truy vấn.
+ B3: Researcher tìm tương đồng, mở rộng community và truy xuất theo tội danh ứng viên.
+ B4: Auditor đối chiếu quy tắc, giải thích pháp lý, checklist và ngày hiệu lực.
+ B5: Adjudicator sinh kết luận có `evidence_ids`, `article_version_id`, phần giải thích.
+ B6: lưu trace, thời gian, token và kết quả cho đánh giá.

## Tổ chức source code mẫu tách dữ liệu khỏi thuật toán

|| Cây thư mục đề xuất cho dự án Việt Nam (chưa phải cây mã nguồn tác giả):

```text
vn-legalgraphrag/
├── docs/
│   ├── overall.md
│   ├── KB-build.md
│   ├── system.md
│   ├── sources.md
│   ├── prepare-data.md
│   ├── normalize-data.md
│   ├── build-graph.md
│   ├── agents.md
│   ├── benchmark.md
│   ├── evaluation.md
│   └── report.md
├── Others/
│   ├── config/          # sources.yaml, domain.yaml, models.yaml
│   ├── reports/
│   ├── skills/
│   └── tests/
├── src/vnlegal/
│   ├── ingest/
│   ├── normalize/
│   ├── extract/
│   ├── graph/
│   ├── agents/
│   ├── eval/
│   └── common/
├── scripts/
│   ├── audit_sources.py
│   ├── prepare_data.py
│   ├── normalize_data.py
│   ├── split_data.py
│   ├── build_graph.py
│   ├── run_agents.py
│   └── evaluate.py
├── data/
│   ├── raw/           # immutable; licensed local copies
│   ├── staged/        # parsed, unverified
│   ├── normalized/    # canonical JSONL
│   ├── enriched/      # features/checklists
│   ├── splits/        # graph/validation/test IDs
│   └── manifests/      # checksums, versions, QA
├── artifacts/
│   ├── graphs/
│   ├── retrieval/
│   ├── predictions/
│   └── metrics/
└── pyproject.toml
```

## Quy trình chung có các cổng kiểm soát chất lượng

+ P0 — Survey: chốt phạm vi luật, nguồn, giấy phép, schema và khả năng truy cập.
+ P1 — Audit: thống kê số bản án đúng miền, tỷ lệ đọc được và độ phủ nhãn.
+ P2 — Normalize: chuẩn hóa `case/defendant/law/version/article/charge`, truy vết nguồn.
+ P3 — Split: chống rò rỉ giữa graph corpus và test, xét cả sơ thẩm–phúc thẩm cùng vụ việc.
+ P4 — Enrich: trích xuất features và checklist, kèm kiểm tra chất lượng.
+ P5 — Graph: dựng Fact/Ontology/Rule, kiểm tra node/edge và sự thống nhất ID.
+ P6 — Agents: triển khai truy xuất → xác minh → tổng hợp, lưu trace.
+ P7 — Benchmark: chọn tập công khai cùng miền hoặc tạo LJP held-out từ bản án.
+ P8 — Evaluate: chạy baseline, ablation, metrics, phân tích lỗi và xuất report.

==> Chỉ chuyển sang P5 khi có báo cáo mapping luật, chất lượng nhãn và split đủ tin cậy.

## Danh mục tài liệu mô tả từng công đoạn

+ KB-build.md (đường dẫn lịch sử: `KB-build.md`): bốn chương về bối cảnh, nguồn dữ liệu, chuẩn hóa và dựng graph.
+ system.md (đường dẫn lịch sử: `system.md`): giao diện module, tương tác tác nhân, mô hình, kiến trúc kỹ thuật.
+ sources.md (đường dẫn lịch sử: `sources.md`): nguồn pháp luật, dataset, benchmark, truy cập, độ phủ, rủi ro.
+ prepare-data.md (đường dẫn lịch sử: `prepare-data.md`): tiếp nhận và khảo sát nguồn dữ liệu thô.
+ normalize-data.md (đường dẫn lịch sử: `normalize-data.md`): schema, liên kết ID, trích xuất và QA.
+ build-graph.md (đường dẫn lịch sử: `build-graph.md`): các bước tạo 3 graph, embedding và lưu trữ.
+ agents.md (đường dẫn lịch sử: `../agents.md`): nhiệm vụ, đầu vào/đầu ra và lời gọi Agent.
+ benchmark.md (đường dẫn lịch sử: `benchmark.md`): benchmark cùng miền và split chống leakage.
+ evaluation.md (đường dẫn lịch sử: `evaluation.md`): baseline, metrics, ablation và kiểm thử.
+ report.md (đường dẫn lịch sử: `report.md`): cấu trúc báo cáo, biểu đồ và bằng chứng thực nghiệm.

## Quy ước trình bày được kế thừa từ template của dự án

+ Heading 1 đặt một từ; Heading 2 và 3 nêu một ý chính.
+ Danh sách ưu tiên `+` và `-`, không quá ba mức.
+ Thuật ngữ trong dấu `<...>`; chú thích trong `(...)`.
+ Dòng `||` giới thiệu ví dụ; `==>` chốt ý chính của mục.
+ Liên kết dùng cú pháp Markdown để có thể nhấp trực tiếp (tương ứng quy tắc đánh dấu link trong template).
+ Tách dòng trống giữa heading, đoạn, danh sách và ví dụ.

## Nguồn nền tảng xác định hướng tái lập

+ Bài báo: [ACL 2026 — LegalGraphRAG](https://aclanthology.org/2026.acl-long.1738/).
+ Code gốc: [XMUDeepLIT/LegalGraphRAG](https://github.com/XMUDeepLIT/LegalGraphRAG).
+ Bản án: [CBBA trên Hugging Face](https://huggingface.co/datasets/tmquan/cbba-toaan-gov-vn).
+ Điều luật: [VBHN 135/VBHN-VPQH](https://chinhphu.vn/?classid=2629&docid=215260&pageid=27160).

==> Kiểm tra nguồn và giấy phép tại thời điểm triển khai; quy mô toàn bộ corpus không phải quy mô hình sự thực dùng.
