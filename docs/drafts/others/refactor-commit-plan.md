# Kế hoạch chia commit refactor

## Phạm vi đã được giao

Chuẩn bị nhánh office-khang từ origin/main, giữ nguyên dev-khang và công việc
local; commit theo từng phần độc lập, chưa merge main. Tiếp tục công việc KB
sau phần Git, vẫn giữ các điểm duyệt nội dung và ngân sách.

## Kiểm tra thực tế

- Nhánh local hiện tại: dev-khang; chưa có office-khang local.
- Lệnh git fetch origin bị chặn tại .git/FETCH_HEAD vì chỉ đọc.
- origin/main local trỏ tới f881358cd8752ad6ae5abc2b292e9e232bae75d0;
  đây là con trỏ local chưa fetch mới, không chứng minh HEAD remote hiện tại.
- Working tree có tài liệu sửa, skill cũ bị đánh dấu xóa và nhiều code chưa
  được track. Không được gom tất cả bằng git add . hoặc loại bỏ thay đổi đó.
- src/vnlegal/law_schema.py vẫn nạp schema từ Others/config/schemas/.
  Chưa thể chỉ mang src sang rồi tuyên bố repo chạy độc lập.

## Các nhóm commit dự kiến

| Nhóm | Sản phẩm | Phụ thuộc và kiểm tra |
| --- | --- | --- |
| Tài liệu/quy ước | Phân loại offices/drafts, ghi quyết định, README | Kiểm link; không liên kết tới file chưa đưa sang |
| Code nền và hợp đồng | Package, schema, config mẫu, prompt cần dùng | Sửa đường dẫn Others; kiểm import và validator |
| Tải dữ liệu HF | Downloader pin commit, kiểm hash, giải nén | Cần xác định manifest tương ứng official/draft; kiểm đường dẫn archive |
| Graph | Snapshot và builder, QA | Phụ thuộc hợp đồng và loader; test bằng fixture tổng hợp |
| Agent | Researcher, Auditor, Adjudicator, adapter model | Phụ thuộc graph và prompt; test offline, không gọi API thật |
| Tích hợp/tài liệu sử dụng | README và bản đồ gọi hàm | Chỉ ghi lệnh thực chạy; không tuyên bố hoàn thành KB |

Đây là nhóm công việc, không phải cam kết mỗi nhóm luôn độc lập để cherry-pick.
Khi có phụ thuộc phải ghi cụ thể trong commit/PR. Một nhóm có thể cần chia lại
để mỗi commit giữ được trạng thái chạy hợp lệ. Commit và PR viết tiếng Anh,
theo dạng A(B): C trong quy ước Git hiện có; nhánh office-khang theo yêu cầu mới.

## Kiểm tra trước commit/push

- Stage bằng danh sách file; kiểm toàn bộ nội dung staged, không chỉ gitignore.
- Không stage data/, Others/, cache, token, log API hoặc mẫu dữ liệu thật.
- Config đưa lên chỉ chứa tên biến môi trường và giá trị mẫu không bí mật.
- Di chuyển tài liệu được chọn sang docs, sửa liên kết và tên file. Giữ nguồn
  local để đối chiếu; không sửa snapshot dữ liệu bất biến trên HF.
- Không đổi tên module Python thành tên chứa dấu gạch ngang; dùng quy tắc
  định danh Python. File tài liệu và thư mục mới dùng chữ thường, dấu gạch ngang.
- Không merge main, không force push. Khi chọn riêng commit sang main, dùng
  nhánh tích hợp và cherry-pick sau khi kiểm phụ thuộc.

## Điểm tiếp tục KB

Nguồn đối chiếu hiện tại: Others/docs/p0-p9-task-plan.md và code src/vnlegal/.
JSON Task7 đã xuất nhưng nhãn theo bị cáo và facts an toàn cho suy luận chưa
được xác minh. Rule Graph compact hiện là literal/candidate, không phải KB
pháp lý đã hoàn thiện. Ontology và Fact cần dữ liệu enrichment đã được duyệt.

Sau Git: kiểm lại gates, trình đầu vào pilot Fact cần duyệt; chỉ chạy model
trong phạm vi token/chi phí được phép, đối chiếu evidence và schema, rồi mới
đề xuất mở rộng. Không dùng việc tiếp tục goal để coi mẫu input cũ đã accepted.

## Trạng thái

Đã chuẩn bị tài liệu; chưa refactor code, tạo nhánh, commit hoặc push do quyền
Git metadata. Không đánh dấu phần Git hay mục tiêu xây dựng KB là hoàn thành.

## Cập nhật phiên có quyền Git

Fetch thành công, origin/main ở e774ec6. Đã tạo office-khang trong
.worktrees/office-khang/; repo gốc vẫn ở dev-khang. Các ghi nhận bị chặn ở
trên là lịch sử. Commit đầu chuẩn bị tài liệu và quy ước; chưa merge main.
