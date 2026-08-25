# 07. CHÍNH SÁCH BẢO MẬT DỮ LIỆU & QUY ĐỊNH PII (PRIVACY & GUARDRAILS)
**Dịch vụ Áp dụng**: Toàn bộ hệ thống AI Agent, Backend API và Nhân viên CSKH Xanh SM  
**Phiên bản**: v2.4 (Cập nhật 2026)  
**Tiêu chuẩn tuân thủ**: Nghị định 13/2023/NĐ-CP về Bảo vệ Dữ liệu Cá nhân  

---

## 1. Danh Mục Thông Tin Định Danh Nhạy Cảm (PII - Personally Identifiable Information)

Hệ thống Xanh SM nghiêm cấm AI Agent hiển thị hoặc rò rỉ các thông tin sau ra ngoài ngữ cảnh công khai:

| Loại thông tin | Định dạng bảo vệ (Masking Rule) | Ví dụ minh họa |
|---|---|---|
| **Số điện thoại thật của Khách** | Che 4 chữ số giữa | `098****321` |
| **Số điện thoại thật của Tài xế** | Ẩn hoàn toàn, chỉ dùng Tổng đài ảo | `Số ảo qua App (VoIP)` |
| **Số thẻ ngân hàng / CVV** | Chỉ giữ 4 số cuối, cấm lưu CVV | `**** **** **** 8899` |
| **Địa chỉ nhà chi tiết (Điểm đón/trả)** | Ẩn số nhà/tên ngõ ngách chi tiết trong log công khai | `Số *** Đường Trần Phú, Ba Đình, Hà Nội` |
| **Căn cước công dân (CCCD)** | Che 6 số giữa | `0010******89` |

---

## 2. Guardrails Cho AI Agent Khi Tương Tác Với Người Dùng

### 2.1. Quy Định Tuyệt Đối Không Tiết Lộ Thông Tin Tài Xế Cho Khách Hàng
- Khi khách hàng hỏi thông tin cá nhân của tài xế (như *"Cho tôi xin số điện thoại riêng của tài xế", "Địa chỉ nhà của bác tài ở đâu?", "Biển số xe máy cá nhân của tài xế là gì?"*):
  - **Phản hồi chuẩn của AI Agent**: *"Để đảm bảo an toàn và bảo mật thông tin cá nhân theo quy định của Xanh SM, hệ thống không thể cung cấp số điện thoại riêng hoặc thông tin cá nhân của tài xế. Nếu Quý khách cần liên hệ tài xế để tìm đồ hoặc xử lý vấn đề cuốc xe, tôi có thể hỗ trợ kích hoạt cuộc gọi ảo bảo mật qua ứng dụng hoặc tạo yêu cầu để bộ phận CSKH hỗ trợ kết nối ạ."*

### 2.2. Quy Định Bảo Mật Lịch Sử Chuyến Đi Của Khách Hàng
- AI Agent chỉ được phép truy vấn và phản hồi thông tin chuyến đi khi:
  - Khách hàng đã được xác thực danh tính qua Token đăng nhập (JWT `user_id` khớp với chủ chuyến đi).
  - Nghiêm cấm trả lời truy vấn về lịch sử di chuyển của người khác (ví dụ: vợ tra cứu lịch sử của chồng, bạn bè tra cứu lịch sử của nhau).

### 2.3. Quy Định Về Trích Xuất Dữ Liệu GPS & Camera Hành Trình
- AI Agent **không được tự ý cung cấp file log GPS thô hoặc hình ảnh/video camera hành trình** cho khách hàng qua khung chat.
- Mọi yêu cầu trích xuất dữ liệu camera an ninh phải được hướng dẫn lập hồ sơ chính thức gửi tới Cơ quan Điều tra hoặc theo văn bản yêu cầu từ cơ quan chức năng có thẩm quyền.

---

## 3. Thời Hạn Lưu Trữ & Hủy Dữ Liệu An Toàn
- **Dữ liệu tọa độ GPS hành trình**: Lưu trữ tối đa **90 ngày** phục vụ đối soát, sau đó tự động tổng hợp (aggregate) và xóa dữ liệu thô.
- **Log hội thoại Chat với AI Agent**: Lưu trữ 180 ngày phục vụ đánh giá chất lượng mô hình (Model Evaluation), toàn bộ PII (tên, SĐT, địa chỉ) đều được làm sạch trước khi nạp vào bộ dataset huấn luyện/đánh giá.
