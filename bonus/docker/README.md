# Bonus — Prometheus + Grafana

Từ **thư mục gốc** của lab:

```bash
mkdir -p .bonus-state/grafana .bonus-state/prometheus
LAB_UID=$(id -u) LAB_GID=$(id -g) docker compose -p gpufinops-bonus -f bonus/docker/docker-compose.yml up -d
.venv/bin/python bonus/docker/check_stack.py
.venv/bin/python bonus/run_all.py --stack --skip-model
```

Grafana: http://localhost:3000/d/lab25-gpu-finops (admin/admin trong lab).
Prometheus: http://localhost:9090. Exporter: http://localhost:9101/metrics.
Các cổng chỉ bind localhost; Grafana anonymous bị tắt.

Dữ liệu hai dịch vụ giữ trong `.bonus-state/` (gitignore) ở workspace, tránh phân vùng Docker chật. UID/GID mặc định là 1000; câu lệnh trên đặt theo user Linux hiện tại. Grafana `/tmp` dùng tmpfs 64 MB. Grafana pin 11.6.0 để giảm kích thước image; Python và Prometheus giữ tag của bài gốc. Image IDs, manifest Grafana và phiên bản runtime nằm trong `outputs/bonus/`.

Dashboard có 5 panel: GPU-Util, MFU, proxy chi phí capacity, MBU và công suất. Datasource có UID cố định. `check_stack.py` kiểm tra HTTP exporter, Prometheus target UP, query 11 GPU, Grafana health, datasource health và dashboard provisioning, rồi lưu `outputs/bonus/stack_check.json`. Script chờ tối đa khoảng 30 giây để dịch vụ sẵn sàng.

Không có Docker, exporter vẫn chạy độc lập:

```bash
.venv/bin/python bonus/docker/exporter.py
# Mở http://localhost:9101/metrics
```

Export mặc định bind 127.0.0.1; bên trong Compose dùng HOST=0.0.0.0 để Prometheus truy cập qua network container.

**Giới hạn:** dữ liệu là trung bình 24 giờ synthetic, không phải telemetry GPU live. `(1-MFU) × giá/giờ` chỉ là proxy capacity FLOPs không sử dụng, không chứng minh tiền có thể thu hồi. MFU thấp ở decode có thể hợp lý. Không cộng proxy vào savings M5. Hình snapshot từ cùng dataset: `outputs/bonus/gpu_efficiency.png`.

Dừng stack (giữ dữ liệu workspace):

```bash
docker compose -p gpufinops-bonus -f bonus/docker/docker-compose.yml down
```
