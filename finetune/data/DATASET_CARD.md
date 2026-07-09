# Verde Bowl Guardrail — Fine-tune Dataset

Built from `redteam/corpus.csv` by `build_dataset.py` (aug=4).
Split by ORIGINAL case first, then TRAIN-only augmentation (no paraphrase leakage into val/test).

## Sizes
- train: 264  (SAFE=60 OFF_SCOPE=26 JAILBREAK=22 INJECTION=44 POLICY_LEAK=56 PII=26 ENCODED=30)
- val:   20  (SAFE=4 OFF_SCOPE=2 JAILBREAK=2 INJECTION=4 POLICY_LEAK=4 PII=2 ENCODED=2)
- test:  20  (SAFE=4 OFF_SCOPE=2 JAILBREAK=2 INJECTION=4 POLICY_LEAK=4 PII=2 ENCODED=2)

## Classes
SAFE, OFF_SCOPE, JAILBREAK, INJECTION, POLICY_LEAK, PII, ENCODED

## Notes
- val/test are clean ORIGINAL corpus cases (real-grounded subset included).
- ENCODED train aug is programmatic (fresh base64/rot13/leet/reversed/spaced); text families are LLM-paraphrased.
- Keep a keyword/rule floor as a hard override at serving time (Week-5 finding).