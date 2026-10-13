"""Measure warmed CPU generation; save raw observations and explicit skip status."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def unit_cost(seconds, tokens, rate_hr):
    if seconds <= 0 or tokens <= 0 or rate_hr < 0:
        raise ValueError('seconds/tokens must be positive and hourly rate nonnegative')
    return seconds * rate_hr / 3600 / tokens * 1e6


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default=os.getenv('LAB_MODEL', 'sshleifer/tiny-gpt2'))
    parser.add_argument('--runs', type=int, default=5)
    parser.add_argument('--tokens', type=int, default=64)
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--rate', type=float, default=float(os.getenv('LAB_CPU_RATE_HR', '.10')))
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/bonus/local_model.json')
    args = parser.parse_args()
    if min(args.runs, args.tokens, args.threads) < 1 or args.rate < 0:
        parser.error('runs/tokens/threads must be positive; rate must be nonnegative')
    os.environ.setdefault('HF_HOME', str(ROOT / '.bonus-state/huggingface'))
    result = {'model': args.model, 'status': 'skipped', 'rate_usd_hr': args.rate,
              'device': 'cpu', 'threads': args.threads}
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import transformers
        result["versions"] = {"torch": torch.__version__, "transformers": transformers.__version__}
        torch.set_num_threads(args.threads)
        torch.manual_seed(25)
        tokenizer = AutoTokenizer.from_pretrained(args.model)
        model = AutoModelForCausalLM.from_pretrained(args.model).to('cpu').eval()
        inputs = tokenizer('GPU FinOps means measuring cost per million tokens because', return_tensors='pt')
        def generate():
            with torch.inference_mode():
                return model.generate(**inputs, max_new_tokens=args.tokens, do_sample=False,
                                      pad_token_id=tokenizer.eos_token_id)
        generate()  # warm-up excluded; loading/download costs also excluded
        samples = []
        for _ in range(args.runs):
            start = time.perf_counter()
            output = generate()
            seconds = time.perf_counter() - start
            count = output.shape[-1] - inputs['input_ids'].shape[-1]
            samples.append({'seconds': seconds, 'output_tokens': count,
                            'tokens_per_second': count / seconds,
                            'usd_per_million_output_tokens': unit_cost(seconds, count, args.rate)})
        from missions.m2_inference_levers import run
        simulation = run(False)
        result.update(status='completed', samples=samples,
                      median_tokens_per_second=statistics.median(s['tokens_per_second'] for s in samples),
                      median_usd_per_million_output_tokens=statistics.median(s['usd_per_million_output_tokens'] for s in samples),
                      simulation_usd_per_million_all_tokens=simulation['optimized_per_m'],
                      generated_text=tokenizer.decode(output[0], skip_special_tokens=True),
                      limitations='Tiny test model; no quality parity. Local cost uses output tokens only, simulation uses input+output. Assumed CPU rental rate, excludes idle/load/network/energy.')
    except (ImportError, OSError) as exc:
        result['reason'] = str(exc)
        print('[skip] Model/dependencies unavailable. Install bonus/local_model/requirements.txt or supply a local --model path.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
