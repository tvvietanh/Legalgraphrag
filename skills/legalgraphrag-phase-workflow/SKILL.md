---
name: legalgraphrag-phase-workflow
description: Điều phối thực hiện từng giai đoạn P0–P9 của LegalGraphRAG Việt Nam giữa người phụ trách dữ liệu và người phụ trách mô hình/hệ thống; lập report-pN.md, thực hiện từng phần được xác nhận, ghi kết quả và bàn giao Git theo doc/git_format.md. Dùng khi bắt đầu, tiếp tục hoặc nghiệm thu một giai đoạn; không áp dụng cho câu hỏi giải thích thông thường.
---

# Quy trình thực hiện giai đoạn

Làm việc trong repository hiện tại. Trao đổi và viết báo cáo bằng tiếng Việt; commit và PR bằng tiếng Anh theo quy định dự án.

## 1. Xác định công việc và đọc trạng thái

- Đọc `doc/overall.md`, `doc/git_format.md`, tài liệu của giai đoạn theo [references/phases.md](references/phases.md) và báo cáo hiện có ở `doc/reports/report-pN.md`.
- Kiểm tra nhánh, working tree và các sản phẩm đầu vào liên quan. Giữ nguyên thay đổi của người khác. Không coi sơ đồ hoặc lệnh dự kiến trong tài liệu là chức năng đã triển khai.
- Xác định giai đoạn, người phụ trách, phạm vi được giao và phần nhỏ cần làm. Suy ra từ yêu cầu và báo cáo nếu rõ; chỉ hỏi thông tin còn thiếu ảnh hưởng trực tiếp đến công việc.
- Khi tiếp tục ở phiên mới, đối chiếu báo cáo với file và Git thực tế. Không suy đoán một mục đã được duyệt nếu không có bằng chứng trong ngữ cảnh hoặc nhật ký xác nhận.

## 2. Chuẩn bị kế hoạch và báo cáo trước khi thực thi

Tạo `doc/reports/report-pN.md` từ [assets/report-template.md](assets/report-template.md), thay N bằng số giai đoạn. Nếu đã tồn tại, cập nhật có mục tiêu, giữ lịch sử; không ghi đè. P0–P9 dùng chung một báo cáo mỗi giai đoạn; phân biệt phần việc hai người bằng task ID và owner.

Mô tả cho người dùng và trong báo cáo:

- Đầu vào cần chuẩn bị, trạng thái sẵn sàng và phụ thuộc còn thiếu.
- Các phần nhỏ có ID `PN-01`, `PN-02`, ...; owner, file dự kiến, đầu ra và tiêu chí nghiệm thu riêng.
- Cách kiểm tra, thứ tự thực hiện và điểm bàn giao giữa hai người.
- Phần nào dùng dữ liệu mô phỏng, phần nào cần dữ liệu đã duyệt; ghi rõ giới hạn kết quả kiểm tra bằng mock.

Việc đọc trạng thái và soạn báo cáo là bước chuẩn bị được phép làm khi người dùng yêu cầu bắt đầu giai đoạn. Chưa chạy biến đổi dữ liệu, gọi model, tải dữ liệu hoặc sửa triển khai trước khi phần việc tương ứng được xác nhận.

## 3. Thực hiện từng phần có xác nhận

Áp dụng vòng lặp sau cho từng task:

1. Trình bày phạm vi cụ thể, sản phẩm và tiêu chí kiểm tra của task, rồi yêu cầu xác nhận trước khi thực hiện. Nếu người dùng đã chỉ rõ cho phép làm task đó trong phiên hiện tại, dùng xác nhận sẵn có; không hỏi lại cùng phạm vi. Lệnh chung như “bắt đầu P2” cho phép chuẩn bị kế hoạch, không tự động duyệt toàn bộ task.
2. Ghi xác nhận và phạm vi vào báo cáo, chuyển task sang `approved`, rồi `in_progress`. Chỉ thực hiện phần được duyệt. Khi phát sinh thay đổi đáng kể về phạm vi, chi phí hoặc sản phẩm, cập nhật đề xuất và xin xác nhận bổ sung trước phần phát sinh.
3. Thực hiện, chạy kiểm tra phù hợp, ghi file đầu ra, lệnh thực tế, kết quả và giới hạn. Không đánh dấu kiểm tra chưa chạy là pass. Nếu thiếu phụ thuộc, ghi `blocked` với nguyên nhân cụ thể; có thể tiếp tục phần độc lập đã được duyệt.
4. Cập nhật báo cáo ngay sau khi làm xong thành `awaiting_review`; báo ngắn kết quả cho người dùng và yêu cầu xác nhận nghiệm thu. Không chờ xác nhận mới ghi bằng chứng, để tránh mất tiến độ giữa các phiên.
5. Khi người dùng xác nhận, ghi vào nhật ký và chuyển `accepted`. Nếu cần sửa, ghi yêu cầu, thực hiện sửa trong phạm vi đã duyệt, kiểm tra lại và trình kết quả. Không tự ghi rằng người dùng đã nghiệm thu.
6. Mặc định dừng ở điểm chờ xác nhận trước khi chuyển sang task kế tiếp. Người dùng có thể duyệt trước một nhóm task cụ thể hoặc cho phép làm liên tục; ghi rõ phạm vi đó và vẫn báo/cập nhật kết quả từng task. Chỉ bỏ điểm chờ nghiệm thu giữa các task khi người dùng cho phép rõ ràng.

Trạng thái task: `planned → approved → in_progress → awaiting_review → accepted`; dùng `blocked` khi có trở ngại và `needs_revision` khi người dùng yêu cầu sửa. Hoàn thành triển khai không đồng nghĩa đã nghiệm thu.

Khi hỏi xác nhận do quy trình này yêu cầu, nêu ngắn lý do và liên kết tới mục 3 của SKILL.md, ví dụ: “Theo [quy trình xác nhận](skills/legalgraphrag-phase-workflow/SKILL.md), phần P2-01 đã sẵn sàng để bạn nghiệm thu.” Dùng công cụ hỏi người dùng nếu có, nếu không hỏi trong câu trả lời kết thúc lượt. Không tự coi thời gian chờ là sự đồng ý.

## 4. Phối hợp và bàn giao

- Owner dữ liệu quyết định việc chọn mẫu, chất lượng nhãn, mapping luật, split và duyệt checklist có nguồn. Owner hệ thống phụ trách runtime/model, graph engine, Agent và runner thực nghiệm.
- Tách P4, P7, P8 thành task của từng owner theo [references/phases.md](references/phases.md); không đợi toàn bộ dữ liệu xong mới chuẩn bị hệ thống.
- Hai bên chốt schema, ID, phiên bản và mẫu giao tiếp từ P0. Hệ thống có thể phát triển bằng fixture không chứa test thật; nghiệm thu tích hợp cần artifact dữ liệu đã duyệt.
- Bàn giao bằng đường dẫn, schema/version, manifest/hash nếu có, kiểm tra đã chạy và vấn đề còn mở. Không sửa giao diện dữ liệu chung ngoài phạm vi đã được duyệt.
- Nếu cả hai cùng sửa một báo cáo, giữ task ID duy nhất, tích hợp bổ sung của người kia và giải quyết xung đột theo nội dung; không ghi đè toàn bộ báo cáo bằng bản cũ.

## 5. Chốt công việc và Git

Đọc lại `doc/git_format.md` tại thời điểm thực hiện Git; file này là nguồn quy định nhánh, commit và PR. Mỗi phần độc lập đã nghiệm thu có thể có commit riêng; chỉ đánh dấu giai đoạn hoàn thành khi tiêu chí giai đoạn đạt và người dùng đã nghiệm thu.

1. Kiểm tra diff, kết quả validation và các task trong phạm vi; cập nhật báo cáo trước commit. Stage bằng danh sách file cụ thể; không dùng `git add .` để gom thay đổi người khác, dữ liệu thô, secrets hoặc artifact lớn.
2. Commit trên `dev`, tiêu đề `A(B): C` với scope đúng P0–P9. Nếu đang ở nhánh khác, kiểm tra khả năng chuyển an toàn; không reset, stash hoặc ghi đè thay đổi người dùng. Nếu không thể chuyển an toàn hoặc có dấu hiệu hai người đang làm chung working tree, báo tình trạng và yêu cầu quyết định về nhánh trước commit. Không sửa `git_format.md` để hợp thức hóa nhánh hiện tại.
3. Trước push/PR, trình danh sách commit, HEAD, kiểm tra, phạm vi diff và đích `origin/dev` → `main`; lấy xác nhận của chủ dự án theo `git_format.md`. Yêu cầu chung “làm theo skill” không phải xác nhận push/merge một HEAD chưa được xem. Nếu đã có xác nhận rõ cho đúng HEAD và hành động trong phiên, không hỏi lại.
4. Push, tạo/cập nhật PR chỉ trong phạm vi được duyệt. Merge cần xác nhận đúng PR và HEAD cùng required checks thành công. Commit mới làm thay đổi phạm vi cần duyệt lại trước merge. Không force push hoặc bỏ qua kiểm tra.
5. Ghi kết quả Git thực tế: commit, trạng thái push, PR, merge nếu có. Nếu bị hạn chế quyền hoặc mạng, giữ kết quả local và báo chính xác thao tác chưa làm; không sửa sandbox/OS.

Để tránh vòng lặp hash tự tham chiếu: báo cáo trong commit ghi các task/validation và “commit hash: xem Git history”; báo cáo hash chính xác trong câu trả lời sau commit. Không tạo commit liên tiếp chỉ để cập nhật hash của chính báo cáo. Nhật ký push/PR có thể bổ sung ở lần cập nhật báo cáo tiếp theo; nói rõ nếu cập nhật đó chưa commit.

## Cách gọi

Xem [references/prompts.md](references/prompts.md) để bắt đầu, tiếp tục, xác nhận task và yêu cầu Git. Skill nằm trong repo có thể được dùng bằng cách yêu cầu agent đọc trực tiếp file này; không giả định đã được cài vào danh mục skill của mọi máy.
