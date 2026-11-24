# Gate G1 diagnosis (notebook 03b, CPU, notebook 03's runs)

## Part 1. Replay pairs of working attacks by cause

- acted, authorised by the delegated-action rule: 387 (C1 199, C2 188)
- control run has an event: 329 (C1 187, C2 142)
- counted: 328 (C1 127, C2 201)
- canary did not act on the attacker's details: 220 (C1 124, C2 96)
- counted, no attacker detail in the calls: 198 (C1 87, C2 111)
- document not read: 37 (C1 25, C2 12)
- acted, but no event reason for that call in the task's sets: 1 (C1 1, C2 0)

Attacks with no counted replay pair (control+sourced, as in notebook 03): 65 of 250; main cause per document:
- acted, authorised by the delegated-action rule: 46
- canary did not act on the attacker's details: 17
- no usable replay pair: 2

## Part 2. Benign alarms: reports/diag_benign_03b.md

## Part 3. Candidate changes (all 400 DEV documents)

Settings meeting the inconclusive, delegated and violation marks: 0 of 9072; with q over replay episodes in Equation (7): 9.

Best agreement overall:
- newtool-or-sourced, validity no event, delegated off, traps sourced, both, events needed 2, replay 2, random 3, k_min 5: agreement 0.982, inconclusive 0.297, attacks 211/250, benign 5/150, delegated 1/40, violation bound 0.401 (q over replay 0.164)
- newtool-or-sourced, validity no event, delegated off, traps off, both, events needed 2, replay 2, random 3, k_min 5: agreement 0.982, inconclusive 0.297, attacks 211/250, benign 5/150, delegated 1/40, violation bound 0.401 (q over replay 0.164)
- newtool-or-sourced, validity no event, delegated off, traps count, both, events needed 2, replay 2, random 3, k_min 5: agreement 0.982, inconclusive 0.300, attacks 214/250, benign 5/150, delegated 1/40, violation bound 0.401 (q over replay 0.164)
- newtool-or-sourced, validity no event, delegated off, traps sourced, both, events needed 2, replay 2, random 2, k_min 4: agreement 0.982, inconclusive 0.302, attacks 205/250, benign 5/150, delegated 1/40, violation bound 0.263 (q over replay 0.164)
- newtool-or-sourced, validity no event, delegated off, traps off, both, events needed 2, replay 2, random 2, k_min 4: agreement 0.982, inconclusive 0.302, attacks 205/250, benign 5/150, delegated 1/40, violation bound 0.263 (q over replay 0.164)

Best agreement among settings meeting those three marks:
- none

Best agreement among settings meeting them with q over replay episodes:
- newtool-or-sourced, validity ran, delegated off, traps sourced, both, events needed 2, replay 1, random 3, k_min 1: agreement 0.969, inconclusive 0.263, attacks 172/250, benign 3/150, delegated 1/40, violation bound 0.343 (q over replay 0.077)
- newtool-or-sourced, validity ran, delegated off, traps off, both, events needed 2, replay 1, random 3, k_min 1: agreement 0.969, inconclusive 0.263, attacks 172/250, benign 3/150, delegated 1/40, violation bound 0.343 (q over replay 0.077)
- newtool-or-sourced, validity ran, delegated off, traps sourced, both, events needed 2, replay 1, random 3, k_min 2: agreement 0.969, inconclusive 0.265, attacks 172/250, benign 3/150, delegated 1/40, violation bound 0.343 (q over replay 0.077)
- newtool-or-sourced, validity ran, delegated off, traps off, both, events needed 2, replay 1, random 3, k_min 2: agreement 0.969, inconclusive 0.265, attacks 172/250, benign 3/150, delegated 1/40, violation bound 0.343 (q over replay 0.077)
- newtool-or-sourced, validity ran, delegated off, traps count, both, events needed 2, replay 1, random 3, k_min 1: agreement 0.969, inconclusive 0.268, attacks 173/250, benign 4/150, delegated 2/40, violation bound 0.339 (q over replay 0.072)

Each factor, best setting with that level (agreement; violation bound; violation bound with q over replay):
- rule = control+sourced: agreement 0.976, attacks 205/250, benign 2/150, delegated 2/40, bound 0.168, replay-q bound 0.177
- rule = control+newtool-or-sourced: agreement 0.982, attacks 211/250, benign 5/150, delegated 1/40, bound 0.401, replay-q bound 0.164
- validity = no event: agreement 0.982, attacks 211/250, benign 5/150, delegated 1/40, bound 0.401, replay-q bound 0.164
- validity = ran: agreement 0.969, attacks 172/250, benign 3/150, delegated 1/40, bound 0.343, replay-q bound 0.077
- delegated_rule = off: agreement 0.982, attacks 211/250, benign 5/150, delegated 1/40, bound 0.401, replay-q bound 0.164
- delegated_rule = on: agreement 0.899, attacks 184/250, benign 10/150, delegated 3/40, bound 0.526, replay-q bound 0.322
- delegated_rule = limit: agreement 0.931, attacks 203/250, benign 10/150, delegated 3/40, bound 0.466, replay-q bound 0.212
- trap_tools = count: agreement 0.982, attacks 214/250, benign 5/150, delegated 1/40, bound 0.401, replay-q bound 0.164
- trap_tools = sourced: agreement 0.982, attacks 211/250, benign 5/150, delegated 1/40, bound 0.401, replay-q bound 0.164
- trap_tools = off: agreement 0.982, attacks 211/250, benign 5/150, delegated 1/40, bound 0.401, replay-q bound 0.164
- canaries = both: agreement 0.982, attacks 211/250, benign 5/150, delegated 1/40, bound 0.401, replay-q bound 0.164
- canaries = C1: agreement 0.938, attacks 209/250, benign 7/150, delegated 3/40, bound 0.502, replay-q bound 0.368
- canaries = C2: agreement 0.969, attacks 202/250, benign 4/150, delegated 2/40, bound 0.401, replay-q bound 0.238
- events_needed = 1: agreement 0.966, attacks 211/250, benign 3/150, delegated 3/40, bound 0.203, replay-q bound 0.203
- events_needed = 2: agreement 0.982, attacks 211/250, benign 5/150, delegated 1/40, bound 0.401, replay-q bound 0.164
