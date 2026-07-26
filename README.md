

# MCP Attack & Defense Range

**A security lab that attacks AI agents through the Model Context Protocol (MCP) — then defends them.**

`Python 3.12` · `MCP SDK` · `Anthropic API` · `3 attack classes` · `3 defense layers`

Three real-world attack classes. Three complementary defensive layers. One shared
detection engine. Every remaining blind spot documented honestly.

<br>

---

## Why this exists

MCP is the emerging standard connecting AI agents to external tools — and its
security is still largely unsolved.

- Tool-poisoning attacks were first disclosed in **2025**.
- The first malicious MCP package (`postmark-mcp`) appeared in the wild in **September 2025**.
- **2026** measurements flag a meaningful share of public servers as vulnerable.

This project builds the attacks, then builds the defenses — to understand the threat
model from both sides.

<br>

---

## The core thesis

> **Effective defense must not depend on the model refusing.**

A well-aligned model often catches these attacks. A different, older, cheaper, or
jailbroken model may not. So every defense here operates at the **infrastructure
layer** and works *regardless of whether the model cooperates*.

<br>

---

## Coverage at a glance

| Attack class | What it exploits | Defense | Layer |
|---|---|---|---|
| **Tool poisoning** | Hidden instructions in a tool's *description* | Signature scanner | Description (static) |
| **Rug pull** | A tool that ships clean, then silently mutates | Tool pinning (SHA-256) | Description (temporal) |
| **Toxic flow** | Injection arriving in *data* a tool returns | Runtime guard (proxy) | Data (runtime) |
| Tool poisoning *(benign-worded)* | Payload phrased to dodge trigger words | ⚠️ *Documented gap* | — honest limitation |

> **One detection engine, two enforcement points** — the same rules run at the
> description layer (scanner) and the data layer (proxy).

<br>

---

## Repository layout

    agent/host.py            The MCP agent loop (discovers + calls tools via Claude)
    servers/
      benign_math.py         Honest control server
      poisoned_math.py       Tool-poisoning variants (V1 tagged, V2 benign-cover, V3 split)
      toxic_flow_github.py   Clean server; injection rides in on returned issue data
      rugpull_email.py       Ships clean, mutates via a local flag file
    scanner/
      rules.py               Detection rules + severity/verdict logic
      scan.py                Scans all tool descriptions + checks pins
      pinning.py             SHA-256 tool fingerprinting for rug-pull detection
    proxy/guard.py           Runtime guard: inspects tool RESULTS before the model sees them
    attacks/
      DAY2..DAY6_*.md        Per-phase findings writeups
      traces/                JSON evidence of every attack + defense run

<br>

---

## Quick start

**Setup**

    uv venv
    .venv\Scripts\activate
    uv add "mcp[cli]>=1.27,<2" anthropic python-dotenv httpx
    # then add your ANTHROPIC_API_KEY to a .env file

**Run the agent** against the benign server

    uv run python agent/host.py servers/benign_math.py "What is 17 times 4?"

**Scan a server** for tool poisoning + rug pulls

    uv run python -m scanner.scan servers/poisoned_math.py

**Run the runtime guard** against the toxic-flow attack

    uv run python -m proxy.guard servers/toxic_flow_github.py "read issue #42 in acme/webapp"

<br>

---

## Key findings

**1. The model refused every naive injection tested.**
Across four tool-poisoning framings (Day 2) and the toxic-flow data-channel attack
(Day 3). Model-side safety is a real first line of defense — but not one to rely on.

**2. The static scanner catches overt poisoning with zero false positives.**
But it has two documented blind spots: a *benign-worded* variant (V2) evaded the
signature rules, and the toxic-flow server scanned completely clean because its
descriptions are honest — the payload lived in data, not metadata.

**3. Tool pinning catches rug pulls that description-scanning cannot.**
Because it detects *change itself*, independent of wording. The mutated tool was
flagged by pinning **and** signatures simultaneously.

**4. The runtime guard closes the toxic-flow gap.**
By inspecting tool *results* before they reach the model — neutralizing the exact
attack the scanner was blind to, independently of model behavior.

*Full per-phase writeups and JSON traces live in `attacks/`.*

<br>

---

## Limitations & future work

- **Signature detection is evadable by paraphrase.** Both the scanner and guard
  share this blind spot. An **LLM-judge inspection pass** — a second model asked
  *"does this contain hidden instructions?"* — would catch reworded attacks. Natural
  next step.
- The guard withholds an entire flagged result; a surgical version would strip only
  the injected span.
- Attacks were tested against a single model family; cross-model evaluation would
  strengthen the core thesis.
- Remote/HTTP MCP transports and OAuth flows are out of scope.

<br>

---

<sub>Built by Ishaan Motwani · Cybersecurity @ Purdue</sub>