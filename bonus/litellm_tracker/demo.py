"""Mock per-team budget demo with saved evidence; no API keys required."""
import json
from pathlib import Path
from tracker import CostTracker, BudgetExceeded


def main():
    tracker = CostTracker(budgets={'team-chat': .05, 'team-eval': 100})
    blocked = None
    for i in range(40):
        try:
            tracker.complete('team-chat', 'large', 'Summarize this very long document ' * 30)
        except BudgetExceeded as exc:
            blocked = {'accepted_before_block': i, 'reason': str(exc)}
            print(f'BLOCKED after {i} chat requests: {exc}')
            break
    for _ in range(5):
        tracker.complete('team-eval', 'small', 'classify: positive or negative?', batch=True)
    result = {'backend': 'mock', 'budgets_usd': tracker.budgets, 'spend_usd': dict(tracker.spend),
              'blocked': blocked, 'accepted_requests': len(tracker.log), 'requests': tracker.log}
    target = Path(__file__).resolve().parents[2] / 'outputs/bonus/tracker.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + '\n')
    print('per-key spend:', tracker.report())
    print('requests logged:', len(tracker.log))
    print('Saved:', target)


if __name__ == '__main__':
    main()
