# NimbusAI — GPU Cost Optimization Report

**Period:** monthly  
**Baseline spend:** $27,133  
**Optimized spend:** $14,626  
**Projected savings:** $12,507  (**46%**)

## Savings by lever

| Lever | Savings (USD) |
|---|---|
| Inference (cascade/cache/batch) | $1,212 |
| Purchasing (spot/reserved) | $10,040 |
| Right-size util-lies | $655 |
| Kill idle GPUs | $600 |

## Sustainability

- Energy per query: 0.24 Wh
- Carbon per query: 0.091 gCO2e
- Cleanest region: europe-north1

_Figures are June-2026 as-of snapshots; re-baseline before acting._

## Phạm vi và giả định

Dữ liệu tổng hợp seed=25, giá và cường độ carbon minh họa tháng 6/2026; không phải báo giá hiện hành. M2 là một ngày traffic, nhân 30 để lấy run-rate tháng. M3 giả định mỗi workload lặp lại 30 ngày; cột days chỉ dùng cho kịch bản carbon theo thời lượng job thực tế.

Tổng đầu báo cáo giữ kịch bản giảng dạy M5: cộng chi phí API và GPU như hai ngân sách riêng. Chưa có ánh xạ telemetry → workload nên right-size và idle là cơ hội bổ sung, chưa chứng minh độc lập với purchasing. Tổng này là dự phóng, không phải tiết kiệm đã thực hiện. Nếu API và GPU phục vụ cùng traffic, phải chọn một mô hình chi phí để tránh tính hai lần.

## Inference: cùng số token, từng đòn bẩy nối tiếp

| Bước | USD/ngày | USD/1M-token | Tiết kiệm tăng thêm USD/tháng |
|---|---:|---:|---:|
| baseline | 48.8742 | 6.488 | 0.00 |
| cascade | 11.4756 | 1.523 | 1121.96 |
| cache | 10.2792 | 1.365 | 35.89 |
| batch | 8.4846 | 1.126 | 53.84 |

Kịch bản chỉ gồm inference + purchasing: $27,133.22 → $15,881.54/tháng (41.5% giảm); chưa cộng right-size/idle. GPU không có số token tương ứng nên không quy toàn bộ hóa đơn GPU về USD/1M-token.

## Hiệu quả GPU và thứ tự hành động

GPU-Util đo tỷ lệ thời gian kernel hoạt động, không đo lượng FLOPs hữu ích. Kernel chờ bộ nhớ hoặc overhead vẫn có thể làm GPU-Util cao. Telemetry phát hiện bất thường nhưng chưa đủ kết luận nguyên nhân; cần profiler và đo throughput/latency.

- gpu-h100-4: GPU-Util 98.2%, MFU 0.194, MBU 0.207.
- gpu-a10g-1: GPU-Util 96.9%, MFU 0.268, MBU 0.302.

Idle: $20.00/ngày, $600.00/tháng. Hạ GPU một bậc là giả thuyết; phải kiểm tra VRAM, bandwidth, chất lượng và SLA trước khi tính savings thực tế.

1. Tắt GPU idle theo lịch và xác minh tag trước chargeback; đo hóa đơn sau thay đổi.
2. Thử cascade trên tập đánh giá chất lượng, rồi cache; chỉ batch tác vụ chấp nhận độ trễ. Cascade đóng góp lớn nhất trong ba lever inference.
3. Checkpoint cho spot; chỉ commit reserved khi có nhu cầu dài hạn. M3 tính reserved theo giờ sử dụng, chưa tính đầy đủ giờ nhàn rỗi/cam kết 3 năm, nên cần xác minh hợp đồng trước triển khai.

## Extension 4 — Ngân sách reasoning

| Traffic | Request | USD/ngày | Wh/ngày |
|---|---:|---:|---:|
| Thông thường | 2199 | 7.0882 | 1887.56 |
| Reasoning | 201 | 1.3965 | 29787.74 |

Reasoning chiếm 8.38% request, 16.46% chi phí optimized và 94.04% năng lượng. Hệ số 80× là giả định lab trên cùng số token; output reasoning còn dài 6× trong bộ sinh dữ liệu, không phải phép đo điện thực tế.

- Cap 10%: chuyển 0 request; tiết kiệm kỳ vọng $0.0000/ngày và 0.00 Wh/ngày.
- Cap 5%: chuyển 81 request; tiết kiệm kỳ vọng $0.4142/ngày và 11932.44 Wh/ngày.

Quy tắc đề xuất: chỉ bật reasoning khi tác vụ nhiều bước và đường trả lời thường không đạt kiểm tra chất lượng; giữ quyền ưu tiên cho tác vụ bắt buộc. Kịch bản cap chọn ngẫu nhiên kỳ vọng, giữ input/model/cache/batch, giảm output về 1/6 và bỏ multiplier năng lượng. Chưa có complexity/confidence trong dataset nên chưa thể kiểm chứng chất lượng; không cộng savings này vào M5.

## Extension 5 — Lịch chạy theo carbon

| Job có thể gián đoạn | kWh | CO2e us-east-1 (kg) | CO2e europe-north1 (kg) |
|---|---:|---:|---:|
| job-train-llm | 1568.00 | 595.84 | 47.04 |
| job-train-embed | 80.00 | 30.40 | 2.40 |
| job-finetune | 25.20 | 9.58 | 0.76 |
| job-dev-sandbox | 52.80 | 20.06 | 1.58 |
| job-batch-eval | 63.00 | 23.94 | 1.89 |

| Vùng | USD/kWh | gCO2e/kWh | Điện USD | CO2e kg |
|---|---:|---:|---:|---:|
| us-east-1 | 0.120 | 380 | 214.68 | 679.82 |
| us-west-2 | 0.070 | 120 | 125.23 | 214.68 |
| europe-north1 | 0.090 | 30 | 161.01 | 53.67 |
| europe-central2 | 0.180 | 660 | 322.02 | 1180.74 |
| us-east-wa | 0.055 | 90 | 98.39 | 161.01 |

Chuyển sang europe-north1: giảm 626.15 kgCO2e (92.11%) và $53.67 tiền điện trong thời lượng các job. Vùng rẻ nhất là us-east-wa, vùng sạch nhất là europe-north1; không có một vùng đồng thời tối thiểu cả hai. us-west-2 là lựa chọn trung gian trong bảng.

Năng lượng = giờ × số GPU × công suất định mức; chưa gồm PUE, CPU, mạng hay checkpoint. Giá điện không phải giá thuê GPU và thường đã nằm trong hóa đơn provider nên không cộng khoản này vào savings GPU. Trước khi di chuyển cần xét dữ liệu, egress, quota, GPU sẵn có và độ trễ; ưu tiên training/offline có thể gián đoạn.

Năng lượng/truy vấn 0.24 Wh ở phần Sustainability là ví dụ 800 token không reasoning; bảng reasoning phía trên mới dùng toàn bộ token thực tế trong dataset.

## Bonus

Xem [báo cáo ba phần bonus](bonus_report.md) và evidence trong `outputs/bonus/`.
