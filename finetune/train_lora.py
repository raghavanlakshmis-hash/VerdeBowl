"""
Phase 6 — LoRA fine-tune a small model as the Verde Bowl input-guardrail classifier.
Designed to run on a free Colab T4. Base: Qwen2.5-1.5B-Instruct (swap to Qwen3-1.7B if you like).

Trains the model to emit ONE label (SAFE/OFF_SCOPE/JAILBREAK/INJECTION/POLICY_LEAK/PII/ENCODED)
for a given user message, then evaluates on the held-out ORIGINAL test split and reports
accuracy + per-class recall (Week-5 rigor). Keep a keyword floor as a hard override at serving.

Colab usage (see README.md):
  !pip install -q "transformers>=4.44" "peft>=0.12" "trl>=0.9" "datasets>=2.20" accelerate bitsandbytes
  !python train_lora.py --base Qwen/Qwen2.5-1.5B-Instruct --epochs 3
"""
import argparse, json, os, re
import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, PeftModel
from trl import SFTTrainer, SFTConfig

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CLASSES = ["SAFE", "OFF_SCOPE", "JAILBREAK", "INJECTION", "POLICY_LEAK", "PII", "ENCODED"]


def fmt(tok, instruction, user, label=None):
    msgs = [{"role": "system", "content": instruction}, {"role": "user", "content": user}]
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    return text + (label + tok.eos_token if label is not None else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--out", default=os.path.join(HERE, "adapter"))
    ap.add_argument("--no4bit", action="store_true", help="disable 4-bit (if bitsandbytes unavailable)")
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(args.base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    quant = None if args.no4bit else BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.base, quantization_config=quant, device_map="auto", torch_dtype=torch.float16)
    model = get_peft_model(model, LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))
    model.print_trainable_parameters()

    ds = load_dataset("json", data_files={
        "train": os.path.join(DATA, "train.jsonl"),
        "val": os.path.join(DATA, "val.jsonl")})

    def to_text(ex):
        return {"text": fmt(tok, ex["instruction"], ex["input"], ex["output"])}
    train_ds = ds["train"].map(to_text, remove_columns=ds["train"].column_names)
    val_ds = ds["val"].map(to_text, remove_columns=ds["val"].column_names)

    trainer = SFTTrainer(
        model=model, tokenizer=tok, train_dataset=train_ds, eval_dataset=val_ds,
        args=SFTConfig(
            output_dir=os.path.join(HERE, "runs"), num_train_epochs=args.epochs,
            per_device_train_batch_size=8, gradient_accumulation_steps=2,
            learning_rate=2e-4, warmup_ratio=0.05, logging_steps=10,
            eval_strategy="epoch", save_strategy="epoch", bf16=False, fp16=True,
            max_seq_length=512, dataset_text_field="text", report_to="none"))
    trainer.train()
    model.save_pretrained(args.out)
    tok.save_pretrained(args.out)
    print(f"\nSaved LoRA adapter to {args.out}")

    # -------- eval on held-out ORIGINAL test split --------
    evaluate(model, tok, args)


def evaluate(model, tok, args):
    import collections
    test = [json.loads(l) for l in open(os.path.join(DATA, "test.jsonl"), encoding="utf-8")]
    model.eval()
    correct = 0
    per = collections.defaultdict(lambda: [0, 0])  # label -> [right, total]
    conf = collections.Counter()
    for ex in test:
        text = fmt(tok, ex["instruction"], ex["input"])
        ids = tok(text, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=6, do_sample=False,
                                  pad_token_id=tok.pad_token_id)
        gen = tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
        pred = next((c for c in CLASSES if c in gen.upper()), "SAFE")
        gold = ex["output"]
        per[gold][1] += 1
        if pred == gold:
            correct += 1; per[gold][0] += 1
        else:
            conf[f"{gold}->{pred}"] += 1
    print(f"\n=== held-out test: accuracy {correct}/{len(test)} = {100*correct/len(test):.1f}% ===")
    for c in CLASSES:
        r, t = per[c]
        if t: print(f"  recall {c:12s} {r}/{t} = {100*r/t:.0f}%")
    if conf:
        print("  confusions:", dict(conf))


if __name__ == "__main__":
    main()
