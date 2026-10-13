"""Additional checks; original grading tests remain unchanged."""
import pytest
from missions import m2_inference_levers as m2, m3_purchasing as m3


def test_sequential_levers_and_reasoning_cap():
    result = m2.run(False)
    stages = list(result['stages'].values())
    assert all(a >= b for a, b in zip(stages, stages[1:]))
    assert stages[-1] == pytest.approx(result['optimized_daily'], abs=.005)
    groups = result['reasoning_budget']['groups']
    assert sum(g['requests'] for g in groups.values()) == 2400
    assert sum(g['cost'] for g in groups.values()) == pytest.approx(stages[-1])
    caps = result['reasoning_budget']['caps']
    assert caps['0.1']['rerouted_requests'] == 0
    assert caps['0.05']['rerouted_requests'] == groups[True]['requests'] - 120
    assert 0 < caps['0.05']['saved_usd'] < groups[True]['cost']
    assert 0 < caps['0.05']['saved_wh'] < groups[True]['wh']


def test_carbon_uses_actual_duration_and_distinct_region_objectives():
    result = m3.run(False)['carbon_schedule']
    training = next(j for j in result['jobs'] if j['job_id'] == 'job-train-llm')
    assert training['wh'] == 20 * 14 * 8 * 700
    assert training['clean_g'] / training['baseline_g'] == pytest.approx(30 / 380)
    assert sum(j['wh'] for j in result['jobs']) == result['total_wh']
    assert min(result['regions'], key=lambda r: r['carbon_g'])['region'] == 'europe-north1'
    assert min(result['regions'], key=lambda r: r['electricity_usd'])['region'] == 'us-east-wa'
