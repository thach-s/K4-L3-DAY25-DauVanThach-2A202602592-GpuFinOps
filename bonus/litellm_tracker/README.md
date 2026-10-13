# Bonus — LiteLLM-style token-cost tracker

A ~60-line proxy that logs token usage, computes **$/request per API key**, and
**hard-stops** requests that would exceed a budget — the token-tier of cost
observability (deck §10). Mock backend, no key required.

```bash
cd bonus/litellm_tracker
python demo.py
```

You'll see `team-chat` blocked once it hits its \$0.05 cap, while `team-eval`
(small model + batch) stays cheap. To use a real provider, replace the `# MOCK
response` block in `tracker.py` with a real `litellm.completion(...)` / SDK call
and read true token counts from the response.

## Phần đã hoàn thiện

Từ thư mục gốc: `.venv/bin/python bonus/litellm_tracker/demo.py`.
Lưu request được chấp nhận, budget, chi phí và lý do block vào
`outputs/bonus/tracker.json`. Budget check và cập nhật spend được khóa cùng nhau,
tránh vượt cap do request đồng thời. Request bị từ chối không cộng phí.

Đây là backend mock với token ước tính theo ký tự, không phải proxy LiteLLM thật.
Nếu nối provider cần reserve chi phí tối đa trước call, đối soát usage thực tế,
lưu spend bền vững và quản lý kỳ ngân sách; tracker hiện dùng bộ nhớ một process.
