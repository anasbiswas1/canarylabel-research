# Notebook 02c summary

- F0 parser: 0.960 of notebook 02's dropped calls read (PASS)
- S0 smoke: qwen7b PASS, twin7b PASS, llama8b PASS, secalign8b PASS
- Task success in clean runs: llama8b 0.340, secalign8b 0.289, qwen7b 0.474, twin7b 0.485
- T1 working units: 830/4895 (AUDIT 202/1184, CAL 61/422, STRESS 48/254, DEV 181/1165, CONFIRM 338/1870)
- On the 519 DEV and CONFIRM units working on T1: T3 114/519, T2 254/519, base Qwen 304/519
- T2 minus base Qwen on those units: -0.096 [-0.144, -0.048]
- Gate P (control+sourced, no event): FAIL (P1 286/320, P2 16/40, P3 1/40)
- Audit: 209 working attack documents, 2694 benign; R = None (empirical safeguard (Proposition 1 not claimed))
- Unit tests: 65 passed
