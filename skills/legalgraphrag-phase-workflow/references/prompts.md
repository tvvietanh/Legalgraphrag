# Prompt sử dụng chung

Các prompt này yêu cầu agent đọc skill trực tiếp trong repo, dùng được kể cả khi skill chưa xuất hiện trong danh mục tự động. Thay các giá trị ví dụ bằng giai đoạn và task thực tế.

## Bắt đầu phía dữ liệu

> Đọc và áp dụng skills/legalgraphrag-phase-workflow/SKILL.md. Tôi phụ trách dữ liệu. Hãy chuẩn bị P1: kiểm tra đầu vào, đề xuất các phần nhỏ và tạo doc/reports/report-p1.md. Chờ tôi xác nhận từng phần trước khi thực hiện.

## Bắt đầu phía mô hình và hệ thống

> Đọc và áp dụng skills/legalgraphrag-phase-workflow/SKILL.md. Tôi phụ trách mô hình và hệ thống. Hãy kiểm tra đầu vào bàn giao, chuẩn bị kế hoạch P4 cho model/runtime và extractor, ghi vào report-p4.md. Phần QA dữ liệu và duyệt checklist thuộc người phụ trách dữ liệu. Chờ xác nhận trước từng phần.

## Cho phép một phần nhỏ

> Tôi xác nhận cho thực hiện P2-01 theo phạm vi và tiêu chí trong báo cáo. Làm xong hãy cập nhật bằng chứng, trình kết quả để tôi nghiệm thu rồi chờ trước khi sang P2-02.

## Nghiệm thu và tiếp tục

> Tôi nghiệm thu P2-01. Cập nhật báo cáo. Tôi cũng cho phép thực hiện P2-02 theo kế hoạch hiện tại.

## Tiếp tục từ phiên khác

> Đọc skill và doc/reports/report-p3.md, đối chiếu file và Git thực tế. Tóm tắt phần đã xong, phần đang chờ và đề xuất task tiếp theo. Không tự coi các mục đang chờ là đã được duyệt.

## Chuẩn bị commit và đề nghị push

> Các task P3-01 và P3-02 đã được nghiệm thu. Kiểm tra và commit phần việc này theo doc/git_format.md. Trình commit list, HEAD, validation và phạm vi push/PR để chủ dự án phê duyệt.

## Duyệt Git sau khi xem kết quả

> Tôi là chủ dự án và phê duyệt push HEAD <hash thực tế vừa xem> lên origin/dev, tạo hoặc cập nhật PR vào main. Chưa cho phép merge.

Để merge, người dùng duyệt PR và HEAD cụ thể theo doc/git_format.md. Không dùng placeholder trong prompt phê duyệt thực tế.
