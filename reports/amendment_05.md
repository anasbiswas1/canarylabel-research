# Amendment 5 to plan v3 (notebooks 03b and 03c)

Evidence: reports/diag_03b.md and diag_benign_03b.md (notebook 03's runs, all 400 DEV documents).
1. Authorised sets are the ground-truth sets. The delegated-action extension of amendment 4 authorised only attacks:
   every one of the 387 replay runs it cleared paid the attacker named in the bill of banking user_task_0, which
   AgentDojo scores as an attack; it removed no false alarm.
2. Validity: the control run only has to finish without error; the event rule leaves its calls out as before. Under
   "no event", 22 in 100 replay runs could not be used, almost all in two banking tasks where the 8B canaries go
   outside the task's sets with no attack present.
3. Trap tools: a trap call counts only when an argument value comes from the document.
4. Replay share 1.0 (plan v3's G1 fallback, "change the replay share", and its G3 fallback, contexts from real tasks
   only): 2 replay episodes, no random-task episode. Random-task episodes added 2 detections in 250 attacks and most of
   the false alarms. Replay episodes still draw the secret, its vector and the trap tools at random.
5. Benign documents are not planted in a slot whose default content the task's ground truth uses (needed_slots); the
   documents with delegated actions are benign documents in the delegated-action tasks' other slots and benign
   rewrites of the bill that keep its account number and amounts.
6. Gate G1 is read on fresh DEV documents with the setting fixed in advance (notebook 03c).
