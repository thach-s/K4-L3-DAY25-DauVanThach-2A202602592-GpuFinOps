"""Run available bonuses and build a measured submission report, without installing anything."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stack', action='store_true', help='Verify an already running Docker stack')
    parser.add_argument('--skip-model', action='store_true', help='Reuse existing model measurements')
    args = parser.parse_args()
    for service in ('grafana', 'prometheus'):
        (ROOT / '.bonus-state' / service).mkdir(parents=True, exist_ok=True)
    folder = ROOT / 'outputs/bonus'
    folder.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(ROOT / 'bonus/litellm_tracker/demo.py')], check=True)
    if not args.skip_model:
        subprocess.run([sys.executable, str(ROOT / 'bonus/local_model/run_local.py')], check=True)
    from bonus.docker.exporter import render
    (folder / 'prometheus_metrics.txt').write_text(render())
    if args.stack:
        subprocess.run([sys.executable, str(ROOT / 'bonus/docker/check_stack.py')], check=True)
    from bonus.docker.snapshot import plot
    plot()
    tracker = json.loads((folder / 'tracker.json').read_text())
    model = json.loads((folder / 'local_model.json').read_text()) if (folder / 'local_model.json').exists() else {'status':'not run'}
    stack = json.loads((folder / 'stack_check.json').read_text()) if (folder / 'stack_check.json').exists() else {'status':'not run'}
    lines = ['# Bonus — GPU FinOps', '', '## 1. LiteLLM-style tracker (mock)', '',
             f"Đã nhận {tracker['accepted_requests']} request; chat bị chặn sau {tracker['blocked']['accepted_before_block']} request.",
             f"Chi phí chat ${tracker['spend_usd']['team-chat']:.6f} ≤ cap $0.05; eval ${tracker['spend_usd']['team-eval']:.6f}.",
             'Budget check/update được khóa để xử lý đồng thời; request bị chặn không tính phí. Backend mock, token ước tính theo ký tự; chưa gọi LiteLLM/provider thật. Spend ở RAM một process, không phải ledger production.',
             '', 'Evidence: [tracker.json](bonus/tracker.json).', '', '## 2. Model chạy CPU', '', f"Trạng thái: **{model['status']}**."]
    if model['status'] == 'completed':
        lines += [f"Model `{model['model']}`; median **{model['median_tokens_per_second']:.2f} output tok/s**, ước tính **${model['median_usd_per_million_output_tokens']:.3f}/1M output token** với CPU ${model['rate_usd_hr']:.2f}/giờ.",
                  f"M2 optimized = ${model['simulation_usd_per_million_all_tokens']:.3f}/1M input+output token. Hai mẫu số và chất lượng khác nhau, không thể kết luận model local rẻ hơn/tốt hơn API từ phép so sánh này.",
                  'Warm-up một lần, đo 5 lần; loại thời gian tải/load khỏi throughput. Tiny GPT-2 chỉ kiểm tra cơ chế, không phải model trả lời chất lượng production.',
                  '', '| Lần | Output token | Giây | Tok/s | USD/1M output token |', '|---|---:|---:|---:|---:|']
        for i, sample in enumerate(model['samples'], 1):
            lines.append(f"| {i} | {sample['output_tokens']} | {sample['seconds']:.4f} | {sample['tokens_per_second']:.2f} | {sample['usd_per_million_output_tokens']:.3f} |")
    else:
        lines.append(model.get('reason','Chưa chạy.'))
    lines += ['', 'Evidence: [local_model.json](bonus/local_model.json).', '', '## 3. Prometheus + Grafana', '',
              f"Trạng thái kiểm tra stack: **{stack['status']}**. Exporter xuất GPU-Util, MFU, MBU, công suất và proxy chi phí capacity cho 11 GPU."]
    if stack['status'] == 'completed':
        lines.append(f"HTTP exporter hoạt động; Prometheus scrape UP và query trả về 11 GPU; Grafana database/datasource OK, dashboard provisioned {stack['dashboard_panels']} panel.")
    if stack['status'] == 'completed':
        lines.append(f"Grafana runtime: {stack['grafana_health'].get('version', 'n/a')}. Dữ liệu Grafana/Prometheus giữ trong `.bonus-state/` của workspace; image IDs: [docker_image_ids.txt](bonus/docker_image_ids.txt).")
    lines += ['Dashboard: http://localhost:3000/d/lab25-gpu-finops (admin/admin cho lab). Prometheus: http://localhost:9090.',
              'Telemetry là trung bình của 24 giờ synthetic; `(1-MFU) × giá/giờ` là proxy capacity FLOPs, không phải mức lãng phí thu hồi được. Không cộng số này vào tiết kiệm M5.',
              '', '![Đối chiếu GPU-Util, MFU và MBU từ dữ liệu synthetic 24 giờ](bonus/gpu_efficiency.png)',
              '', 'Evidence: [stack_check.json](bonus/stack_check.json), [metrics](bonus/prometheus_metrics.txt).', '', '## Tái chạy', '',
              '```bash', '.venv/bin/python bonus/run_all.py',
              'docker compose -p gpufinops-bonus -f bonus/docker/docker-compose.yml up -d',
              '.venv/bin/python bonus/run_all.py --stack --skip-model',
              'docker compose -p gpufinops-bonus -f bonus/docker/docker-compose.yml down', '```',
              '', 'Phiên bản Python đã chạy: [python_environment.txt](bonus/python_environment.txt). Dependencies model và thao tác Docker: xem README của từng bonus. Chi phí CPU là giá giả định, còn throughput là phép đo trên máy hiện tại.']
    (ROOT / 'outputs/bonus_report.md').write_text('\n'.join(lines)+'\n')
    print('Written outputs/bonus_report.md')


if __name__ == '__main__':
    main()
