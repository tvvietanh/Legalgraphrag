# Tài liệu thiết kế lịch sử — cần đối chiếu

Nội dung sau được giữ để truy vết; không phải xác nhận đã triển khai.
Liên kết và cây thư mục cũ có thể đã thay đổi.

# Preparation

## Mục tiêu bước chuẩn bị là tạo dữ liệu thô có thể truy vết và khảo sát được

Đầu vào là dataset bản án, văn bản luật và hướng dẫn. Đầu ra là bản ghi thô/staged có metadata thống nhất và báo cáo khả thi. Chưa trích xuất ontology features, chưa tạo embedding và chưa xây graph ở bước này.

## Chọn phạm vi và tiêu chí lọc trước khi tải dữ liệu lớn

+ `domain.yaml`: `criminal`, tập điều luật mục tiêu, phiên bản luật, khoảng năm khảo sát.
+ Lọc `category == Criminal` trong CBBA (giá trị thực được đối chiếu schema tại thời điểm tải).
+ Ưu tiên bản án đọc được phần tình tiết, có phần quyết định và có nguồn gốc xác minh.
+ Giai đoạn thử nghiệm: 200–300 bản án; giai đoạn sau kiểm kê toàn bộ phần hình sự hợp lệ.
+ Lưu danh sách `selected_case_ids` để tái lập.

## Tổ chức các file Python phục vụ ingest và audit

| Tệp đề xuất | Hàm chính | Input | Output |
| --- | --- | --- | --- |
| `src/vnlegal/ingest/cbba.py` | `iter_criminal_judgments()` | CBBA Parquet | staged cases JSONL |
| `src/vnlegal/ingest/statutes.py` | `iter_law_articles()` | BLHS / Pháp điển | staged laws JSONL |
| `src/vnlegal/ingest/guidance.py` | `iter_legal_guidance()` | VBPL/TANDTC | staged guidance JSONL |
| `src/vnlegal/ingest/manifests.py` | `write_manifest()` | source metadata | sha256 manifest |
| `scripts/audit_sources.py` | `main()` | source config | audit CSV/JSON |
| `scripts/prepare_data.py` | `main()` | raw files | staged JSONL |
| `src/vnlegal/common/provenance.py` | `attach_source()` | record + origin | record with trace |

## Quá trình thu thập giữ nguyên bản gốc và thống nhất metadata

+ B1: lưu dataset ID, commit/revision hoặc ngày tải, license, access method.
+ B2: tải có giới hạn/stream theo phần; kiểm checksum và đếm bản ghi.
+ B3: chỉ đọc/trích văn bản nguồn, không sửa nội dung gốc trong `data/raw/`.
+ B4: chuyển sang `data/staged/{cases,laws,guidance}.jsonl`, chuẩn hóa Unicode NFC.
+ B5: ghi mỗi bản ghi kèm `source_dataset`, `source_url`, `source_id`, `snapshot_date`, `raw_hash`.
+ B6: sinh báo cáo phân bố theo `category`, `year`, `instance_level`, `article-citation` và tỷ lệ lỗi.

|| Manifest nguồn minh họa:

```json
{
  "source_name": "tmquan/cbba-toaan-gov-vn",
  "snapshot_date": "2026-11-21",
  "revision": null,
  "license": "CC-BY-4.0 (theo dataset card, phải kiểm tra lại)",
  "document_count_raw": null,
  "document_count_criminal": null,
  "sha256": null,
  "note": "Chưa có số liệu audit sau lọc"
}
```

## Thống kê kiểm toán phải dựa trên dữ liệu đã tải thực tế

+ Tổng bản án tải và tỷ lệ đủ lớp text.
+ Tổng bản án `Criminal`, phân bố sơ thẩm/phúc thẩm/giám đốc thẩm.
+ Số bản án có `citations_law`, có phần nhận định/quyết định và có thể nhận diện bị cáo.
+ Số bản án liên quan Điều 168–175 và phân bố theo từng điều.
+ Số văn bản luật và hướng dẫn có thể ánh xạ theo phiên bản.
+ Số lỗi URL/metadata, số tài liệu trùng và mức độ cần xử lý thủ công.

## Quy tắc đạo đức và sử dụng dữ liệu phải được kiểm tra ngay

+ Giấy phép phát hành lại không đảm bảo mọi thông tin cá nhân an toàn để sử dụng tiếp.
+ Không công khai bản ghi chứa danh tính, địa chỉ, thông tin cá nhân nhạy cảm.
+ Ghi chính sách lưu trữ, thời hạn giữ và người có quyền truy cập.
+ Tách test set và log chạy LLM; cân nhắc không gửi nguyên văn bản án có dữ liệu nhạy cảm tới API bên ngoài.

## Điều kiện hoàn thành bước chuẩn bị là báo cáo khả thi có số liệu

+ Có `source-manifest.json` với thông tin nguồn và phiên bản.
+ Có `data-audit.json` và `data-audit.csv` phản ánh số đếm sau lọc.
+ Có mẫu 200–300 bản án staged để kiểm tra extraction.
+ Có danh sách lỗi/thiếu nguồn và quyết định tiếp tục hoặc thu hẹp miền.

==> Nếu nhãn bản án không đủ để tạo held-out benchmark, không tăng số lượng tải chỉ để có corpus lớn hơn.

## Tài liệu tham khảo cho bước ingest

+ [CBBA dataset card](https://huggingface.co/datasets/tmquan/cbba-toaan-gov-vn).
+ [Bộ Pháp điển dataset](https://huggingface.co/datasets/tmquan/phapdien-moj-gov-vn).
+ [Bộ luật Hình sự hợp nhất](https://chinhphu.vn/?classid=2629&docid=215260&pageid=27160).
+ [CSDL VBPL](https://vbpl.moj.gov.vn/).
