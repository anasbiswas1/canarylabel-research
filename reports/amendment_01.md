# Amendment 1 to plan v3 (notebook 01)

1. Attack pool. The attack documents are AgentDojo v1.2 tool outputs carrying an attack whose goal is a tool action the oracle can see (11 templates; the denial-of-service and manual templates are not used). Injection tasks that only ask the agent to say something move to the instruction pool. Workspace injection tasks without AgentDojo ground truth stay in the pool, and whether they work is decided by instrumented events in real runs (notebook 02).
2. Instruction pool. Injected documents without a tool goal in AgentDojo (BIPIA pairs, tau-bench, the second source, the structural set's embedded forms) carry an instruction but cannot be verified as working by the oracle. They serve as decoys (attack A4) and for the secondary detection result, never as working attacks or as audit attacks.
3. Paraphrase attacker. The Phase 5 caches are paraphrases of BIPIA injections, which have no tool goal. In notebook 04 the paraphrase attacker is applied to AgentDojo goals instead.
4. Control document. The control run leaves the document's vector at its AgentDojo default, the benign value the benchmark ships, so the control is the clean environment of the same task.
5. Event rule. The start time of a new calendar event is a checked argument. Attacks that leak content to a recipient the task may legitimately contact are not visible to the rule; they cannot count as working attacks and are listed in reports/event_check_01.csv.
6. Splits. As in the design log of this notebook, with the held-out templates and goals written to schema/split_keys.json.
