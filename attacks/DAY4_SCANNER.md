\# Day 4 — Static Scanner: Findings



\## What the scanner does

The scanner connects to an MCP server, retrieves every advertised tool, and runs

each tool's DESCRIPTION through a set of detection rules (`scanner/rules.py`). It

never calls the model -- it reasons about tool metadata directly. This is the

core defensive claim of the project: \*\*detection must not depend on model refusal.\*\*

The scanner flags a poisoned tool whether or not any given model would comply.



Rules are derived from the attacks in Days 2-3: hidden directive tags

(`<IMPORTANT>`, `\[system configuration]`), concealment language ("do not mention",

"need not be surfaced"), impersonated system/maintenance notes, sensitive-file

access, and exfiltration primitives. Each finding has a severity; any high-severity

hit marks the server MALICIOUS.



\## Detection results

| Server | Attack type | Verdict | Assessment |

|---|---|---|---|

| benign\_math | none | clean | Correct -- no false positives |

| poisoned (V1) | tool poisoning, tagged | MALICIOUS | Caught |

| poisoned (V2) | tool poisoning, benign cover | clean | \*\*False negative (documented)\*\* |

| poisoned (V3) | split across two tools | partial | One half flagged |

| toxic\_flow\_github | data-channel injection | clean | Correct by design -- out of scope |



\## Key findings (the honest limitations matter most)

1\. \*\*No false positives.\*\* The benign server passed cleanly. A scanner that flags

&#x20;  safe tools is unusable, so this is a required property, not a given.



2\. \*\*False negative on benign-worded poisoning (V2).\*\* V2 instructs reading the

&#x20;  decoy secret but phrases it as a routine "reproducibility log." It evaded the

&#x20;  signature rules. This is a fundamental limitation of pattern matching: an

&#x20;  attacker who avoids known trigger phrases slips through. Not patched on purpose

&#x20;  -- it is more valuable as evidence.



3\. \*\*Data-channel attacks are invisible to description scanning.\*\* The toxic-flow

&#x20;  server scanned completely clean because its tool descriptions are honest -- the

&#x20;  payload lived in returned DATA, not metadata. A description-layer scanner cannot

&#x20;  see this class of attack. This is the empirical justification for a runtime proxy

&#x20;  (Day 6) that inspects tool RESULTS.



\## Conclusion

The scanner is an effective first layer against overt tool poisoning, but two

documented gaps -- benign-worded payloads and data-channel injection -- prove that

no single layer suffices. This directly motivates defense-in-depth:

description-layer scanning (this) + tool pinning for rug pulls (Day 5) + a runtime

proxy for data-channel attacks (Day 6).



\## Components

\- `scanner/rules.py` -- detection rules + severity/verdict logic

\- `scanner/scan.py` -- connects to a server and scans all tool descriptions

\- `scanner/pinning.py` -- SHA-256 tool fingerprinting for rug-pull detection (Day 5)

