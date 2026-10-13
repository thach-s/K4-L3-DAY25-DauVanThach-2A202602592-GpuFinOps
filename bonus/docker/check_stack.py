"""Verify running local stack; save evidence from real service endpoints."""
import base64
import json
import time
from urllib.error import URLError
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]


def get(url, auth=False):
    request = Request(url)
    if auth:
        request.add_header('Authorization', 'Basic ' + base64.b64encode(b'admin:admin').decode())
    with urlopen(request, timeout=15) as response:
        return response.read().decode()


def main():
    metrics = get('http://127.0.0.1:9101/metrics')
    health = json.loads(get('http://127.0.0.1:3000/api/health'))
    dashboard = json.loads(get('http://127.0.0.1:3000/api/dashboards/uid/lab25-gpu-finops', True))
    datasource = json.loads(get('http://127.0.0.1:3000/api/datasources/uid/lab25-prometheus/health', True))
    assert datasource['status'] == 'OK'
    targets = json.loads(get('http://127.0.0.1:9090/api/v1/targets'))
    query = json.loads(get('http://127.0.0.1:9090/api/v1/query?' + urlencode({'query': 'gpu_mfu'})))
    assert health['database'] == 'ok'
    assert len(dashboard['dashboard']['panels']) == 5
    assert any(t['health'] == 'up' for t in targets['data']['activeTargets'])
    assert len(query['data']['result']) == 11
    output = ROOT / 'outputs/bonus'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'prometheus_metrics.txt').write_text(metrics)
    (output / 'stack_check.json').write_text(json.dumps({
        'status': 'completed', 'grafana_health': health, 'datasource_health': datasource,
        'dashboard_title': dashboard['dashboard']['title'],
        'dashboard_panels': len(dashboard['dashboard']['panels']),
        'prometheus_targets': targets['data']['activeTargets'],
        'gpu_mfu_query': query}, indent=2) + '\n')
    print('PASS: exporter HTTP, Prometheus scrape (11 GPUs), Grafana health and 5-panel provisioned dashboard')


if __name__ == '__main__':
    for attempt in range(15):
        try:
            main()
            break
        except (URLError, AssertionError):
            if attempt == 14:
                raise
            time.sleep(2)
