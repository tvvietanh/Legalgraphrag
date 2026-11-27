# Kiểm tra refactor và bàn giao Git

## Quyền và nhánh

Đã fetch origin và tạo office-khang từ e774ec6 trong .worktrees/office-khang.
Repo gốc vẫn dev-khang; không reset/stash hoặc sửa thay đổi local của người dùng.
Không merge main. Các ghi nhận read-only trong chat trước là lịch sử đã giải quyết.

## Các phần đã commit

1. Tài liệu/quy ước: docs/offices tiếng Anh; docs/drafts tiếng Việt, thêm others.
2. Normalize và schema: 123 tests offline đạt.
3. Graph và reader: 165 tests tích lũy đạt.
4. Agent/model/setup: 294 tests tích lũy đạt; bỏ hai probe chỉ đọc corpus local.
5. Tải HF: 8 tests mới, tổng 303 tests offline đạt; mặc định plan-only.

Schema JSON có tên dùng dấu gạch ngang; module và file test Python giữ
snake_case để import. Các field/ID trong hợp đồng dữ liệu không đổi chỉ vì
đổi quy ước tên file. Script Python được import bởi test giữ tên cũ khi cần.

## Phạm vi và giới hạn

Không đưa data/, Others/, .hf/, credentials thật, corpus, graph output hoặc
log API vào Git. Config mẫu chỉ lưu tên biến môi trường; file example khóa rỗng.
Các pipeline thu thập/OCR và script review một lần vẫn ở local cũ, chưa tự
mang toàn bộ sang repo code hệ thống. Tài liệu lịch sử được đánh dấu draft;
liên kết cũ không tồn tại được chuyển thành đường dẫn lịch sử dạng chữ.

Đã kiểm module/CLI bằng offline tests; chưa chạy LLM, chưa tải lại dữ liệu
private hoặc model. Chưa chứng minh đủ ba lớp KB hay đánh giá end-to-end.
Công cụ restore có thể để lại các file hợp lệ đã khôi phục khi lỗi giữa chừng;
không ghi đè sửa tay. Receipt dùng để đối chiếu, không phải nghiệm thu pháp lý.

## Tiếp tục sau Git

Duyệt input/prompt/schema pilot Fact còn là gate nội dung. Không tự coi
quyền tiếp tục goal là duyệt mẫu hoặc cấp budget API. Bước kỹ thuật tiếp
theo có thể kiểm manifest/span và chuẩn bị bảng review gắn nguồn trong HF.
Commit hash xem git log; trạng thái push phải dựa vào kết quả remote thực tế.

Preflight cấu hình remote trả configuration_incomplete vì không có biến môi
trường trong worktree mới, exit 2 đúng dự kiến; network_called=false. Không
sao chép credential từ repo cũ. Đã kiểm help CLI và link Markdown nội bộ.

## Kết quả Git thực tế

Đã tạo sáu commit riêng: 4dae9f9 (tài liệu), 63ce97c (normalize/schema),
8a451da (graph), 11bb229 (agent), e4753d2 (tải HF), 1c2de6c (kiểm tích hợp).
Đã rà 116 tệp code/tài liệu: không có data/, Others/, cache, token theo các
mẫu khóa phổ biến hoặc tệp lớn hơn 1 MiB. Kiểm này không thay thế review
bảo mật toàn diện. Toàn bộ 303 tests offline đạt.

Lệnh git push -u origin office-khang chưa thành công: môi trường không có
credential HTTPS, báo could not read Username. gh không được cài; không cài
gói hệ thống hoặc đọc kho khóa của người dùng. ls-remote chưa thấy nhánh
office-khang trên origin. Chưa tạo PR hoặc merge main.

Người dùng có thể push các commit đã có bằng terminal Git đã đăng nhập, tại
.worktrees/office-khang/. Không cần tạo lại nhánh hoặc chép lại dữ liệu.
Chưa tiếp tục chạy model xây KB vì phần Git chưa bàn giao remote và mẫu
input Fact/chi phí request vẫn cần duyệt theo quy tắc hiện có.
