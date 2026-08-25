# 04. QUY TRÌNH HỖ TRỢ TÌM KIẾM ĐỒ THẤT LẠC (LOST & FOUND POLICY)
**Dịch vụ Áp dụng**: Xanh SM Bike, Xanh SM Taxi (GreenCar), Xanh SM Luxury  
**Phiên bản**: v2.5 (Cập nhật chuẩn thực tế theo Xanh SM)  
**Hotline 24/7**: 1900 2088 | **Email hỗ trợ**: support.vn@greensm.com  

---

## 1. Nguyên Tắc Tiếp Nhận Thông Tin Thất Lạc

Xanh SM cam kết hỗ trợ khách hàng tối đa trong việc liên hệ tài xế và tìm kiếm tài sản để quên trên phương tiện.

Khi khách hàng báo để quên đồ, AI Agent cần trích xuất đủ **4 thông tin bắt buộc**:
1. **Mã chuyến đi (`ride_id`)**: Để định danh chính xác tài xế và biển số xe.
2. **Mô tả chi tiết tài sản**: Tên đồ vật, màu sắc, nhãn hiệu, đặc điểm nhận dạng riêng (ví dụ: *"Ví da nam màu nâu, bên trong có CCCD mang tên Nguyễn Văn A"* hoặc *"Điện thoại iPhone 15 màu xanh lá"*).
3. **Vị trí để quên ước tính**: Ghế phụ trước, hàng ghế sau, sàn xe, cốp xe (đối với Taxi) hoặc túi treo đồ, móc treo mũ (đối với Bike).
4. **Thời điểm kết thúc chuyến đi**: Để xác định xem tài xế đã đón thêm cuốc khách nào sau đó chưa.

---

## 2. Quy Trình Phối Hợp & Liên Hệ Tài Xế

### 2.1. Trong vòng 24 Giờ Kể Từ Khi Kết Thúc Chuyến
- AI Agent kích hoạt tính năng **Cuộc gọi ảo bảo mật (Masked Call / Virtual VoIP)** trên ứng dụng, cho phép khách hàng gọi trực tiếp đến tài xế mà **không làm lộ số điện thoại cá nhân của cả hai bên**.
- AI Agent gửi tin nhắn thông báo tự động (Push Notification & SMS) đến ứng dụng của Tài xế với nội dung: *"Khách hàng chuyến [#ID] báo để quên tài sản [Mô tả]. Vui lòng kiểm tra xe và phản hồi."*

### 2.2. Sau 24 Giờ Kể Từ Khi Kết Thúc Chuyến
- Tính năng gọi trực tiếp sẽ tự động khóa để bảo vệ quyền riêng tư của tài xế.
- Mọi liên hệ sẽ thông qua **Tổng đài CSKH Xanh SM** (AI Agent tạo ticket chuyển bộ phận Hỗ trợ điều phối viên liên hệ tài xế).

---

## 3. Quy Định Bàn Giao & Chi Phí Vận Chuyển

Tài xế Xanh SM có trách nhiệm bảo quản nguyên vẹn tài sản của khách hàng khi tìm thấy. Việc bàn giao tài sản tuân thủ các phương án sau:

### Phương Án 1: Tài Xế Mang Đồ Đến Trả Tận Nơi
- Do tài xế phải di chuyển ngoài giờ làm việc hoặc ngắt quãng ca chạy, khách hàng cần hỗ trợ **Chi phí di chuyển (xăng xe / khấu hao)** cho tài xế.
- **Mức phí đề xuất chuẩn**:
  - Dưới 5 km: 30.000 VNĐ.
  - Từ 5 km – 15 km: 60.000 VNĐ.
  - Trên 15 km: Tính theo biểu phí cước giao hàng dịch vụ Xanh Express tiêu chuẩn.

### Phương Án 2: Gửi Qua Dịch Vụ Giao Hàng (Xanh Express)
- Tài xế có thể gửi món đồ qua dịch vụ chuyển phát / Xanh Express đến địa chỉ của khách hàng. Khách hàng thanh toán phí ship khi nhận hàng.

### Phương Án 3: Bàn Giao Tại Văn Phòng Điều Hành Xanh SM
- Tài xế bàn giao tài sản về **Văn phòng Trung tâm Điều hành Xanh SM gần nhất** trong vòng 48 giờ.
- Bộ phận CSKH sẽ lập biên bản tiếp nhận và liên hệ khách hàng mang giấy tờ tùy thân đến nhận miễn phí.

---

## 4. Quy Trình Xử Lý Tài Sản Giá Trị Cao & Không Tìm Thấy

- **Đối với tài sản có giá trị lớn ($> 5.000.000$ VNĐ, tiền mặt lớn, vàng bạc, laptop)**:
  - Nếu tài xế xác nhận tìm thấy: Yêu cầu bàn giao trực tiếp tại Văn phòng Công ty hoặc Đồn Công an phường sở tại có sự chứng kiến của 3 bên.
  - Nếu tài xế thông báo kiểm tra xe nhưng không thấy đồ (do khách sau vô tình/cố ý lấy mất): CSKH sẽ hỗ trợ trích xuất lịch sử các cuốc khách kế tiếp và hướng dẫn khách hàng làm việc với Cơ quan Công an theo đúng trình tự pháp luật.
