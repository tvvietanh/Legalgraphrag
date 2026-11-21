# Sources

## Mục tiêu khảo sát là tìm nguồn dữ liệu hình sự có thể nối được với nhau

Chỉ nhận một nguồn sau khi xác minh: phạm vi hình sự; cấu trúc bản ghi; giấy phép/điều kiện truy cập; khóa nối sang corpus khác; mốc thời gian và chất lượng nhãn. Các con số bên dưới là số liệu công bố của toàn nguồn tại thời điểm khảo sát (21/11/2026), **không** phải số mẫu hợp lệ cho miền tội xâm phạm sở hữu.

## Nguồn bản án cung cấp đầu vào chính cho Fact Graph

### CBBA là kho bản án thô lớn nhất trong danh sách khảo sát

+ Nguồn: [tmquan/cbba-toaan-gov-vn](https://huggingface.co/datasets/tmquan/cbba-toaan-gov-vn).
+ Quy mô: 1.542.247 tài liệu trích xuất được lớp text (nhiều lĩnh vực); dữ liệu phát hành `documents` Parquet.
+ Field hữu ích: `doc_name`, `official_document_id`, `category`, `instance_level`, `issued_date`, `markdown`, `citations_law`, `citations_case`, `web_url`.
+ Dùng cho: tình tiết vụ án, trích dẫn, metadata, phân loại/đơn vị bị cáo, nhãn dự đoán tội danh/điều luật/hình phạt sau trích xuất.
+ Giấy phép trên card: CC BY 4.0; vẫn phải rà soát dữ liệu nhạy cảm.
+ Rủi ro: chỉ tài liệu đọc lớp text; regex citation/metadata có lỗi; phân bố không cân bằng; `category = Criminal` phải đo lại.
+ Kiểm tra ngay: filter theo `category`, tỷ lệ parse thành công, đủ nhãn, phân bố năm và điều luật, overlap sơ/phúc thẩm.

### Cổng công bố bản án là nguồn đối chiếu pháp lý

+ Nguồn: [Cổng công bố bản án TANDTC](https://congbobanan.toaan.gov.vn/).
+ Dùng cho: đối chiếu số hiệu, văn bản gốc, ngày tuyên và quyết định xét xử khi bộ trích xuất sai.
+ Không tự động coi đường dẫn còn truy cập được trong toàn bộ thời gian triển khai; lưu bản chụp và hash trong phạm vi giấy phép.

### Án lệ có thể cung cấp quan hệ bổ sung nhưng không phải nhãn LJP chính

+ Nguồn: [tmquan/anle-toaan-gov-vn](https://huggingface.co/datasets/tmquan/anle-toaan-gov-vn).
+ Quy mô: 1.844 tài liệu, trong đó 9 bản ghi được gắn `is_precedent = true` trong phát hành này.
+ Field: `precedent_number`, `is_precedent`, `markdown`, `citations_law`, `citations_case` và metadata bản án.
+ Dùng cho: quan hệ án lệ–bản án nguồn; chỉ lọc hình sự và đối chiếu từng án lệ với cổng TANDTC.
+ Không suy ra rằng Việt Nam chỉ có chín án lệ chính thức từ con số của dataset này.

## Nguồn luật chính thức cung cấp căn cứ để xây Rule Graph

### Bộ luật Hình sự cần được gắn phiên bản và hiệu lực

+ [VBHN 135/VBHN-VPQH, ngày 05/09/2025](https://chinhphu.vn/?classid=2629&docid=215260&pageid=27160): bản hợp nhất để tra cứu thuận tiện ở mốc công bố.
+ [Luật 86/2025/QH15](https://vbpl.moj.gov.vn/bocongan/Pages/vbpq-toanvan.aspx?ItemID=179251&Keyword=): thay đổi quy định cần xét hiệu lực và chuyển tiếp.
+ [CSDL VBPL](https://vbpl.moj.gov.vn/): kiểm chứng số văn bản, ngày, hiệu lực, văn bản hướng dẫn/sửa đổi.
+ Phạm vi trích: cấu trúc chương, điều, khoản, điểm; nội dung; ngày hiệu lực; liên kết sửa đổi; căn cứ áp dụng.
+ Quy tắc: trường hợp lịch sử phải dùng bộ quy định có thể áp dụng vào thời điểm pháp lý thích hợp; không chỉ lấy text mới nhất.

### Bộ Pháp điển cung cấp bản ghi luật đã phân đoạn

+ Dataset: [tmquan/phapdien-moj-gov-vn](https://huggingface.co/datasets/tmquan/phapdien-moj-gov-vn).
+ Quy mô: 65.967 dòng `documents` (nhiều ngành), 202 `subjects`, 42 `ontology_topics` theo card đang hiển thị.
+ Các field: `record_id`, `subject_id`, `topic_id`, `article_id`, `content_text`, `article_title`, `source_note_text`, `source_links`, `related_note_text`.
+ Dùng cho: text điều luật, phân cấp đề mục và gợi ý trích dẫn văn bản nguồn.
+ Cảnh báo schema: `article_id` không duy nhất trên toàn bộ bộ dữ liệu; dùng `record_id` và khóa gốc để nối.
+ Cổng đối chiếu: [Bộ Pháp điển chính thức](https://phapdien.moj.gov.vn/).

### VLSP Legal Corpus là nguồn thay thế khi cần phủ rộng pháp luật

+ Dataset: [longstnguyen/vlsp2025-legal-corpus](https://huggingface.co/datasets/longstnguyen/vlsp2025-legal-corpus).
+ Quy mô: 56.810 văn bản đa ngành (1954–2025), `metadata + chunks` theo điều/chương.
+ Truy cập: gated, cần cấp quyền, trích dẫn công trình theo điều kiện nguồn.
+ Rủi ro: đã lọc văn bản bị bãi bỏ/thay thế để phản ánh hiệu lực lúc thu thập; không đủ để phục dựng mọi phiên bản luật cho bản án lịch sử.
+ Vai trò: nguồn phụ; tránh nhập trùng với Pháp điển và văn bản chính thức.

## Nguồn quan hệ hỗ trợ Rule Graph và provenance

### VNLegalText hỗ trợ nhận diện tham chiếu giữa văn bản pháp luật

+ Nguồn: [mlalab/VNLegalText](https://github.com/mlalab/VNLegalText).
+ Quy mô: 5.031 văn bản đã tiền xử lý, 61.446 tham chiếu (nhiều ngành).
+ Nhãn quan hệ: `Is pursuant to`, `Refers`, `Expires`, `Supersedes`, `Amends or Supplements`, `Guides`, `No relationship`.
+ Dùng cho: tạo ứng viên cạnh văn bản–văn bản; lọc hình sự, đối chiếu pháp luật chính thức trước khi thêm.

### Hướng dẫn của Hội đồng Thẩm phán bổ trợ checklist pháp lý

+ Nguồn tìm kiếm: [VBPL — TANDTC](https://vbpl.moj.gov.vn/Toaannhandantoicao/Pages/Home.aspx).
+ Nguồn liên quan: [Cổng án lệ TANDTC](https://anle.toaan.gov.vn/).
+ Dùng cho: điều kiện áp dụng một điều/khoản, giải thích khái niệm, hướng dẫn hình phạt.
+ Mỗi đơn vị guidance cần `document_id`, `legal_scope`, `source_span`, `effective_range`, quan hệ tới điều luật.
+ Chưa có số lượng văn bản hướng dẫn hình sự được xác minh trong tập con; không điền số ước đoán.

## Benchmark công khai được khảo sát tách khỏi corpus xây graph

### Vietnamese Legal QA có nhãn điều luật phù hợp cho truy xuất

+ Nguồn: [nguyenthanhasia/vn-legal-qa](https://huggingface.co/datasets/nguyenthanhasia/vn-legal-qa).
+ Quy mô: 5.330 train + 592 test; legal corpus được card mô tả khoảng 207 MB.
+ Field: `question_id`, `question`, `relevant_articles[{law_id,article_id}]`.
+ Hạn chế: đa ngành và retrieval-based; chỉ dùng tập con hình sự có thể map đúng luật trong graph.

### DRiLL là benchmark tham chiếu cho bài toán tìm điều luật

+ Bài báo: [DRILL Shared Task 2025](https://aclanthology.org/2025.vlsp-1.16/).
+ Trang cuộc thi: [VLSP DRiLL](https://vlsp.org.vn/vlsp2025/eval/drill).
+ Bài toán: truy xuất những điều luật liên quan đến câu hỏi pháp luật tiếng Việt.
+ Hạn chế: cần kiểm tra split, bộ dữ liệu tải được và các cặp qrels còn nằm trong miền hình sự trước khi công bố điểm số.

### VLegal-Bench hữu ích cho kiểm thử kỹ năng suy luận

+ Nguồn: [CMC-OPENAI/VLegal-Bench](https://huggingface.co/datasets/CMC-OPENAI/VLegal-Bench).
+ Cấu trúc: 22 nhóm tác vụ trong 5 mảng, gồm recognition, structuring, verification, article prediction, decision prediction, multi-hop reasoning.
+ Hạn chế: một phần nhiệm vụ là trắc nghiệm/tình huống, không tương đương tập LJP bản án hình sự nhiều bị cáo.

## Kiểm tra khả năng liên kết nguồn theo một khóa luật chuẩn

+ Chọn `article_version_id` làm khóa chung thay vì chỉ `Điều 173`.
+ Với mỗi cạnh `case → article`, lưu nguồn trích, vị trí và phân loại `mentioned`/`applied`.
+ Với mỗi văn bản luật, lưu `source_document_id`, mốc hiệu lực và quan hệ bản sửa đổi.
+ Với án lệ, gắn số án lệ và phân biệt văn bản chính thức với nguồn án lệ.
+ Với benchmark, chỉ giữ qrels mà nguồn luật tương ứng có trong graph và thống kê tỷ lệ match.

## Bảng quyết định lựa chọn nguồn theo giai đoạn

| Nguồn | POC 200 mẫu | Graph 10k+ | Benchmark | Ưu tiên |
| --- | --- | --- | --- | --- |
| CBBA | Có | Có khi vượt QA | Có thể tạo held-out LJP | Bắt buộc |
| VBHN + VBPL | Có | Có | Ground truth luật | Bắt buộc |
| Bộ Pháp điển | Có | Có sau khử trùng | Có thể đánh giá retrieval | Cao |
| Nghị quyết/hướng dẫn | Có nếu tìm đúng | Có theo phạm vi | Kiểm chứng checklist | Cao |
| VNLegalText | Không bắt buộc | Có | Đánh giá quan hệ phụ | Trung bình |
| Án lệ | Không bắt buộc | Có | Kiểm tra nguồn án lệ | Trung bình |
| VLSP Corpus | Nguồn dự phòng | Có nếu được cấp quyền | Corpus retrieval phụ | Tùy chọn |
| Vietnamese Legal QA | Không dựng KB | Không | Đánh giá retrieval phụ | Cao |
| DRiLL / VLegal-Bench | Không dựng KB | Không | Đánh giá phụ | Trung bình |

==> Báo cáo Data Audit mới quyết định số lượng hình sự thực dùng; không nhầm giữa quy mô corpus gốc và quy mô dữ liệu phù hợp.
