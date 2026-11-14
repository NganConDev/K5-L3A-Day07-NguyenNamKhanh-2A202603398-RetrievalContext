# Kế hoạch thực hiện thử thách nâng cao – FPT Annual Report 2024

## 1. Nguồn tài liệu

- File PDF: `/Users/nguyennamkhanh/Downloads/bao_cao_thuong_nien_fpt_2024_883024f1dd.pdf`
- Loại tài liệu: báo cáo thường niên doanh nghiệp / annual report
- Đặc điểm phù hợp: có nhiều số liệu, bảng, KPI, biểu đồ, mục lục và phần phân tích hoạt động
- Yêu cầu bonus: phù hợp vì đây là tài liệu thực tế, có tính chất business reporting và chứa dữ liệu dạng bảng / chart / text

Lưu ý:

- File này đã xác nhận là PDF hợp lệ và tồn tại trên máy local.
- Cần kiểm tra thêm số trang thực tế và các phần có chứa bảng/biểu đồ trước khi tiến hành benchmark hoàn chỉnh.

## 2. Tại sao tài liệu này phù hợp cho bonus

Tài liệu báo cáo thường niên FPT 2024 phù hợp với thử thách nâng cao vì nó thường có:

- văn bản mô tả hoạt động, chiến lược và kết quả kinh doanh
- bảng tài chính, KPI và số liệu theo quý/năm
- biểu đồ tăng trưởng, tỷ trọng, hiệu suất
- sơ đồ hoặc hình ảnh minh họa hoạt động / cấu trúc / hệ sinh thái

Đây là đúng mô hình mà `ADVANCED.md` yêu cầu: "một tài liệu thực tế ít nhất 100 trang có text, bảng, ảnh và biểu đồ".

## 3. Kế hoạch triển khai

### Bước 1 — Xác nhận tài liệu (đã hoàn tất)

- File PDF gốc: `/Users/nguyennamkhanh/Downloads/bao_cao_thuong_nien_fpt_2024_883024f1dd.pdf`
- File project-local: `/Users/nguyennamkhanh/Documents/AI In Action/AI20K_Lab/K5-L3A-Day07-NguyenNamKhanh-2A202603398-RetrievalContext/data/bonus/fpt_annual_report_2024.pdf`
- Số trang thực tế: 213 trang
- Metadata đã xác nhận:
  - Creator: Adobe InDesign 20.0 (Macintosh)
  - Producer: Adobe PDF Library 17.0
  - Creation date: 2025-04-01
- Kết quả kiểm tra sơ bộ:
  - file tồn tại và có thể đọc
  - PDF có cấu trúc báo cáo: trang đầu chứa title, mục lục, các phần chính như `Dấu ấn 2024`, `Phân tích hoạt động kinh doanh`, `Quản trị công ty`, `Báo cáo ESG`, `Báo cáo tài chính`
  - nội dung có nhiều văn bản, bảng và số liệu, phù hợp với yêu cầu bonus

Tiếp theo, cần phân loại các section chính để tạo benchmark theo nhóm: bảng, biểu đồ, ảnh/sơ đồ, text, multi-hop và câu thiếu bằng chứng.

### Bước 2 — Xây pipeline index

Tạo một pipeline index riêng cho tài liệu này với các loại dữ liệu:

- text: chunk theo section/page
- table: trích xuất dữ liệu từ bảng tài chính / KPI
- chart: trích xuất tiêu đề, trục, đơn vị và giá trị quan trọng
- image/diagram: OCR mô tả minh họa nếu có

Metadata cần lưu:

- `source`
- `page`
- `section`
- `entity`
- `type` = `text` | `table` | `chart` | `image`
- `caption`
- `unit`
- `content`

### Bước 3 — Thiết kế benchmark dev/test

Tạo benchmark tối thiểu 30 câu test như yêu cầu của `ADVANCED.md`.

#### Tỷ lệ tối thiểu theo nhóm

| Nhóm chính       | Số câu tối thiểu | Ví dụ câu hỏi                                                          |
| ---------------- | ---------------: | ---------------------------------------------------------------------- |
| Bảng             |                6 | "Doanh thu mảng nào cao nhất trong năm 2024?"                          |
| Ảnh, sơ đồ       |                5 | "Sơ đồ mô tả mối quan hệ nào giữa các đơn vị?"                         |
| Biểu đồ          |                5 | "Xu hướng lợi nhuận tăng trong khoảng thời gian nào?"                  |
| Multi-hop        |                4 | "Kết hợp bảng tài chính và phần phân tích để trả lời mức tăng trưởng?" |
| Text             |                4 | "FPT tập trung vào mục tiêu chiến lược nào?"                           |
| Thiếu bằng chứng |                6 | "Câu hỏi gần chủ đề nhưng không đủ dữ liệu trong báo cáo"              |

#### Dev benchmark

- 15 câu có đáp án
- 3 câu thiếu bằng chứng
- mỗi nhóm đều được phủ ít nhất 1–2 câu

#### Test benchmark

- 24 câu có đáp án
- 6 câu thiếu bằng chứng
- không dùng test để điều chỉnh pipeline; chỉ dùng sau khi dev đã chốt

## 4. Cấu hình retrieval cần thử

### Cấu hình 1 — Dense retrieval

- embedding từ vector store Day 6 hoặc embedding mới
- search theo semantic similarity
- filter theo section/page nếu có metadata

### Cấu hình 2 — Lexical / BM25

- search theo từ khóa tài liệu
- mạnh ở các câu hỏi chứa số liệu / tên mảng / KPI

### Cấu hình 3 — Hybrid retrieval

- kết hợp dense + lexical
- ưu tiên precision cho bảng và biểu đồ

### Cấu hình 4 — Best config

- dense + section filter + metadata table/chart boost
- tăng khả năng chọn đúng evidence từ report tài chính và chart

## 5. Tiêu chí chấm theo yêu cầu bonus

### Câu có đáp án

Đạt khi:

- trả lời đúng thông tin
- đúng đơn vị và giá trị
- có evidence rõ ràng từ bản gốc
- citation/truy xuất đúng page/section/graphic

### Câu thiếu bằng chứng

Đạt khi:

- agent từ chối hoặc nói rõ không đủ thông tin
- không suy đoán nếu dữ liệu không có trong tài liệu

### Ngưỡng bonus

- Tổng test phải đạt ít nhất 90%
- Với 30 câu test => cần ít nhất 27/30 câu đạt
- Không được làm tròn để qua ngưỡng

## 6. Ví dụ câu hỏi mẫu

### Bảng

- Tăng trưởng doanh thu của mảng nào lớn nhất trong năm 2024?
- Mức lợi nhuận sau thuế của FPT trong năm 2024 là bao nhiêu?
- Mảng nào chiếm tỷ trọng lớn nhất trong doanh thu tổng hợp?

### Biểu đồ

- Trong biểu đồ doanh thu, xu hướng tăng trưởng rõ nhất diễn ra ở giai đoạn nào?
- Chỉ số nào tăng mạnh nhất trong chuỗi KPI từ năm trước đến năm nay?

### Ảnh / sơ đồ

- Sơ đồ mô tả mối liên kết giữa các đơn vị nào?
- Hình ảnh minh họa cho chiến lược nào trong năm 2024?

### Multi-hop

- Kết hợp thông tin từ phần tài chính và phần hoạt động, mảng nào đóng góp lớn nhất và được giải thích như thế nào?
- So sánh dữ liệu năm 2024 với năm 2023 trong phần doanh thu và lợi nhuận để rút ra nhận định đúng.

### Text

- FPT ưu tiên mục tiêu chiến lược nào trong báo cáo năm 2024?
- Đâu là trọng tâm đầu tư chính của công ty trong năm nay?

### Thiếu bằng chứng

- FPT có triển khai dự án X ở quốc gia Y không?
- Báo cáo có nêu doanh thu từ thị trường Z không?

## 7. Kết quả mong muốn

Mục tiêu cuối cùng khi làm bonus:

- benchmark dev và test rõ ràng
- retrieval tốt trên bảng/biểu đồ
- agent biết cách abstain khi không có evidence
- báo cáo phần nâng cao đầy đủ với trace, evidence, nhận xét lỗi và kết quả theo nhóm

## 8. Bước tiếp theo

1. Kiểm tra số trang PDF thật và các section chính.
2. Lấy danh sách page chứa bảng, chart và sơ đồ.
3. Tạo `benchmark/dev.json` và `benchmark/test.json` theo format `ADVANCED.md`.
4. Chạy pipeline retrieval trên dev.
5. Chốt best config.
6. Chạy trên test và ghi kết quả.
7. Viết báo cáo bonus cuối cùng.

## 9. Gợi ý thực hiện

Nếu muốn làm nhanh nhưng vẫn hợp lệ:

- ưu tiên report financial / annual report
- không chọn tài liệu quá phức tạp với hình ảnh quá nhiều hoặc OCR khó
- nên ưu tiên mục có nhiều bảng tài chính + tiêu chí quan sát rõ
- tập trung tạo benchmark có câu hỏi “đúng, rõ, dễ chấm” thay vì câu hỏi quá mơ hồ

## 10. Kết luận

Tài liệu này là một lựa chọn rất hợp lệ cho phần bonus +15 điểm. Cần thực hiện đúng quy trình ở `ADVANCED.md`: index đa dạng, benchmark chất lượng, chốt config trên dev, chạy test, và báo kết quả rõ ràng với evidence.

### Section thật chi tiết và page range (ước lượng theo cấu trúc PDF)

Dựa trên tiêu đề xuất hiện trên trang đầu và phần lặp lại trong báo cáo, có thể chia PDF FPT 2024 thành các section như sau. Đây là phân đoạn theo cấu trúc của báo cáo, không phải số trang tuyệt đối do một số trang in lặp lại tiêu đề mục lục và header; cần dùng lại OCR/parse chi tiết để xác định chính xác hơn khi tạo benchmark thật.

| Mã section | Tên section                       | Page range ước lượng | Ghi chú                                                                                |
| ---------- | --------------------------------- | -------------------: | -------------------------------------------------------------------------------------- |
| S01        | Thông điệp Ban lãnh đạo           |                  2–7 | Có tiêu đề `01 THÔNG ĐIỆP BAN LÃNH ĐẠO`, thông điệp Chủ tịch HĐQT và Tổng giám đốc     |
| S02        | Dấu ấn 2024 & Tổng quan về FPT    |                 8–40 | Phần giới thiệu FPT, dấu ấn doanh nghiệp, tổng quan hoạt động                          |
| S03        | Phân tích hoạt động kinh doanh    |               41–100 | Chứa kết quả hoạt động theo mảng kinh doanh, hiệu suất, chiến lược                     |
| S04        | Quản trị công ty                  |              101–140 | Phần governance, cơ cấu, quản trị nội bộ, doanh nghiệp và định hướng điều hành         |
| S05        | Báo cáo ESG / phát triển bền vững |              111–170 | Có tiêu đề `06 BÁO CÁO ESG`, phần này có nhiều văn bản mô tả ESG và trách nhiệm xã hội |
| S06        | Báo cáo tài chính                 |              170–213 | Phần tài chính, số liệu, bảng KPI và báo cáo tổng kết cuối thư mục                     |

Lưu ý:

- Một số section có phần header lặp lại trên nhiều trang; vì vậy page range chỉ là ước lượng thiết thực để định vị benchmark, không phải số tuyệt đối được xác minh bằng OCR từng trang.
- Với mục tiêu bonus, section chính cần ưu tiên là:
  - `S02` (Tổng quan về FPT)
  - `S03` (Phân tích kinh doanh)
  - `S04` (Quản trị công ty)
  - `S05` (ESG)
  - `S06` (Tài chính)
- Khi tạo benchmark, nên ưu tiên câu hỏi thuộc các section có nhiều bảng, biểu đồ và KPI như `S03` và `S06` vì đây là nơi dễ chốt dữ liệu và dễ chấm đúng.

### Phân bổ benchmark theo section

| Section          | Nhóm phù hợp             | Gợi ý số câu |
| ---------------- | ------------------------ | -----------: |
| S02              | Text, Tổng quan          |          4–6 |
| S03              | Text, Multi-hop, Bảng    |         8–10 |
| S04              | Text, Governance         |          4–6 |
| S05              | Text, ESG, Multi-hop     |          5–7 |
| S06              | Bảng, Biểu đồ, Multi-hop |        10–12 |
| Thiếu bằng chứng | Toàn báo cáo             |            6 |

Từ đây có thể xây benchmark tương đối rõ ràng, dễ phân loại và dễ đánh giá thỏa điều kiện bonus: 30 câu test, 24 câu có đáp án + 6 câu thiếu bằng chứng, và mỗi câu đều gắn với một `section` rõ ràng.
