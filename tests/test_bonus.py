"""Bonus budget guard, unit economics, exporter endpoint and dashboard checks."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import threading
from urllib.request import urlopen
from http.server import HTTPServer
import pytest
from bonus.litellm_tracker.tracker import CostTracker, BudgetExceeded
from bonus.local_model.run_local import unit_cost
from bonus.docker.exporter import Handler, render


def test_budget_guard_is_atomic_and_rejected_requests_are_free():
    tracker = CostTracker({'team': .01})
    def request(_):
        try:
            tracker.complete('team', 'large', 'hello', max_output_tokens=256)
            return True
        except BudgetExceeded:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        accepted = sum(pool.map(request, range(40)))
    assert accepted == 2
    assert len(tracker.log) == accepted
    assert tracker.spend['team'] <= .01
    before = tracker.spend['team']
    with pytest.raises(BudgetExceeded):
        tracker.complete('team', 'large', 'hello')
    assert tracker.spend['team'] == before
    with pytest.raises(ValueError):
        tracker.complete('team', 'small', 'hello', max_output_tokens=-1)


def test_unit_cost_uses_generated_tokens_and_elapsed_time():
    assert unit_cost(3600, 1000000, .1) == pytest.approx(.1)
    with pytest.raises(ValueError):
        unit_cost(1, 0, .1)


def test_exporter_metrics_http_and_dashboard():
    metrics = render()
    for name in ('gpu_mfu', 'gpu_util_pct', 'gpu_mbu', 'gpu_power_w'):
        assert sum(line.startswith(name + '{') for line in metrics.splitlines()) == 11
    dashboard = json.loads(Path('bonus/docker/grafana/dashboards/gpu_cost.json').read_text())
    assert len({panel['id'] for panel in dashboard['panels']}) == 5
    assert all(panel['datasource']['uid'] == 'lab25-prometheus' for panel in dashboard['panels'])
    try:
        server = HTTPServer(('127.0.0.1', 0), Handler)
    except PermissionError:
        pytest.skip('Sandbox blocks localhost sockets; rerun outside sandbox for HTTP integration')
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        base = f'http://127.0.0.1:{server.server_port}'
        with urlopen(base + '/metrics') as response:
            assert response.status == 200
            assert response.read().decode() == metrics
        with urlopen(base + '/health') as response:
            assert response.read() == b'ok\n'
    finally:
        server.shutdown()
        worker.join()
        server.server_close()
