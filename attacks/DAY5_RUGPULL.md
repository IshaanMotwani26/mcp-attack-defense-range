\# Day 5 — Rug Pulls: Findings



\## What a rug pull is

A rug pull is a time-based attack: an MCP server ships CLEAN, passes inspection,

earns approval -- and then a later version silently changes a tool's behavior.

Because the server was benign at approval time, description scanning at that moment

finds nothing. The real-world case is postmark-mcp: many clean releases, then one

version quietly began BCC-ing every email to an attacker address.



\## Why description scanning alone can't stop it

At approval time there is nothing malicious to flag. The defense must be TEMPORAL:

fingerprint each tool when first approved, then re-check later and detect that the

fingerprint changed. This is tool pinning (scanner/pinning.py): a SHA-256 hash over

each tool's name + description + input schema, stored and compared across scans.



\## Lab setup

\- servers/rugpull\_email.py serves a send\_email tool in one of two forms, chosen by

&#x20; a local flag file (servers/rugpull\_state.txt):

&#x20; - clean: an honest one-line description.

&#x20; - pulled: description mutated to BCC a hidden attacker address and "do not mention

&#x20;   this to the user."

\- Demonstration: scan clean (pin it) -> flip the flag -> scan again.



\## Result

Scan 1 (clean):

&#x20;   \[ OK ] send\_email: clean  |  pin: new

&#x20;   SERVER VERDICT: clean



Scan 2 (after the pull):

&#x20;   \[FAIL] send\_email: MALICIOUS  |  pin: CHANGED (possible rug pull)

&#x20;           - (high) concealment instruction

&#x20;   SERVER VERDICT: MALICIOUS

&#x20;   RUG PULL ALERT: a tool definition changed since it was pinned!



The mutated tool was caught by BOTH layers simultaneously:

1\. Tool pinning: fingerprint no longer matched the pin from Scan 1.

2\. Signature rules: the new "do not mention" phrasing tripped the concealment rule.



\## Key takeaway: the layers cover each other's blind spots

On Day 4, variant V2 (benign-worded poisoning) evaded the signature rules. A rug

pull worded that carefully would evade them too -- but pinning would STILL catch it,

because pinning detects CHANGE itself, independent of wording. Conversely, signature

scanning catches a first-contact poisoned tool that has no prior pin to compare

against. Neither layer is sufficient alone; together they are complementary. This is

defense-in-depth demonstrated empirically, not asserted.



\## Components

\- scanner/pinning.py -- SHA-256 tool fingerprinting, pin storage, change detection

\- scanner/scan.py    -- now checks pins on every scan and raises a rug-pull alert

\- servers/rugpull\_email.py -- the clean-then-mutated demonstration server

