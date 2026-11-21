# Graph

## Mục đích xây graph là tổ chức tri thức đã chuẩn hóa thành ba lớp truy vấn được

Bước này chỉ nhận dữ liệu đã qua kiểm soát nhãn, provenance và split. Snapshot xây từ tập &lt;graph corpus&gt; không có case thuộc test. Ba lớp Fact/Ontology/Rule chia sẻ không gian định danh; bản đầu dùng `NetworkX MultiDiGraph` giống phong cách repo gốc.

## Fact Graph được xây từ quan hệ đã xác minh

+ Nodes: `Cases`, `Laws`, `Crimes` để tương thích code gốc.
+ Mở rộng đề xuất: `Defendant`, `LawArticleVersion`, `LegalDocument`, `Guidance`.
+ Edges gốc liên quan: `RELATES_TO_LAW` và `RELATED_CRIME`.
+ Edges Việt hóa: `DEFENDANT_APPLIED_ARTICLE`, `DEFENDANT_CONVICTED_AS`, `ARTICLE_DEFINES_CHARGE`.
+ Thuộc tính edge: `source_id`, `source_span`, `confidence`, `status`, `legal_version`, `extraction_version`.

|| Mẫu liên kết theo chuẩn nghiên cứu:

```text
Case C01
   └─ HAS_DEFENDANT → Defendant D01
         ├─ CONVICTED_AS → Charge X
         └─ APPLIED_ARTICLE → BLHS Rev01 / Article 173
                                      └─ DEFINES → Charge X
```

### Tệp xây Fact Graph lấy quan hệ từ normalized JSONL

+ `src/vnlegal/graph/fact.py`: `add_case_nodes`, `add_law_nodes`, `add_charge_nodes`, `add_fact_edges`.
+ Không tạo `APPLIED_ARTICLE` từ `citations_law` nếu chưa xác nhận điều luật được áp dụng cho đúng bị cáo.
+ Không bỏ `Defendant` khi đánh giá multi-defendant; adapter gốc có thể flatten từ mức defendant thành case theo yêu cầu.

## Ontology Graph được tạo từ đặc trưng pháp lý và vector

+ Từ `cases_with_features.jsonl`, chuẩn hóa text bốn nhóm feature theo thứ tự cố định.
+ Tạo BGE-m3 embedding cho case/charge/law description, giữ model revision và embedding dimension.
+ Xây k-NN cho case vectors (bắt đầu `top_k=3` để gần cấu hình tác giả; tham số hóa và kiểm tra).
+ Tạo `SIMILAR_TO` edges kèm `similarity` và `embedding_version`.
+ Phát hiện community; dùng Louvain khi bám vào hàm repo hiện có, hoặc Leiden nếu muốn theo mô tả paper (phải báo cáo khác biệt).
+ Tạo `Cluster` nodes có summary chỉ từ graph corpus.

### Việc đánh giá embedding cần thực hiện trên dữ liệu tiếng Việt

+ So sánh BGE-m3 với ít nhất một multilingual/tiếng Việt embedding baseline nếu tài nguyên cho phép.
+ Kiểm tra nearest neighbors có giống về yếu tố pháp lý, không chỉ các từ/cụm từ giống nhau.
+ Định kỳ lưu các cặp hard negative (điều luật tương tự nhưng khác điều kiện áp dụng).
+ Không sử dụng embedding có sẵn của CBBA (Nemotron 4096-D) trộn trực tiếp với vector BGE-m3; nếu thay model phải embed lại toàn bộ tập được so sánh.

## Rule Graph được xây từ luật và hướng dẫn đã kiểm tra

+ `LawArticleVersion`: text, clause/point, effective range, nguồn văn bản.
+ `DiagnosticChecklist`: câu hỏi điều kiện, nguồn, trạng thái duyệt.
+ `JudicialGuidance`: đoạn giải thích được pháp lý hóa và link tới điều luật.
+ `AMENDS`/`SUPERSEDES`/`GUIDES` chỉ được thêm nếu nguồn xác minh được quan hệ.
+ Trong adapter gốc, `judge_dep`, `related_laws`, `insights` có thể là thuộc tính Law Node; bản mở rộng có thể thêm node riêng.

|| Ví dụ rule đã duyệt (không phải điều kiện pháp lý thực):

```json
{
  "article_version_id": "law:blhs:rev01:art173",
  "checklist": [
    {"q": "Điều kiện số 1 đã nêu trong nguồn?", "source_id": "guide:001", "approved": true}
  ],
  "effective_from": null,
  "effective_to": null
}
```

## Hợp nhất ba lớp không tạo ba bản sao của cùng một điều luật

+ `GraphStore` quản lý một `nx.MultiDiGraph` và namespace ID chung.
+ Fact dùng `Cases`, `Laws`, `Crimes`; Ontology thêm tương đồng/cluster; Rule làm giàu Law Node và liên kết guidance.
+ Khi một Law xuất hiện trong nhiều nguồn, hợp nhất theo `article_version_id`, không theo tên điều luật.
+ Ghi edge provenance tách biệt để Auditor có thể lần ngược source.

## Tệp Python được xây theo thứ tự có thể chạy độc lập

| Tệp đề xuất | Hàm/chức năng | Đầu ra |
| --- | --- | --- |
| `src/vnlegal/graph/store.py` | `GraphStore.add_node/add_edge/save/load` | graph snapshot |
| `src/vnlegal/graph/fact.py` | `build_fact_graph()` | fact nodes/edges |
| `src/vnlegal/graph/embeddings.py` | `embed_nodes()` và cache | vector store |
| `src/vnlegal/graph/ontology.py` | `build_knn_edges()`, `build_communities()` | similar/cluster |
| `src/vnlegal/graph/rule.py` | `attach_rules_and_guidance()` | law/checklists |
| `src/vnlegal/graph/validate.py` | `graph_invariants()` | graph QA |
| `scripts/build_graph.py` | orchestration CLI | `artifacts/graphs/vn_hierargraph.pkl` |

## Luồng chạy build phải có báo cáo sau từng lớp

+ P1: nạp `normalized/` và `enriched/` theo split `graph`.
+ P2: sinh `Fact Graph`, đếm node/edge/orphan, so với nhãn chuẩn.
+ P3: embed và cache vectors, đối chiếu độ dài vector, kiểm tra NaN/zero vectors.
+ P4: k-NN, community và summary; báo thống kê size/cộng đồng.
+ P5: gắn Rule properties, checklist và phiên bản luật.
+ P6: đánh giá invariants và lưu snapshot có checksum.
+ P7: chạy smoke queries và kiểm tra đường đi tới điều luật đúng.

## Bộ kiểm thử ngắn bảo vệ chất lượng graph

+ Một `defendant_id` phải trỏ tới đúng `case_id`.
+ Mọi `applied_article_version_id` phải tồn tại ở Rule/Fact hoặc bị loại khỏi graph chờ duyệt.
+ Mọi `in_cluster` chỉ trỏ đến Case trong graph corpus.
+ Không có node từ test/validation trong graph (bao gồm summary được sinh từ chúng).
+ Mọi checklist dùng cho Auditor phải `approved = true`.
+ Mọi cited edge phải giữ `source_id`.
+ Tất cả embeddings so sánh với nhau phải từ cùng model/revision.

## Nguồn kỹ thuật đối chiếu với repository gốc

+ [feature_graph.py](https://github.com/XMUDeepLIT/LegalGraphRAG/blob/main/core/graph_construct/feature_graph.py): ba lớp ghi vào một graph.
+ [graph_db.py](https://github.com/XMUDeepLIT/LegalGraphRAG/blob/main/core/graph_construct/graph_db.py): `nx.MultiDiGraph`, embeddings và pickle.
+ [fact_graph.py](https://github.com/XMUDeepLIT/LegalGraphRAG/blob/main/core/graph_construct/fact_graph.py).
+ [ontology_graph.py](https://github.com/XMUDeepLIT/LegalGraphRAG/blob/main/core/graph_construct/ontology_graph.py).
+ [rule_graph.py](https://github.com/XMUDeepLIT/LegalGraphRAG/blob/main/core/graph_construct/rule_graph.py).
+ [Bài báo](https://aclanthology.org/2026.acl-long.1738/): Leiden ở phần mô tả phương pháp, Louvain trong hàm `detect_communities` của mã nguồn đã kiểm tra.

==> Trước khi chạy full Agent, yêu cầu một truy vấn mẫu phải giải thích được từng node/edge và nguồn của điều luật được trích.
