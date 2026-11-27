# Tài liệu thiết kế lịch sử — cần đối chiếu

Nội dung sau được giữ để truy vết; không phải xác nhận đã triển khai.
Liên kết và cây thư mục cũ có thể đã thay đổi.

# Knowledge

## Chương 1: Bối cảnh tái triển khai LegalGraphRAG cho pháp luật Việt Nam

### Bài toán gốc yêu cầu suy luận từ tình tiết sang kết luận có dẫn chứng

&lt;LegalGraphRAG&gt; là framework công bố tại ACL 2026, kết hợp &lt;Hierarchical Legal Graph&gt; và chuỗi <Researcher–Auditor–Adjudicator>. Phương pháp xử lý câu truy vấn mô tả vụ án, tìm bằng chứng, xác minh quy định phù hợp và tạo kết luận có thể truy vết. Nhiệm vụ chính trong bài báo là dự đoán tội danh, điều luật và thời hạn hình phạt từ tình tiết vụ án hình sự.

+ Khó khăn 1: các tài liệu khác cấp độ (vụ án, điều luật, diễn giải) không thể xử lý chỉ bằng đồ thị phẳng hoặc semantic similarity.
+ Khó khăn 2: những kết quả truy xuất giống câu hỏi nhưng không đúng điều kiện áp dụng sẽ làm suy luận sai.
+ Giải pháp gốc: Fact Graph + Ontology Graph + Rule Graph, truy xuất đa chiến lược và kiểm chứng từng điều kiện trước khi tổng hợp.

==> Tái lập phương pháp phải tái lập cả kiến trúc truy xuất và bước kiểm chứng, không chỉ dựng graph rồi hỏi LLM.

### Ba lớp graph phục vụ các kiểu tri thức khác nhau

+ &lt;Fact Graph&gt;: Case, Article, Offense và các quan hệ viện dẫn/định tội; nguồn chính là bản án.
+ &lt;Ontology Graph&gt;: đặc trưng chủ thể, hành vi, đối tượng tác động, trạng thái lỗi; embedding, k-NN, community.
+ &lt;Rule Graph&gt;: điều luật, hướng dẫn, các điều kiện cần kiểm tra để áp dụng; nguồn là văn bản quy phạm và hướng dẫn pháp lý.

|| Cách phân biệt trên một tình huống (không phải hồ sơ thật):

```text
Case C01: hành vi chiếm đoạt tài sản
  ├─ Fact: C01 --APPLIES--> Article A; C01 --CONVICTED_AS--> Charge X
  ├─ Ontology: C01 --SIMILAR_TO--> C28; C01 --IN_CLUSTER--> K03
  └─ Rule: Article A --HAS_CHECKLIST--> Checklist A; --GUIDED_BY--> Document G
```

### Phạm vi Việt hóa được chọn nhằm giữ tương đồng với nghiên cứu gốc

+ Chọn <Hình sự>: có thể nối tình tiết → tội danh → điều luật → hình phạt.
+ Bước đầu chọn <Tội xâm phạm sở hữu> (các Điều 168–175 BLHS sau kiểm tra phiên bản và phạm vi áp dụng).
+ Có thể mở rộng tập điều luật chung (lỗi, đồng phạm, quyết định hình phạt, tình tiết tăng/giảm) nếu thực sự xuất hiện trong vụ án.
+ Đánh giá theo một bị cáo, hỗ trợ nhiều tội danh; không suy đoán pháp luật hiện hành chỉ từ bản án cũ.

### Khác biệt giữa luật Việt Nam và luật Trung Quốc đòi hỏi thêm chuẩn hóa

+ Mọi điều luật phải gắn với văn bản, số điều, khoản/điểm và phiên bản có hiệu lực.
+ Phải tách `cited_article` khỏi `applied_article` (điều luật được nhắc đến chưa chắc là điều luật kết tội).
+ Phải tách phần `facts` khỏi `judgment` để không làm lộ nhãn khi kiểm thử.
+ Phải liên kết theo `defendant_id` trong vụ án nhiều bị cáo.
+ Checklist trích xuất bởi LLM là dữ liệu dự thảo, chỉ được chấp nhận sau kiểm tra nguồn và điều kiện pháp lý.

==> Mục tiêu của giai đoạn này là một KB phục vụ nghiên cứu; không kết luận một điều luật áp dụng khi thiếu dữ kiện hoặc không xác định được phiên bản.

## Chương 2: Khảo sát những nguồn dữ liệu có thể xây dựng ba Graph

### Các bản án đã công bố cung cấp phần lớn dữ liệu cho Fact và Ontology Graph

+ [CBBA — Vietnamese Court Judgments](https://huggingface.co/datasets/tmquan/cbba-toaan-gov-vn): 1.542.247 tài liệu toàn lĩnh vực trong bản phát hành có text gốc (không phải toàn bộ là hình sự); `category`, `doc_name`, `official_document_id`, `issued_date`, `markdown`, `citations_law`, `citations_case`, `web_url`.
  - Dùng cho Fact: case ID, tình tiết, nhãn tội danh, điều luật áp dụng và hình phạt (các nhãn phải trích xuất từ phần quyết định).
  - Dùng cho Ontology: trích xuất bốn nhóm đặc trưng từ tình tiết, không đưa phần phán quyết vào input.
  - Rủi ro: 26,6% nguồn PDF không có văn bản trích xuất được trong phát hành; lệch lĩnh vực, regex citation có lỗi; cần lọc hình sự và audit thực tế.
+ [Cổng công bố bản án chính thức](https://congbobanan.toaan.gov.vn/): kiểm chứng sample và nguồn gốc khi metadata hoặc kết quả trích xuất bất thường.
+ [Án lệ / bản án nguồn án lệ](https://huggingface.co/datasets/tmquan/anle-toaan-gov-vn): 1.844 bản ghi toàn miền; 9 bản ghi gắn cờ án lệ chính thức trong phiên bản phát hành; chỉ dùng bổ sung sau lọc hình sự.

### Văn bản quy phạm chính thức tạo lõi cho Rule Graph

+ [Bộ luật Hình sự — VBHN 135/VBHN-VPQH](https://chinhphu.vn/?classid=2629&docid=215260&pageid=27160): bản hợp nhất ngày 05/09/2025 để tra cứu văn bản hợp nhất ở mốc này.
+ [Luật 86/2025/QH15](https://vbpl.moj.gov.vn/bocongan/Pages/vbpq-toanvan.aspx?ItemID=179251&Keyword=): văn bản sửa đổi; đối chiếu quy định hiệu lực/chuyển tiếp khi dùng bản án lịch sử.
+ [Cơ sở dữ liệu VBPL Bộ Tư pháp](https://vbpl.moj.gov.vn/): văn bản gốc, sửa đổi, thông tin hiệu lực, dẫn chiếu cơ quan ban hành.
+ [Bộ Pháp điển điện tử](https://phapdien.moj.gov.vn/): tra cứu quy phạm được pháp điển hóa theo chủ đề/đề mục và nguồn văn bản.
+ [Pháp điển dataset](https://huggingface.co/datasets/tmquan/phapdien-moj-gov-vn): 65.967 dòng `documents` toàn ngành; `record_id`, `subject_id`, `article_id`, `content_text`, `source_note_text`, `source_links`.
  - Không join theo `article_id` đơn độc vì không duy nhất toàn cục; dùng `record_id`/key kết hợp và đối chiếu source.
  - Dùng làm tập trung gian; văn bản chính thức là nguồn xác minh cuối cùng.
+ [VLSP 2025 Legal Corpus](https://huggingface.co/datasets/longstnguyen/vlsp2025-legal-corpus): 56.810 văn bản đa ngành, `metadata + chunks` theo chương/điều; truy cập có điều kiện; tập đã lọc văn bản bị bãi bỏ ở thời điểm thu thập nên không dùng thay nguồn lịch sử.

### Hướng dẫn và liên kết pháp lý là nguồn bổ sung có điều kiện

+ [TANDTC — án lệ](https://anle.toaan.gov.vn/): liên hệ vụ án/án lệ/giải pháp pháp lý; phải phân biệt án lệ chính thức với bản án nguồn.
+ [VBPL — TANDTC](https://vbpl.moj.gov.vn/Toaannhandantoicao/Pages/Home.aspx): tìm nghị quyết hướng dẫn pháp luật hình sự có liên quan đến nhóm điều luật.
+ [VNLegalText](https://github.com/mlalab/VNLegalText): 5.031 văn bản đa ngành và 61.446 tham chiếu, có nhãn tham chiếu/sửa đổi/hướng dẫn/thay thế; dùng làm gợi ý cạnh, phải xác minh phạm vi hình sự.

### Bảng ánh xạ nguồn dữ liệu sang lớp graph

| Nguồn | Dữ liệu trích xuất | Graph | Trạng thái |
| --- | --- | --- | --- |
| CBBA | `case`, `defendant`, `fact`, `applied_articles`, `charges`, `penalty` | Fact | Ưu tiên; phải trích nhãn |
| CBBA | `features.defendant_info/criminal_acts/victim_property_details/intent_remorse` | Ontology | Cần LLM + QA |
| BLHS / VBPL | `document_id`, `article`, `clause`, `point`, `version`, `content` | Rule | Nguồn pháp lý chính |
| Hướng dẫn HĐTP | giải thích và điều kiện áp dụng | Rule | Chỉ nhập khi kiểm chứng được |
| VNLegalText | `AMENDS`, `REFERS`, `GUIDES`, `SUPERSEDES` | Rule | Nguồn quan hệ phụ |
| Án lệ | số án lệ, tình huống, giải pháp pháp lý | Fact/Rule | Giai đoạn mở rộng |

==> Quy mô công bố là tổng corpus, không phải số lượng có thể dùng cho tập hình sự đã chọn; số dùng thực tế phải do Data Audit xác định.

## Chương 3: Kế hoạch xây công cụ chuẩn hóa dữ liệu trước khi dựng Graph

### Tách nguồn thô thành những lớp dữ liệu có thể kiểm tra độc lập

+ `data/raw/`: bản gốc tải về, không chỉnh sửa; ghi phiên bản, checksum, giấy phép.
+ `data/staged/`: nội dung đọc/parse được, chưa duyệt nhãn.
+ `data/normalized/`: JSONL chuẩn hóa theo schema có provenance.
+ `data/enriched/`: đặc trưng pháp lý, checklist đã sinh và trạng thái QA.
+ `data/splits/`: `graph`, `dev`, `test` tách theo nhóm vụ việc.

### Các script tiếp nhận và thống kê dữ liệu

| Script đề xuất | Input | Output | Chức năng |
| --- | --- | --- | --- |
| `audit_sources.py` | danh mục nguồn | `data-audit.json` | đếm tài liệu theo loại, năm, tỷ lệ text, nhãn |
| `prepare_data.py` | raw Parquet/PDF/JSON | staged JSONL | tải, kiểm tra, chuẩn hóa Unicode, parse metadata |
| `normalize_data.py` | staged JSONL | normalized JSONL | trích fact và quyết định, cấu trúc theo bị cáo |
| `link_refs.py` | cases + laws | links JSONL | nối viện dẫn với `law_version_id` |
| `extract_features.py` | case facts | features JSONL | LLM sinh bốn chiều ontology, kèm span nguồn |
| `extract_checklists.py` | laws + guidance | checklist drafts | LLM trích điều kiện pháp lý, giữ nguồn và mức tin cậy |
| `validate_data.py` | normalized/enriched | QA reports | kiểm schema, trùng, ID sai, nhãn mâu thuẫn |
| `split_data.py` | dataset đã duyệt | manifests/splits | chống leakage và giữ phân phối tội danh |

### Chuẩn hóa danh tính văn bản và điều luật bằng khóa ổn định

+ `document_id`: số hiệu + cơ quan + loại + năm, kèm URL và checksum nguồn.
+ `law_version_id`: `document_id + effective_range + amendment_revision` (định nghĩa dự án).
+ `article_version_id`: `law_version_id + article_number + clause + point`.
+ `case_id`: ID nguồn + phiên bản tài liệu; `matter_group_id` để nhóm sơ thẩm/phúc thẩm cùng vụ việc.
+ `defendant_id`: định danh nội bộ trong case, không sử dụng họ tên thật làm khóa.
+ `charge_id`: bảng từ điển tội danh thống nhất, gắn điều luật và version.

### Việc trích xuất phải tránh rò rỉ đáp án từ bản án

+ Phát hiện phần tình tiết/sự kiện trước đoạn nhận định và quyết định của tòa.
+ Trích nhãn từ phần quyết định riêng, rồi đưa vào vùng dữ liệu không được truy xuất trong quá trình test.
+ Trường `facts` không chứa những dòng như "xử phạt", "tuyên bố phạm tội", "áp dụng Điều..." ở phần quyết định.
+ Không dùng `charges`/`applied_articles` từ chính query để xây query embedding trong test.
+ Không để test case tham gia tạo embedding, community summary hoặc graph edges.

### Chất lượng dữ liệu được kiểm tra theo tầng

+ L1: file parse được, encoding Unicode, JSON schema hợp lệ.
+ L2: ID duy nhất, không để trùng nguồn hoặc lặp case.
+ L3: điều luật tồn tại, đúng văn bản, mốc hiệu lực có nguồn kiểm chứng.
+ L4: câu trích dẫn được mapping sang đúng khoản/điểm.
+ L5: labels theo bị cáo khớp với quyết định xét xử (đánh giá mẫu thủ công).
+ L6: phân phối dữ liệu hợp lý và không có overlap graph/test.

|| Ví dụ dữ liệu chuẩn hóa ở mức case (minh họa, không phải bản án có thật):

```json
{
  "case_id": "case:00001",
  "matter_group_id": "matter:00001",
  "facts": "Văn bản tình tiết đã tách nhãn...",
  "defendants": [{
    "defendant_id": "def:00001",
    "charges": ["charge:theft"],
    "applied_article_version_ids": ["law:blhs:version-X:article-173"],
    "imprisonment_months": 18
  }],
  "source": {"dataset": "CBBA", "source_id": "...", "url": "..."},
  "label_status": "needs_review"
}
```

==> Chi tiết schema, rule kiểm chứng và lỗi thường gặp nằm trong [normalize-data.md](normalize-data.md).

## Chương 4: Kế hoạch xây dữ liệu Graph từ dữ liệu đã chuẩn hóa

### Các model hỗ trợ xây graph có vai trò khác nhau

+ &lt;GPT-4o-mini&gt; (hoặc LLM thay thế có kiểm tra đầu ra): trích xuất features và checklist dự thảo; không tự quyết định hiệu lực văn bản.
+ &lt;BGE-m3&gt;: mã hóa mô tả case/law/charge và query thành vector chung, dùng cho k-NN và semantic retrieval.
+ &lt;Qwen3-8B&gt;: reasoning backbone mặc định cho Agent trong thực nghiệm theo paper, không cần fine-tune ba mô hình riêng.
+ &lt;NetworkX MultiDiGraph&gt;: graph store nghiên cứu, phù hợp hướng code gốc; có thể chuyển Neo4j ở giai đoạn mở rộng nhưng không bắt buộc.

### Fact Graph liên kết vụ án, điều luật và tội danh đã chuẩn hóa

+ Nodes: `Case`, `Defendant` (mở rộng Việt hóa), `LawArticleVersion`, `Charge`.
+ Edges: `CASE_HAS_DEFENDANT`, `DEFENDANT_CONVICTED_AS`, `DEFENDANT_APPLIED_ARTICLE`, `ARTICLE_DEFINES_CHARGE`.
+ Trong adapter gốc: thu gọn thành `Cases`, `Laws`, `Crimes` cùng các cạnh gần tương ứng.
+ Quy tắc: mọi cạnh kết tội phải có `source_doc_id`, `source_span`, `extraction_method`, `verified`.

### Ontology Graph tổ chức các vụ án theo bản chất pháp lý

+ Input: bốn chiều `defendant_info`, `criminal_acts`, `victim_property_details`, `intent_remorse`.
+ Chuyển các chiều thành văn bản pháp lý nhất quán; tạo BGE-m3 embedding theo cùng model version.
+ k-NN kết nối các case tương đồng; cộng đồng được phát hiện trên các cạnh đã chọn.
+ Nodes: `Cases`, `Cluster`; Edges: `SIMILAR_TO`, `IN_COMMUNITY` (tên đề xuất, mapping theo code gốc).
+ Community summary phải sinh từ graph corpus, không xem test labels.

### Rule Graph cung cấp căn cứ và điều kiện kiểm chứng

+ Input: `LawArticleVersion`, `GuidanceDocument`, `DiagnosticChecklist`.
+ Bản tương thích code gốc: `judge_dep` và `related_laws` lưu trong thuộc tính Law Node.
+ Bản Việt hóa mở rộng: `GUIDED_BY`, `AMENDS`, `SUPERSEDES`, `HAS_CHECKLIST`, `EFFECTIVE_DURING` với provenance.
+ Không thêm cạnh quan hệ khi nguồn không xác nhận; liên kết mơ hồ phải có `needs_review`.

### Các Graph chia sẻ node ID và dùng chung một snapshot

|| Cấu trúc minh họa:

```text
[Case C01] ──APPLIES──► [LawArticleVersion A173-v1] ──DEFINES──► [Charge THEFT]
    │                          │
    ├──SIMILAR_TO──► [Case C08] ├──GUIDED_BY──► [Guidance G01]
    │                          └──HAS_CHECKLIST──► [Checklist D173]
    └──IN_COMMUNITY──► [Cluster K02]
```

### Agent tiêu thụ các lớp graph theo trách nhiệm

+ &lt;Researcher&gt;: dùng case feature/query embedding, tìm case gần nhất, mở rộng cluster, lấy điều luật/tội danh liên quan.
+ &lt;Auditor&gt;: lấy các checklist và guidance, kiểm từng điều kiện, loại luật không phù hợp.
+ &lt;Adjudicator&gt;: nhận case facts + verified evidence, tạo kết quả có trích dẫn và mức bất định.

### Xây graph theo thứ tự để kiểm tra được từng bước

+ B1: kiểm tra input schema, ID mapping và split.
+ B2: tạo Fact Graph từ quan hệ xác minh được; chạy invariant tests.
+ B3: sinh embedding, k-NN và communities; kiểm chất lượng hàng xóm.
+ B4: gắn Rule Graph theo version; duyệt một mẫu checklist.
+ B5: hợp nhất thành một `GraphSnapshot`, lưu checksum/version.
+ B6: chạy truy vấn mẫu và kiểm tra provenance của mọi câu trả lời.
+ B7: ghi số node, edge theo loại, độ phủ luật, orphan nodes, recall thử nghiệm.

## Chốt kế hoạch cần hoàn thành trước khi tăng quy mô

+ Chưa biết chính xác số bản án hình sự đủ nhãn sau lọc; phải làm Data Audit trước khi đặt mục tiêu cố định.
+ Benchmark chính phải là tập hình sự held-out theo vụ việc; benchmark QA đa ngành chỉ là phép đánh giá bổ sung.
+ Không sử dụng truy xuất luật hiện hành làm chuẩn tuyệt đối cho bản án lịch sử.
+ Nếu thiếu văn bản hướng dẫn, báo thiếu nguồn thay vì để LLM điền điều kiện pháp lý không kiểm chứng.

==> Tài liệu chi tiết tiếp nối: [sources.md](sources.md), [prepare-data.md](prepare-data.md), [normalize-data.md](normalize-data.md), [build-graph.md](build-graph.md), [agents.md](../agents.md), [benchmark.md](benchmark.md).

## Tài liệu tham khảo của kế hoạch

+ [Bài báo LegalGraphRAG tại ACL 2026](https://aclanthology.org/2026.acl-long.1738/).
+ [Repository LegalGraphRAG](https://github.com/XMUDeepLIT/LegalGraphRAG).
+ [CBBA](https://huggingface.co/datasets/tmquan/cbba-toaan-gov-vn).
+ [Bộ Pháp điển dataset](https://huggingface.co/datasets/tmquan/phapdien-moj-gov-vn).
+ [Bộ luật Hình sự VBHN 135/VBHN-VPQH](https://chinhphu.vn/?classid=2629&docid=215260&pageid=27160).
+ [VNLegalText](https://github.com/mlalab/VNLegalText).
