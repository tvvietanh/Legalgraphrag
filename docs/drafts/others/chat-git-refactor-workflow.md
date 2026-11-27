# Thảo luận tổ chức repo và refactor theo commit

## Vấn đề

Nhánh phát triển và thư mục local có nhiều thay đổi so với main. Cần đưa code
hệ thống lên GitHub, giữ dữ liệu trên Hugging Face, đồng thời có thể kiểm tra,
hoàn tác và tích hợp từng phần độc lập.

## Hướng của người dùng

- Dùng nhánh `office-khang` để lưu refactor chưa chốt; chưa merge vào main.
- Chia commit theo nhiệm vụ: tài liệu, code nền, tải dữ liệu, graph, agent…
- GitHub lưu code, cấu hình mẫu, schema, prompt, kiểm thử và tài liệu.
- Không đưa dữ liệu thật, đầu ra chạy, khóa, cache hoặc toàn bộ Others lên GitHub.
- `docs/offices/` chứa tài liệu chính thức bằng tiếng Anh.
- `docs/drafts/` chứa tài liệu phát triển bằng tiếng Việt, chia theo pN.
- `docs/drafts/others/` chứa thảo luận không thuộc giai đoạn cụ thể, bằng tiếng Việt.
- Tên chat là `chat-<chu-de>.md`; tên file/thư mục mới viết thường, dùng dấu gạch ngang.
- README ngắn: giới thiệu, hướng dẫn cài đặt, thiết kế cơ bản, cấu trúc source code.
  Hướng dẫn chạy local chi tiết được viết sau.

## Gợi ý của ChatGPT

- Tạo office-khang từ origin/main trong worktree riêng, giữ nguyên dev-khang
  và các thay đổi local. Chỉ đưa từng nhóm code/tài liệu cần thiết sang.
- Mỗi commit có chức năng rõ ràng và kiểm tra phù hợp; ghi phụ thuộc giữa các commit.
- Muốn đưa riêng K1 vào main khi office-khang đã tới K4: tạo nhánh tích hợp
  từ main, cherry-pick K1 và tạo PR riêng. Cherry-pick tạo commit mới.
- Merge toàn bộ office-khang sẽ đưa tất cả thay đổi chưa có trong main.
- Không coi commit nào cũng độc lập: commit dùng code từ phần trước phải mang
  theo phụ thuộc hoặc được tách lại trước khi tích hợp.
- Dùng revert để hoàn tác commit đã chia sẻ; không reset lịch sử hoặc force push.
- Lệnh tải dữ liệu HF cần pin phiên bản/commit và kiểm hash trước khi sử dụng.

## Thống nhất

Người dùng đã yêu cầu tiến hành theo cách chia nhánh và commit từng phần,
đồng thời lưu thảo luận tại docs/drafts/others. Không merge main trong đợt này.
Quy định mới về nhánh, ngôn ngữ và vị trí tài liệu ưu tiên hơn tài liệu cũ.
Tên offices được giữ đúng theo yêu cầu, không tự đổi thành official.
Nhãn official trên Hugging Face chỉ biểu thị TXT đã chốt, không tự nghiệm thu
JSON, nhãn pháp lý hoặc graph. Tài liệu dẫn tới HF bằng đường dẫn và commit;
không sao chép dữ liệu thật vào báo cáo GitHub.

Vị trí conventions.md đang được đề xuất ở root repo, ngang README.md;
yêu cầu trước đó có nhắc đặt ngoài thư mục dự án nên vị trí này chưa được
xác nhận riêng. Phiên này không tạo file bên ngoài repo.

## Kết quả thực hiện và điểm tiếp tục

- Đã đọc trạng thái repo, quy ước Git và skill phase-workflow.
- Nhánh hiện tại vẫn là dev-khang. Chưa sửa, xóa hoặc di chuyển code/dữ liệu cũ.
- Đã lưu bản tổng hợp thảo luận này; đây không phải bản sao toàn bộ lịch sử chat.
- Git fetch bị chặn: không ghi được .git/FETCH_HEAD vì filesystem chỉ đọc.
  Chưa fetch thành công, chưa tạo office-khang, chưa tạo worktree, commit hoặc push.
- Tiếp tục khi có phiên cho phép ghi Git metadata: fetch origin, kiểm tra nhánh
  đích local/remote, tạo worktree từ origin/main rồi chuyển tài liệu này sang
  commit đầu tiên. Không tạo lại hoặc ghi đè nhánh nếu nó đã tồn tại.
- Sau đó refactor từng nhóm code, cập nhật đường dẫn, kiểm thử, rà dữ liệu/khóa
  trong danh sách stage và commit theo chức năng. Chưa có phần nào được báo
  là đã hoàn tất refactor hoặc được nghiệm thu ngoài thỏa thuận trên.
