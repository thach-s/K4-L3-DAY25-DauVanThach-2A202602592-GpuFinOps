"""Static visual evidence from the same 24-hour synthetic dataset as the exporter."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def plot():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from bonus.docker.exporter import _load
    _, GPUs = _load()
    names = list(GPUs)
    series = [('GPU-Util', 'util', 1), ('MFU', 'mfu', 100), ('MBU', 'mbu', 100)]
    fig, ax = plt.subplots(figsize=(11, 5))
    for offset, (label, key, scale) in enumerate(series):
        values = [sum(GPUs[g][key]) / len(GPUs[g][key]) * scale for g in names]
        ax.bar([i + (offset-1)*.25 for i in range(len(names))], values, width=.25, label=label)
    ax.set_xticks(range(len(names)), names, rotation=35, ha='right')
    ax.set_ylabel('Utilization (%)')
    ax.set_ylim(0, 105)
    ax.set_title('24-hour synthetic GPU telemetry: busy time vs compute/bandwidth efficiency')
    ax.legend()
    ax.grid(axis='y', alpha=.2)
    fig.tight_layout()
    target = ROOT / 'outputs/bonus/gpu_efficiency.png'
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, dpi=130)
    plt.close(fig)
    return target


if __name__ == '__main__':
    print(plot())
