# Notebook 02d diagnosis

Q1 T1 units: security check passed 302, event only 528, not working 4065.
AUDIT working documents: 70 by the security check, 209 by security or event; R under the security check: (None, 'empirical safeguard (Proposition 1 not claimed)').

Q2 second pilot by verification basis (attack seen / documents):
- any / task done and no event: security 6/13, event only 11/27, benign 5/40
- any / no event: security 10/13, event only 20/27, benign 5/40
- control / task done and no event: security 6/13, event only 11/27, benign 5/40
- control / no event: security 10/13, event only 20/27, benign 5/40
- control+twin / task done and no event: security 6/13, event only 8/27, benign 4/40
- control+twin / no event: security 10/13, event only 18/27, benign 4/40
- control+sourced / task done and no event: security 5/13, event only 2/27, benign 1/40
- control+sourced / no event: security 7/13, event only 9/27, benign 1/40
- control+twin+sourced / task done and no event: security 5/13, event only 2/27, benign 1/40
- control+twin+sourced / no event: security 7/13, event only 9/27, benign 1/40
- control+sourced-plus / task done and no event: security 5/13, event only 2/27, benign 1/40
- control+sourced-plus / no event: security 7/13, event only 9/27, benign 1/40

Q3 projection (validity no event), P(attack seen) for security-verified attacks and benign documents:
- control, 2 episodes, 1 pair(s): security 0.819, event only 0.649, benign 0.119
- control, 2 episodes, 2 pair(s): security 0.412, event only 0.171, benign 0.007
- control, 4 episodes, 1 pair(s): security 0.964, event only 0.923, benign 0.219
- control, 4 episodes, 2 pair(s): security 0.814, event only 0.674, benign 0.031
- control, 6 episodes, 1 pair(s): security 0.992, event only 0.971, benign 0.303
- control, 6 episodes, 2 pair(s): security 0.947, event only 0.844, benign 0.065
- control, 8 episodes, 1 pair(s): security 0.999, event only 0.993, benign 0.375
- control, 8 episodes, 2 pair(s): security 0.990, event only 0.951, benign 0.103
- control+sourced, 2 episodes, 1 pair(s): security 0.631, event only 0.279, benign 0.025
- control+sourced, 2 episodes, 2 pair(s): security 0.287, event only 0.025, benign 0.001
- control+sourced, 4 episodes, 1 pair(s): security 0.801, event only 0.549, benign 0.047
- control+sourced, 4 episodes, 2 pair(s): security 0.564, event only 0.175, benign 0.003
- control+sourced, 6 episodes, 1 pair(s): security 0.873, event only 0.666, benign 0.068
- control+sourced, 6 episodes, 2 pair(s): security 0.706, event only 0.292, benign 0.007
- control+sourced, 8 episodes, 1 pair(s): security 0.920, event only 0.783, benign 0.088
- control+sourced, 8 episodes, 2 pair(s): security 0.807, event only 0.454, benign 0.012
- control+sourced-plus, 2 episodes, 1 pair(s): security 0.631, event only 0.279, benign 0.025
- control+sourced-plus, 2 episodes, 2 pair(s): security 0.287, event only 0.025, benign 0.001
- control+sourced-plus, 4 episodes, 1 pair(s): security 0.801, event only 0.549, benign 0.047
- control+sourced-plus, 4 episodes, 2 pair(s): security 0.564, event only 0.175, benign 0.003
- control+sourced-plus, 6 episodes, 1 pair(s): security 0.873, event only 0.666, benign 0.068
- control+sourced-plus, 6 episodes, 2 pair(s): security 0.706, event only 0.292, benign 0.007
- control+sourced-plus, 8 episodes, 1 pair(s): security 0.920, event only 0.783, benign 0.088
- control+sourced-plus, 8 episodes, 2 pair(s): security 0.807, event only 0.454, benign 0.012

T1 in DEPLOY tasks (runs; any event; not in the clean run; sourced and new):
- attack: 40; 13; 10; 3
- benign: 40; 7; 6; 0

Unit tests: 66 passed
