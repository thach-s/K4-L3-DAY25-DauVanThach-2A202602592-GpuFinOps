"""Measured analysis shared by the report and submission write-up."""
def analysis(r1, r2, r3):
    stages = r2['stages']
    budget = r2['reasoning_budget']
    carbon = r3['carbon_schedule']
    lines = ['\n## Phạm vi và giả định', '',
        'Dữ liệu tổng hợp seed=25, giá và cường độ carbon minh họa tháng 6/2026; không phải báo giá hiện hành. M2 là một ngày traffic, nhân 30 để lấy run-rate tháng. M3 giả định mỗi workload lặp lại 30 ngày; cột days chỉ dùng cho kịch bản carbon theo thời lượng job thực tế.',
        '', 'Tổng đầu báo cáo giữ kịch bản giảng dạy M5: cộng chi phí API và GPU như hai ngân sách riêng. Chưa có ánh xạ telemetry → workload nên right-size và idle là cơ hội bổ sung, chưa chứng minh độc lập với purchasing. Tổng này là dự phóng, không phải tiết kiệm đã thực hiện. Nếu API và GPU phục vụ cùng traffic, phải chọn một mô hình chi phí để tránh tính hai lần.',
        '', '## Inference: cùng số token, từng đòn bẩy nối tiếp', '',
        '| Bước | USD/ngày | USD/1M-token | Tiết kiệm tăng thêm USD/tháng |', '|---|---:|---:|---:|']
    previous = stages['baseline']
    for name, cost in stages.items():
        lines.append(f'| {name} | {cost:.4f} | {cost / r2["total_tokens"] * 1e6:.3f} | {(previous-cost)*30:.2f} |')
        previous = cost
    conservative_base = stages['baseline']*30 + r3['on_demand_monthly']
    conservative_opt = stages['batch']*30 + r3['optimized_monthly']
    lines += ['', f'Kịch bản chỉ gồm inference + purchasing: ${conservative_base:,.2f} → ${conservative_opt:,.2f}/tháng ({(1-conservative_opt/conservative_base)*100:.1f}% giảm); chưa cộng right-size/idle. GPU không có số token tương ứng nên không quy toàn bộ hóa đơn GPU về USD/1M-token.',
        '', '## Hiệu quả GPU và thứ tự hành động', '',
        'GPU-Util đo tỷ lệ thời gian kernel hoạt động, không đo lượng FLOPs hữu ích. Kernel chờ bộ nhớ hoặc overhead vẫn có thể làm GPU-Util cao. Telemetry phát hiện bất thường nhưng chưa đủ kết luận nguyên nhân; cần profiler và đo throughput/latency.', '']
    for lie in r1['lies']:
        lines.append(f'- {lie["gpu_id"]}: GPU-Util {lie["gpu_util_pct"]:.1f}%, MFU {lie["mfu"]:.3f}, MBU {lie["mbu"]:.3f}.')
    lines += ['', f'Idle: ${r1["idle_waste_daily"]:.2f}/ngày, ${r1["idle_waste_daily"]*30:.2f}/tháng. Hạ GPU một bậc là giả thuyết; phải kiểm tra VRAM, bandwidth, chất lượng và SLA trước khi tính savings thực tế.',
        '', '1. Tắt GPU idle theo lịch và xác minh tag trước chargeback; đo hóa đơn sau thay đổi.',
        '2. Thử cascade trên tập đánh giá chất lượng, rồi cache; chỉ batch tác vụ chấp nhận độ trễ. Cascade đóng góp lớn nhất trong ba lever inference.',
        '3. Checkpoint cho spot; chỉ commit reserved khi có nhu cầu dài hạn. M3 tính reserved theo giờ sử dụng, chưa tính đầy đủ giờ nhàn rỗi/cam kết 3 năm, nên cần xác minh hợp đồng trước triển khai.',
        '', '## Extension 4 — Ngân sách reasoning', '',
        '| Traffic | Request | USD/ngày | Wh/ngày |', '|---|---:|---:|---:|']
    for flag, group in budget['groups'].items():
        lines.append(f'| {"Reasoning" if flag else "Thông thường"} | {group["requests"]} | {group["cost"]:.4f} | {group["wh"]:.2f} |')
    lines += ['', f'Reasoning chiếm {budget["traffic_share"]:.2%} request, {budget["cost_share"]:.2%} chi phí optimized và {budget["energy_share"]:.2%} năng lượng. Hệ số 80× là giả định lab trên cùng số token; output reasoning còn dài 6× trong bộ sinh dữ liệu, không phải phép đo điện thực tế.', '']
    for cap, scenario in budget['caps'].items():
        lines.append(f'- Cap {float(cap):.0%}: chuyển {scenario["rerouted_requests"]} request; tiết kiệm kỳ vọng ${scenario["saved_usd"]:.4f}/ngày và {scenario["saved_wh"]:.2f} Wh/ngày.')
    lines += ['', 'Quy tắc đề xuất: chỉ bật reasoning khi tác vụ nhiều bước và đường trả lời thường không đạt kiểm tra chất lượng; giữ quyền ưu tiên cho tác vụ bắt buộc. Kịch bản cap chọn ngẫu nhiên kỳ vọng, giữ input/model/cache/batch, giảm output về 1/6 và bỏ multiplier năng lượng. Chưa có complexity/confidence trong dataset nên chưa thể kiểm chứng chất lượng; không cộng savings này vào M5.',
        '', '## Extension 5 — Lịch chạy theo carbon', '',
        '| Job có thể gián đoạn | kWh | CO2e us-east-1 (kg) | CO2e europe-north1 (kg) |', '|---|---:|---:|---:|']
    for job in carbon['jobs']:
        lines.append(f'| {job["job_id"]} | {job["wh"]/1000:.2f} | {job["baseline_g"]/1000:.2f} | {job["clean_g"]/1000:.2f} |')
    lines += ['', '| Vùng | USD/kWh | gCO2e/kWh | Điện USD | CO2e kg |', '|---|---:|---:|---:|---:|']
    for region in carbon['regions']:
        lines.append(f'| {region["region"]} | {region["price_kwh"]:.3f} | {region["carbon_kwh"]} | {region["electricity_usd"]:.2f} | {region["carbon_g"]/1000:.2f} |')
    baseline = next(r for r in carbon['regions'] if r['region']=='us-east-1')
    clean = min(carbon['regions'], key=lambda r:r['carbon_g'])
    cheap = min(carbon['regions'], key=lambda r:r['electricity_usd'])
    lines += ['', f'Chuyển sang {clean["region"]}: giảm {(baseline["carbon_g"]-clean["carbon_g"])/1000:.2f} kgCO2e ({(1-clean["carbon_g"]/baseline["carbon_g"])*100:.2f}%) và ${baseline["electricity_usd"]-clean["electricity_usd"]:.2f} tiền điện trong thời lượng các job. Vùng rẻ nhất là {cheap["region"]}, vùng sạch nhất là {clean["region"]}; không có một vùng đồng thời tối thiểu cả hai. us-west-2 là lựa chọn trung gian trong bảng.',
        '', 'Năng lượng = giờ × số GPU × công suất định mức; chưa gồm PUE, CPU, mạng hay checkpoint. Giá điện không phải giá thuê GPU và thường đã nằm trong hóa đơn provider nên không cộng khoản này vào savings GPU. Trước khi di chuyển cần xét dữ liệu, egress, quota, GPU sẵn có và độ trễ; ưu tiên training/offline có thể gián đoạn.',
        '', 'Năng lượng/truy vấn 0.24 Wh ở phần Sustainability là ví dụ 800 token không reasoning; bảng reasoning phía trên mới dùng toàn bộ token thực tế trong dataset.']
    return '\n'.join(lines)+'\n'
