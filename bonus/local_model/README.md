# Bonus — Đo model CPU thực tế

Từ thư mục gốc, dùng cùng môi trường lab:

```bash
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -r bonus/local_model/requirements.txt
HF_HOME=/tmp/gpufinops-hf .venv/bin/python bonus/local_model/run_local.py
```

Model mặc định `sshleifer/tiny-gpt2` là model kiểm tra rất nhỏ, không đại diện chất lượng LLM production. Có thể chọn model tải sẵn bằng `--model /path/to/model` hoặc `LAB_MODEL`. Tải model cần Internet; không cần API key cho model công khai.

Script chạy CPU ở chế độ eval/inference, warm-up một lần rồi đo 5 lần bằng đồng hồ monotonic. Lưu số token **thực sự sinh ra**, thời gian, tok/s và median vào `outputs/bonus/local_model.json`. Tham số `--tokens`, `--runs`, `--threads`, `--rate` cho phép tái đo.

Chi phí = thời gian / 3600 × giá CPU giả định / output token × 1 triệu. Tok/s là phép đo thật; USD là ước tính từ giá giả định 0.10 USD/giờ. Không gồm tải model, idle, năng lượng hay vận hành. M2 chia chi phí cho input+output, model local chỉ chia cho output; không so sánh trực tiếp chất lượng/giá hai phương án. Thiếu dependency/model sẽ lưu trạng thái `skipped`, không tạo số đo giả.

Nếu không đặt HF_HOME, cache model được lưu trong `.bonus-state/huggingface` của workspace (gitignore).
