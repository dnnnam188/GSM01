/** Định dạng dùng chung. Tiền tệ luôn theo chuẩn Việt Nam, không rút gọn. */

export function money(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${value.toLocaleString("vi-VN")} ₫`;
}

export function ms(value: number | null | undefined): string {
  if (!value) return "—";
  return value >= 1000 ? `${(value / 1000).toFixed(2)} s` : `${value} ms`;
}

export function when(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function sinceNow(iso: string): string {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (minutes < 1) return "vừa xong";
  if (minutes < 60) return `${minutes} phút trước`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} giờ trước`;
  return `${Math.round(hours / 24)} ngày trước`;
}

/** Nhãn tiếng Việt cho 10 nhãn ý định — xem docs/intent-taxonomy.md */
export const INTENT_LABEL: Record<string, string> = {
  "booking.create": "Đặt xe",
  "booking.cancel": "Huỷ chuyến",
  "booking.modify": "Đổi điểm đến",
  "trip.lookup": "Tra cứu chuyến",
  "fare.inquiry": "Hỏi cước phí",
  "refund.request": "Yêu cầu hoàn tiền",
  "complaint.driver": "Khiếu nại tài xế",
  "complaint.lost_item": "Thất lạc đồ",
  "policy.faq": "Hỏi chính sách",
  other: "Ngoài phạm vi",
};

export const REASON_LABEL: Record<string, string> = {
  DOUBLE_CHARGE: "Thu tiền trùng",
  ROUTE_INEFFICIENCY: "Tài xế đi vòng",
  FARE_DISCREPANCY: "Chênh lệch cước",
  WRONG_CANCEL_FEE: "Thu phí huỷ sai",
  SERVICE_INTERRUPTION: "Gián đoạn dịch vụ",
  OTHER: "Lý do khác",
};
