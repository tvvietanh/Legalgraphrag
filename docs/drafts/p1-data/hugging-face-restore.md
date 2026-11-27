# Khôi phục dữ liệu từ Hugging Face

Script scripts/download-dataset.py gọi vnlegal.datasets.restore. Mặc định
chỉ in plan offline. --download mới truy cập repo private, dùng HF_HOME của
worktree (.hf/) hoặc biến HF_TOKEN đã được người dùng cấp; không in token.
Phiên đăng nhập ở repo cũ không tự đồng nghĩa worktree mới đã đăng nhập.

Commit nguồn cố định: b45aeda06cbba853271106b319e5e516bf252028.
Kiểm SHA manifest bố cục trước, sau đó kiểm size/hash từng gói. JSON bản án
được đọc lại đối chiếu manifest sau giải nén. Chỉ tải các nhóm yêu cầu; không
tải model. Không có thao tác upload hoặc sửa Hugging Face.

Nhóm laws/cases/precedents khôi phục TXT official vào các đường dẫn logic
workspace mà JSON đang tham chiếu. Nhóm structured khôi phục JSON draft và
tạo pointer local có hash. rule là snapshot candidate; pilot là input review,
không phải output mô hình. Muốn chạy CompactRelease.cases cần cả structured
và cases; compact Rule cần structured, laws và precedents.

Ví dụ (chạy từ root worktree, sau khi tự đăng nhập HF):

```bash
python scripts/download-dataset.py
python scripts/download-dataset.py --groups laws precedents structured --download
```

Không có dữ liệu thật được đóng gói trong code. Không ghi đè bản chỉnh tay:
file tồn tại giống hash được giữ; khác hash thì dừng. Nếu lỗi giữa chừng,
có thể đã có một phần dữ liệu khôi phục; đọc receipt/log trước khi chạy lại.
Một lần khôi phục không phải giao dịch atomic cho toàn corpus. Archive được
kiểm header, không cho đường dẫn ngoài đích, symlink hoặc thành viên trùng.

Đã chạy 8 kiểm thử mới cho mapping, manifest/hash, archive và bảo toàn sửa tay;
tổng 302 kiểm thử offline đạt. Chưa thực hiện download tích hợp trên repo private.
