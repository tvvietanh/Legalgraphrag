# Báo cáo P<N> — <Tên giai đoạn>

## Thông tin và phạm vi

- Trạng thái giai đoạn: planning / in_progress / awaiting_review / accepted.
- Owner dữ liệu: <vai trò hoặc tên đã biết>.
- Owner hệ thống: <vai trò hoặc tên đã biết>.
- Nhánh / base commit lúc bắt đầu: <giá trị thực tế>.
- Cập nhật: <ngày giờ và múi giờ>.
- Yêu cầu và phạm vi được giao: <nội dung>.
- Tiêu chí hoàn thành giai đoạn: <điều kiện kiểm chứng được>.

## Đầu vào và chuẩn bị

| Đầu vào / phụ thuộc | Đường dẫn, phiên bản | Trạng thái thực tế | Owner / cách giải quyết |
| --- | --- | --- | --- |
| <đầu vào> | <path/version> | <sẵn sàng hoặc thiếu> | <owner> |

## Kế hoạch từng phần

| Task ID | Owner | Việc cần làm / file dự kiến | Đầu ra và tiêu chí nghiệm thu | Phụ thuộc | Trạng thái |
| --- | --- | --- | --- | --- | --- |
| P<N>-01 | <owner> | <phạm vi nhỏ> | <sản phẩm và cách kiểm tra> | <ID hoặc không> | planned |

## Nhật ký xác nhận

Ghi xác nhận thực tế của người dùng; không điền sẵn đồng ý. Tách cho phép thực hiện, nghiệm thu và phê duyệt Git.

| Thời điểm | Người / vai trò | Task hoặc HEAD | Loại xác nhận | Nội dung và giới hạn |
| --- | --- | --- | --- | --- |

## Kết quả từng phần

### P<N>-01 — <Tên task>

- Đã thực hiện: <thay đổi thực tế; chưa làm thì ghi chưa thực hiện>.
- Đầu ra: <đường dẫn từ root repo, schema/version/hash khi có>.
- Validation: <lệnh thực tế, pass/fail/chưa chạy và lý do>.
- Bằng chứng: <file log, số liệu, source span hoặc diff liên quan>.
- Giới hạn / lỗi / phần còn thiếu: <nội dung>.
- Nghiệm thu: <đang chờ hoặc xác nhận thực tế>.

## Bàn giao giữa hai người

| Bên giao → bên nhận | Artifact / hợp đồng | Phiên bản | Kiểm tra phía nhận | Trạng thái |
| --- | --- | --- | --- | --- |

## Quyết định và vấn đề còn mở

| Thời điểm | Vấn đề / thay đổi | Quyết định, người xác nhận | Ảnh hưởng / bước tiếp theo |
| --- | --- | --- | --- |

## Git và tích hợp

- Phạm vi file/commit: <danh sách cụ thể>.
- Kết quả kiểm tra trước commit: <kết quả thực tế>.
- Commit hash: xem Git history nếu báo cáo nằm trong chính commit đó.
- Phê duyệt push/PR: <chưa có hoặc người duyệt, HEAD, phạm vi>.
- Push / PR / merge: <chưa thực hiện hoặc kết quả thực tế và link>.
- Nếu cập nhật mục này sau commit: <ghi rõ thay đổi báo cáo chưa commit khi có>.

## Điểm tiếp tục

- Task hiện tại và trạng thái: <ID/state>.
- Đang chờ: <xác nhận / đầu vào / kiểm tra nào>.
- Bước tiếp theo: <hành động cụ thể trong phạm vi đã duyệt hoặc đề xuất cần duyệt>.
