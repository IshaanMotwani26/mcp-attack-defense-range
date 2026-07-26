\# MCP Attack \& Defense Range



A hands-on security lab that \*\*attacks\*\* AI agents through the Model Context

Protocol (MCP) and \*\*defends\*\* them with a custom multi-layer detection system.

Three real-world attack classes, three complementary defensive layers, one shared

detection engine — with every remaining blind spot documented honestly.



\## Why this exists



MCP is the emerging standard that connects AI agents to external tools. Its

security is still largely unsolved: tool-poisoning attacks were first disclosed in

2025, the first malicious MCP package (`postmark-mcp`) appeared in the wild that

September, and 2026 measurements flag a meaningful share of public servers as

vulnerable. This project builds the attacks, then builds the defenses, to

understand the threat model from both sides.



\## The core thesis



\*\*Effective defense must not depend on the model refusing.\*\* A well-aligned model

often catches these attacks — but a different, older, cheaper, or jailbroken model

may not. So every defense here operates at the infrastructure layer and works

\*regardless of whether the model cooperates\*.



\## Coverage at a glance



| Attack class | What it exploits | Defense | Layer |

|---|---|---|---|

| \*\*Tool poisoning\*\* | Hidden instructions in a tool's \*description\* | Signature scanner | Description (static) |

| \*\*Rug pull\*\* | A tool that ships clean, then silently mutates | Tool pinning (SHA-256 fingerprints) | Description (temporal) |

| \*\*Toxic flow\*\* | Injection arriving in \*data\* a tool returns | Runtime guard (proxy) | Data (runtime) |

| Tool poisoning, \*benign-worded\* | Payload phrased to avoid trigger words | \*Documented gap\* | — honest limitation |



\*\*One detection engine, two enforcement points:\*\* the same rules run at the

description layer (scanner) and the data layer (proxy).



\## Repository layout



&#x20;   agent/host.py            The MCP agent loop (discovers + calls tools via Claude)

&#x20;   servers/

&#x20;     benign\_math.py         Honest control server

&#x20;     poisoned\_math.py       Tool-poisoning variants (V1 tagged, V2 benign-cover, V3 split)

&#x20;     toxic\_flow\_github.py   Clean server; injection rides in on returned issue data

&#x20;     rugpull\_email.py       Ships clean, mutates via a local flag file

&#x20;   scanner/

&#x20;     rules.py               Detection rules + severity/verdict logic

&#x20;     scan.py                Connects to a server, scans all tool descriptions, checks pins

&#x20;     pinning.py             SHA-256 tool fingerprinting for rug-pull detection

&#x20;   proxy/guard.py           Runtime guard: inspects tool RESULTS before the model sees them

&#x20;   attacks/

&#x20;     DAY2..DAY6\_\*.md        Per-phase findings writeups

&#x20;     traces/                JSON evidence of every attack + defense run



\## Quick start



Setup:



&#x20;   uv venv

&#x20;   .venv\\Scripts\\activate

&#x20;   uv add "mcp\[cli]>=1.27,<2" anthropic python-dotenv httpx

&#x20;   # then add your ANTHROPIC\_API\_KEY to a .env file



Run the agent against the benign server:



&#x20;   uv run python agent/host.py servers/benign\_math.py "What is 17 times 4?"



Scan a server for tool poisoning + rug pulls:



&#x20;   uv run python -m scanner.scan servers/poisoned\_math.py



Run the runtime guard against the toxic-flow attack:



&#x20;   uv run python -m proxy.guard servers/toxic\_flow\_github.py "read issue #42 in acme/webapp"



\## Key findings



1\. \*\*A current frontier model refused every naive injection tested\*\* — across four

&#x20;  tool-poisoning framings (Day 2) and the toxic-flow data-channel attack (Day 3).

&#x20;  Model-side safety is a real first line of defense, but not one to rely on.



2\. \*\*The static scanner catches overt poisoning with no false positives\*\*, but has

&#x20;  two documented blind spots: a \*benign-worded\* poisoning variant (V2) evaded its

&#x20;  signature rules, and the toxic-flow server scanned completely clean because its

&#x20;  descriptions are honest — the payload lived in data, not metadata.



3\. \*\*Tool pinning catches rug pulls that description-scanning cannot\*\*, because it

&#x20;  detects \*change itself\*, independent of wording. The mutated tool was flagged by

&#x20;  both pinning and signatures simultaneously.



4\. \*\*The runtime guard closes the toxic-flow gap\*\* by inspecting tool \*results\*

&#x20;  before they reach the model — neutralizing the exact attack the scanner was

&#x20;  blind to, and doing so independently of model behavior.



Full per-phase writeups and JSON traces are in attacks/.



\## Limitations \& future work



\- \*\*Signature detection is evadable by paraphrase.\*\* Both the scanner and the guard

&#x20; share this blind spot. An \*\*LLM-judge inspection pass\*\* (a second model asked

&#x20; "does this contain hidden instructions?") would catch reworded attacks and is the

&#x20; natural next step.

\- The guard withholds an entire flagged result; a more surgical version would strip

&#x20; only the injected span.

\- Attacks were tested against a single model family; cross-model evaluation would

&#x20; strengthen the "don't depend on the model" thesis.

\- Remote/HTTP MCP transports and OAuth flows are out of scope here.



\## Built with



Python 3.12 · MCP Python SDK · Anthropic API · `uv`

