# Kế hoạch và file báo cáo cho thử thách nâng cao (bonus +15 điểm)

## 1. Mục tiêu

Hoàn thành phần thử thách nâng cao theo đúng yêu cầu của `ADVANCED.md`:

- chọn 1 tài liệu thực tế từ 100 trang trở lên
- có text, bảng, ảnh và biểu đồ
- xây pipeline index và retrieval đa dạng
- tạo benchmark dev/test riêng với các câu hỏi có và không có evidence
- đạt ít nhất 90% trên test (ít nhất 27/30 nếu test có 30 câu)

## 2. Kế hoạch thực hiện

### Bước 1 — Chọn tài liệu nguồn

Chọn 1 tài liệu có đủ đặc tính:

- từ 100 trang trở lên
- có bảng dữ liệu, sơ đồ, ảnh, biểu đồ
- nội dung phụ thuộc vào chữ và hình trực quan
- có thể truy cập nguồn gốc và kiểm chứng lại được

Ví dụ hợp lệ:

- báo cáo thường niên doanh nghiệp
- báo cáo nghiên cứu khoa học
- báo cáo tài chính / thị trường / ESG
- tài liệu kỹ thuật có biểu đồ và sơ đồ

Ghi rõ:

- tên tài liệu
- nguồn / bản quyền / link truy cập
- số trang
- phiên bản
- tóm tắt nội dung

### Bước 2 — Xây pipeline index

Cần index không chỉ text, mà cả dữ liệu trực quan:

- text: chunk từ PDF / HTML / DOCX
- bảng: trích xuất hàng/cột, lưu metadata page + region
- ảnh / sơ đồ: OCR hoặc mô tả bằng vision model
- biểu đồ: trích xuất trục, nhãn, đơn vị, giá trị

Khuyến nghị pipeline:

1. OCR / parse text từ PDF
2. phân tách section theo page
3. trích bảng, lưu `table_id`, `page`, `row`, `column`, `unit`
4. trích ảnh/sơ đồ, lưu `image_id`, `page`, `caption`, `alt_text`
5. lưu metadata `source`, `page`, `section`, `type` (`text` | `table` | `image` | `chart`)
6. index vào vector store hoặc hybrid index

### Bước 3 — Thiết kế benchmark

Tổng test tối thiểu 30 câu:

- 24 câu có đáp án
- 6 câu thiếu bằng chứng

Phân bổ tối thiểu theo nhóm:

| Nhóm chính | Số câu tối thiểu | Ví dụ                                    |
| ---------- | ---------------: | ---------------------------------------- |
| Bảng       |                6 | lấy giá trị từ hàng/cột, so sánh dữ liệu |
| Ảnh, sơ đồ |                5 | giải thích hình, nhận diện đối tượng     |
| Biểu đồ    |                5 | đọc trục/đơn vị, so sánh xu hướng        |
| Multi-hop  |                4 | kết hợp 2 nguồn hoặc 2 phần khác nhau    |
| Text       |                4 | trả lời từ đoạn văn bản                  |

Dev nên có:

- 15 câu có đáp án
- 3 câu thiếu bằng chứng
- bao phủ đủ các nhóm trên

Lưu ý:

- 1 câu chỉ thuộc 1 nhóm chính duy nhất
- câu dev và test không được trùng nguyên mẫu, chỉ có thể là biến thể câu hỏi cùng ý nghĩa
- không đưa gold answer vào pipeline khi chạy benchmark

### Bước 4 — Cấu hình retrieval

Thử ít nhất 3 phương án:

- dense retrieval
- lexical / BM25
- hybrid retrieval
- có thể thêm section filter hoặc rerank

Đánh giá theo:

- Hit@1
- Evidence Hit@3
- Context Evidence Rate
- độ đúng trên benchmark dev

Chốt config tốt nhất trên dev rồi mới chạy test.

### Bước 5 — Chấm và báo cáo

Mỗi câu test cần có:

- `query_id`
- `group`
- `question`
- `expected_answer` hoặc `abstain_expected`
- `source_page`
- `source_section`
- `evidence_type` (`text`, `table`, `image`, `chart`)
- `reason`

Chấm dựa trên bản gốc, không chỉ nhìn vào mô tả OCR hoặc trả lời của model.

Định dạng báo cáo cần có:

- tổng quan tài liệu
- pipeline xử lý và dữ liệu index
- benchmark dev/test
- kết quả retrieval
- kết quả agent
- lỗi và cải tiến
- bảng tổng kết theo nhóm
- kết luận đạt/tại sao không đạt bonus

## 3. File báo cáo mẫu

```md
# Báo cáo thử thách nâng cao — Bonus +15 điểm

## 1. Tài liệu nguồn

- Tên tài liệu:
- Nguồn:
- Bản quyền / quyền truy cập:
- Số trang:
- Phiên bản:
- Nội dung chính:

## 2. Indexing pipeline

- Text extraction:
- Table extraction:
- Image / diagram extraction:
- Chart parsing:
- Metadata lưu trữ:
- Trạng thái phần chưa xử lý:

## 3. Benchmark

### 3.1 Tổng quan

- Tổng test: 30 câu
- Có đáp án: 24
- Thiếu bằng chứng: 6
- Dev: 18 câu
- Test: 30 câu

### 3.2 Phân bổ theo nhóm

| Nhóm             | Dev | Test | Mô tả |
| ---------------- | --: | ---: | ----- |
| Bảng             |     |      |       |
| Ảnh, sơ đồ       |     |      |       |
| Biểu đồ          |     |      |       |
| Multi-hop        |     |      |       |
| Text             |     |      |       |
| Thiếu bằng chứng |     |      |       |

## 4. Retrieval experiment

| Cấu hình    | Mô tả | Dev | Test | Ghi chú |
| ----------- | ----- | --: | ---: | ------- |
| Dense       |       |     |      |         |
| BM25        |       |     |      |         |
| Hybrid      |       |     |      |         |
| Best config |       |     |      |         |

## 5. Agent evaluation

- Model dùng:
- Tool:
- Số lượt search:
- Điều kiện dừng:
- Cách chọn context:
- Cách xử lý abstain:

| Split | Câu đạt | Tổng | Tỷ lệ | Ghi chú |
| ----- | ------: | ---: | ----: | ------- |
| Dev   |         |      |       |         |
| Test  |         |      |       |         |

## 6. Chi tiết từng câu test

| Query ID | Nhóm             | Loại      | Kết quả | Evidence | Ghi chú |
| -------- | ---------------- | --------- | ------- | -------- | ------- |
| test_01  | Bảng             | Có đáp án |         |          |         |
| test_02  | Ảnh              | Có đáp án |         |          |         |
| test_03  | Biểu đồ          | Có đáp án |         |          |         |
| test_04  | Multi-hop        | Có đáp án |         |          |         |
| test_05  | Text             | Có đáp án |         |          |         |
| test_06  | Thiếu bằng chứng | Abstain   |         |          |         |

## 7. Lỗi và cải tiến

- Lỗi chính 1:
- Nguyên nhân:
- Cách thử:
- Kết quả:

- Lỗi chính 2:
- Nguyên nhân:
- Cách thử:
- Kết quả:

## 8. Kết luận

- Cấu hình cuối cùng:
- Benchmark test:
- Tỷ lệ đạt:
- Có đạt bonus không?:
- Giới hạn còn lại:

## 9. Đường dẫn tài liệu và artifacts

- PDF / source:
- Benchmark file:
- Index / vector store:
- Trace file:
- Summary report:
```

## 4. Mức độ đạt bonus cần có

Để đạt +15 điểm, phải đồng thời đảm bảo:

- tài liệu thực tế >=100 trang
- có bảng, ảnh và biểu đồ
- benchmark đúng theo quy cách
- test đạt >=90% theo công thức `số câu đạt / tổng câu test`
- có trace, evidence, artifact tái lập
- phần báo cáo đầy đủ và minh bạch

## 5. Gợi ý tối ưu

Nếu bạn muốn làm phần bonus trong thời gian ngắn mà vẫn chắc chắn:

1. chọn tài liệu có 100-200 trang, dễ parse text và có nhiều bảng/chart rõ ràng
2. ưu tiên tài liệu có ít text rối và nhiều dữ liệu dạng bảng/biểu đồ
3. xây benchmark theo nhóm rõ ràng để chấm nhanh và dễ kiểm tra
4. không làm quá phức tạp ở phần OCR / vision nếu chưa cần, chỉ cần pipeline rõ ràng và đáng tin cậy
5. ưu tiên dự án có 30 câu test đúng format, thay vì nỗ lực làm quá nhiều

## 6. Kết luận ngắn

Phần bonus không phải “làm nhiều hơn” mà là “làm đúng chuẩn và có bằng chứng”. Nếu bạn có tài liệu 100+ trang, benchmark rõ ràng, trace đầy đủ và đạt trên 90% test, bạn mới đủ điều kiện nhận +15 điểm.
