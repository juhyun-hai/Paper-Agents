# vLLM Backend Setup Guide

This guide explains how to set up and use the vLLM backend for light summarization.

## Prerequisites

- Python 3.11+
- CUDA-capable GPU (recommended)
- vLLM installed (`pip install vllm`)

## Quick Start

### 1. Install vLLM

```bash
pip install vllm
```

### 2. Start vLLM Server

**Option A: Basic (for testing)**
```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct \
  --port 8000 \
  --max-model-len 4096
```

**Option B: With Quantization (recommended for production)**
```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct \
  --port 8000 \
  --quantization awq \
  --max-model-len 4096
```

**Option C: Larger Model**
```bash
vllm serve meta-llama/Llama-3.1-70B-Instruct \
  --port 8000 \
  --tensor-parallel-size 4 \
  --max-model-len 8192
```

### 3. Configure Environment

Add to `.env`:
```bash
SUMMARY_BACKEND=vllm
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
```

### 4. Run Summarization

```bash
# Use vLLM backend from env
python scripts/run_light_summary.py --limit 50

# Override backend via CLI
python scripts/run_light_summary.py --backend vllm --limit 50
```

## Supported Models

Any model supported by vLLM can be used. Recommended models:

**Llama 3.1 Series:**
- `meta-llama/Llama-3.1-8B-Instruct` (recommended for most use cases)
- `meta-llama/Llama-3.1-70B-Instruct` (best quality)

**Mistral Series:**
- `mistralai/Mistral-7B-Instruct-v0.3`
- `mistralai/Mixtral-8x7B-Instruct-v0.1`

**Qwen Series:**
- `Qwen/Qwen2.5-7B-Instruct`
- `Qwen/Qwen2.5-72B-Instruct`

## Timeout Configuration

The vLLM backend uses a tuple timeout of `(5, 300)`:
- **Connect timeout: 5 seconds** - Time to establish connection
- **Read timeout: 300 seconds (5 minutes)** - Time for generation

This allows deep summaries with large models (70B) to complete without timeouts while failing fast on connection issues.

**Why 5 minutes?**
- 70B models can take 30-60 seconds per summary
- Deep summaries may require more tokens (up to 700)
- Network latency + queue time in vLLM
- Provides buffer for slower GPUs

**When to increase:**
- If using models larger than 70B
- If generating very long summaries (>1000 tokens)
- If vLLM server is under heavy load

## Performance Tips

### GPU Memory Optimization

1. **Use quantization** (AWQ or GPTQ):
   ```bash
   vllm serve model-name --quantization awq
   ```

2. **Reduce max model length**:
   ```bash
   vllm serve model-name --max-model-len 2048
   ```

3. **Enable GPU memory fraction**:
   ```bash
   vllm serve model-name --gpu-memory-utilization 0.9
   ```

### Throughput Optimization

1. **Increase batch size**:
   ```bash
   vllm serve model-name --max-num-seqs 64
   ```

2. **Use tensor parallelism** (for multi-GPU):
   ```bash
   vllm serve model-name --tensor-parallel-size 2
   ```

## Troubleshooting

### Connection Refused
```
RuntimeError: vLLM API request failed: Connection refused
```

**Solution:** Ensure vLLM server is running:
```bash
curl http://localhost:8000/v1/models
```

### Timeout Errors
```
RuntimeError: vLLM API timeout (connect=5s, read=300s)
```

**Explanation:**
- Connect timeout: 5 seconds (connection establishment)
- Read timeout: 300 seconds (5 minutes for generation)

**Solutions:**
1. For slow models (70B+), the default 5-minute read timeout should be sufficient
2. If timeouts persist, check vLLM server logs for generation issues
3. For very long summaries, you can increase the timeout in `light_vllm.py`:
   ```python
   timeout=(5, 600)  # 10 minutes for generation
   ```

### Out of Memory
```
CUDA out of memory
```

**Solutions:**
1. Use smaller model (8B instead of 70B)
2. Enable quantization (`--quantization awq`)
3. Reduce `--max-model-len`
4. Reduce `--max-num-seqs`

### JSON Parsing Errors

The pipeline includes automatic retry with a "fix JSON" prompt. If this fails:

1. Check vLLM logs for generation issues
2. Try different model (some models are better at JSON)
3. Increase `max_tokens` in `light_vllm.py` if summaries are truncated

### Slow Generation

**Benchmark your setup:**
```bash
# Test generation speed
time curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.1-8B-Instruct",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }'
```

**Expected speeds:**
- 8B model on A100: ~100-150 tokens/sec
- 8B model on RTX 4090: ~50-80 tokens/sec
- 70B model on 4xA100: ~30-50 tokens/sec

## Cost Estimation

vLLM is free (self-hosted), but consider:

- **GPU costs**: $1-3/hour for cloud GPUs (AWS/GCP)
- **Electricity**: ~$0.10-0.30/hour for consumer GPUs
- **Token throughput**: ~100-150 papers/hour on 8B model

**Example cost:**
- 1000 papers/day
- 8B model on RTX 4090
- ~7 hours runtime
- Cost: ~$2/day in electricity

## Monitoring

Check vLLM server health:
```bash
# Check models
curl http://localhost:8000/v1/models

# Check generation
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.1-8B-Instruct",
    "messages": [{"role": "user", "content": "Test"}],
    "max_tokens": 10
  }'
```

Watch token usage in pipeline logs:
```
Total tokens: 125,000
Avg tokens/paper: 625
```

## Alternative: Use Claude API

If you prefer not to run vLLM locally, you can implement a Claude backend:

1. Add `ANTHROPIC_API_KEY` to `.env`
2. Create `packages/core/summarizers/light_claude.py`
3. Update routing in `light.py`

Claude API is more expensive but requires no GPU infrastructure.
