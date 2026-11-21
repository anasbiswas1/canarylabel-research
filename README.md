# Canary-labelled, risk-gated adaptation for prompt-injection detectors

Working repository for a research project by Md Anas Biswas (School of Computing, University of Portsmouth).

Some prompt-injection detectors keep learning after deployment: when a small detector is unsure about a document, something else labels it, and the label is used to update the detector. If a language model makes that label, the attacker's document can tell it to answer "benign", and the detector learns the attack as safe. This project builds a label source the attacker cannot steer without its attack failing: canary agents run the document in random contexts it cannot predict, on the protected agent's own base model, and only measured security events (a planted secret leaving, a trap tool used, an unauthorised argument, a forbidden action) count. Updates pass a risk gate with a guarantee under repeated use of one audit set, and an online monitor checks the assumption behind the label guarantee during deployment and triggers rollback when it breaks.

## Status

Setup. Notebooks arrive one by one, each with its own pre-registered marks.

## Layout

```
notebooks/   numbered from 00; each ends with the standard commit cell
src/         paths, cache keys, environments, canary oracle, labellers, attackers, escalation, vetoes, gate, monitor, updates
tools/       commit_cell.py, the single commit step
tests/       checks that run without the network
schema/      task bank, authorised and forbidden action sets, attack templates
reports/     plans, decisions, result tables, plan_frozen.json before confirmation
figures/     600 dpi figures with paper names in legends and axes
tables/      manuscript tables
data/        caches, streams, checkpoints; ignored by git
```

## Shared inputs

Detectors, the second indirect source, the AgentDojo set and the paraphrase caches come from picalib-research; the rebuilt public sets of Liu (arXiv 2610.03448) and the continued Wolf Defender checkpoints come from wani-research. They are read in place through `src/paths.py`, never copied, and recorded with sha256 in `data_manifest.json`. Open-weight models are loaded from Hugging Face with their revisions pinned in the notebooks that use them.

## Working rules

- Every notebook states CPU or GPU from a written count of model calls, and is dry-run on a mock before use.
- Every model output is cached under the full key of `src/cachekey.py` and reused only when every field matches.
- Development, calibration, audit, stress and confirmation data are kept apart; the audit set is touched only by the gate.
- Commits go through `tools/commit_cell.py` from a notebook's last cell; it strips outputs, refuses `data/`, model weights and secrets, commits and pushes.

## Session bootstrap (first cell of every notebook)

```python
from google.colab import drive; drive.mount("/content/drive")
import os, sys, subprocess
PROJECT_ROOT = "/content/drive/MyDrive/CanaryLabel_Research"
REPO_DIR = PROJECT_ROOT + "/canarylabel-research"
os.environ["CANARY_DRIVE"] = "/content/drive/MyDrive"
os.environ["CANARY_PROJECT_ROOT"] = PROJECT_ROOT
os.environ["CANARY_REPO_ROOT"] = REPO_DIR
os.chdir(REPO_DIR); sys.path.insert(0, "src")
print(subprocess.run(["git", "pull", "--ff-only"], capture_output=True, text=True).stdout)
```

## Licence and citation

MIT licence. Citation details are in `CITATION.cff`.
