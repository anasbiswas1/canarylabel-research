# Amendment 7 to plan v3 (notebook 04b)

Gate G2's fallback G2a asks for an optimisation attack on the plain judge L1 when A1 alone yields less than 0.20
against it (notebook 04: 0 of 59). The optimiser is random search on the judge's log-probability of answering benign
(Andriushchenko, Croce and Flammarion, ICLR 2025) instead of GCG: it needs only the judge's first-token
log-probabilities, which the vLLM server returns from its prefix cache, where GCG needs a backward pass through the
7B model over the whole tool output for every step; the same paper reports random search at least as strong as GCG
on open models. The attacker is the same: its own copy of the open judge, offline; the deployed labeller is asked
once per seed, on the document the target actually received. Mark 1 is read from this notebook; mark 2 from
notebook 04.
