# Phase 6 — Fine-tuned Input-Guardrail Classifier

A small LoRA-fine-tuned model that labels each incoming message
`SAFE / OFF_SCOPE / JAILBREAK / INJECTION / POLICY_LEAK / PII / ENCODED`, so the v1
guardrail runs cheaply on every request. Direct callback to Week 5 — with the Week-5 fix
baked in: **keep a keyword/rule floor as a hard override** at serving time.

## Files
| File | Purpose |
|---|---|
| `build_dataset.py` | Builds train/val/test from `redteam/corpus.csv` (augments TRAIN only; no leakage) |
| `data/` | `train.jsonl` `val.jsonl` `test.jsonl` (Alpaca), `test.csv`, `DATASET_CARD.md` |
| `train_lora.py` | LoRA SFT on a small base model + held-out eval (accuracy + per-class recall) |
| `keyword_floor.py` | Deterministic rule override used at serving (built in Phase 7) |

## 1. Build the dataset (already done locally)
```bash
python build_dataset.py --aug 4      # reads OPENAI_API_KEY from ../redteam/.env
# -> train 264 / val 20 / test 20
```

## 2. Train on Colab (free T4 works)
1. New Colab notebook → **Runtime → Change runtime type → T4 GPU**.
2. Get the code + data into Colab (either):
   - `!git clone <your-repo>` then `cd verde-bowl/finetune`, **or**
   - upload the `finetune/` folder (at least `train_lora.py` + `data/`).
3. Install + train:
   ```python
   !pip install -q "transformers>=4.44" "peft>=0.12" "trl>=0.9" "datasets>=2.20" accelerate bitsandbytes
   !python train_lora.py --base Qwen/Qwen2.5-1.5B-Instruct --epochs 3
   ```
   (Swap `--base Qwen/Qwen3-1.7B` if you prefer; add `--no4bit` if bitsandbytes misbehaves.)
4. It prints held-out **accuracy + per-class recall + confusions**, and saves the adapter to
   `finetune/adapter/`.
5. Download the adapter:
   ```python
   from google.colab import files; import shutil
   shutil.make_archive("verde_adapter", "zip", "adapter"); files.download("verde_adapter.zip")
   ```

## 3. Serve it (Phase 7)
Unzip the adapter into `finetune/adapter/`. The v1 pipeline's **input-guardrail node** loads it
(or falls back to the keyword floor if the adapter isn't present), classifies each message, and
**blocks any non-`SAFE` class before the model sees it**. Report the added latency/cost — the
guardrail runs on every request, so defense-in-depth is not free (that's a graded metric).

## Honest-limits note (for the writeup)
Report accuracy *with* limitations: the test split is small (20 clean originals) and augmentation
is synthetic paraphrase. The keyword floor exists precisely because a small fine-tune misses
obvious attacks; document one residual miss as a finding, not a failure.
