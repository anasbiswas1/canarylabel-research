# Notebook 02 summary

- S0 smoke: qwen7b PASS, twin7b PASS, llama8b PASS, secalign8b PASS
- Task success in clean runs: llama8b 0.285, secalign8b 0.237, qwen7b 0.330, twin7b 0.361
- T1 working units: 461/4895 (AUDIT 122/1184, CAL 32/422, STRESS 20/254, DEV 102/1165, CONFIRM 185/1870)
- On the 287 DEV and CONFIRM units working on T1: T3 15/287, T2 50/287, base Qwen 75/287
- T2 minus base Qwen on those units: -0.087 [-0.132, -0.042]
- Gate P: FAIL (P1 182/320, P2 16/40, P3 9/40)
- Audit: 141 working attack documents, 2694 benign; R = None (empirical safeguard (Proposition 1 not claimed))
- Unit tests: 49 passed
