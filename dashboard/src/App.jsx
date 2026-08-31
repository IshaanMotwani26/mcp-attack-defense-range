import React, { useEffect, useState, useRef } from "react";
import { getScenarios, getRuns, getRun, openScan, resetPins } from "./api.js";

const VERDICT_CLASS = {
  clean: "v-clean",
  SUSPICIOUS: "v-warn",
  MALICIOUS: "v-malic",
  control: "v-clean",
};

function AttackTag({ cls }) {
  return <span className={`tag tag-${cls}`}>{cls}</span>;
}

export default function App() {
  const [scenarios, setScenarios] = useState([]);
  const [selected, setSelected] = useState(null);
  const [running, setRunning] = useState(false);
  const [channels, setChannels] = useState([]);
  const [verdict, setVerdict] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | scanning | done | error
  const [runs, setRuns] = useState([]);
  const [detail, setDetail] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    getScenarios().then((s) => {
      setScenarios(s);
      setSelected((cur) => cur ?? s.find((x) => x.attack_class !== "control")?.id ?? s[0]?.id);
    });
    getRuns().then(setRuns);
  }, []);

  function runScan() {
    if (!selected || running) return;
    setRunning(true);
    setStatus("scanning");
    setChannels([]);
    setVerdict(null);
    setDetail(null);

    const ws = openScan(selected, (evt) => {
      if (evt.event === "tool") {
        setChannels((prev) => [...prev, evt]);
      } else if (evt.event === "verdict") {
        setVerdict(evt);
      } else if (evt.event === "saved") {
        setStatus("done");
        setRunning(false);
        getRuns().then(setRuns);
      } else if (evt.event === "error") {
        setStatus("error");
        setRunning(false);
      }
    });
    wsRef.current = ws;
  }

  const current = scenarios.find((s) => s.id === selected);

  return (
    <div className="range">
      <header className="masthead">
        <div className="brand">
          <span className="brand-mark">◈</span>
          <div>
            <h1>MCP Attack &amp; Defense Range</h1>
            <p className="eyebrow">Signature scanner · description layer</p>
          </div>
        </div>
        <div className="thesis">
          Defense runs at the infrastructure layer — it flags a poisoned tool
          whether or not the model would have refused.
        </div>
      </header>

      <div className="grid">
        {/* ---- left rail: targets ---- */}
        <aside className="rail">
          <h2 className="rail-title">Targets</h2>
          <ul className="targets">
            {scenarios.map((s) => (
              <li key={s.id}>
                <button
                  className={`target ${selected === s.id ? "is-selected" : ""}`}
                  onClick={() => setSelected(s.id)}
                  disabled={running}
                >
                  <span className="target-name">{s.label}</span>
                  <AttackTag cls={s.attack_class} />
                </button>
              </li>
            ))}
          </ul>

          {current && <p className="target-blurb">{current.blurb}</p>}

          <button className="run" onClick={runScan} disabled={running || !selected}>
            {running ? "Scanning…" : "Run scan"}
          </button>
          <button
            className="ghost"
            onClick={() => resetPins().then(() => getRuns().then(setRuns))}
            disabled={running}
            title="Forget every pinned fingerprint so the next scan re-baselines"
          >
            Reset rug-pull baseline
          </button>
        </aside>

        {/* ---- center: live readout ---- */}
        <main className="readout">
          <div className={`scope ${status}`}>
            <div className="scope-head">
              <span className="scope-label">Readout</span>
              <span className="scope-status">
                {status === "idle" && "awaiting target"}
                {status === "scanning" && "sweeping channels…"}
                {status === "done" && "scan complete"}
                {status === "error" && "server unreachable"}
              </span>
            </div>

            {channels.length === 0 && status === "idle" && (
              <div className="empty">
                Select a target and run a scan to watch each tool resolve to a
                verdict.
              </div>
            )}

            {status === "error" && (
              <div className="empty error">
                Could not reach the range. Is the backend running on :8000?
              </div>
            )}

            <ul className="channels">
              {channels.map((c) => (
                <li key={c.index} className={`channel ${VERDICT_CLASS[c.verdict]}`}>
                  <div className="channel-row">
                    <span className="ch-name">{c.name}</span>
                    <span className="ch-meter">
                      <i className="bar" />
                      <i className="bar" />
                      <i className="bar" />
                    </span>
                    <span className={`ch-verdict ${VERDICT_CLASS[c.verdict]}`}>
                      {c.verdict}
                    </span>
                    {c.pin.startsWith("CHANGED") && (
                      <span className="ch-pin">rug pull</span>
                    )}
                  </div>
                  {c.findings.length > 0 && (
                    <ul className="findings">
                      {c.findings.map((f, i) => (
                        <li key={i} className={`finding sev-${f.severity}`}>
                          <span className="sev">{f.severity}</span> {f.label}
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          </div>

          {verdict && (
            <div className={`banner ${VERDICT_CLASS[verdict.overall]}`}>
              <span className="banner-verdict">{verdict.overall}</span>
              <span className="banner-detail">
                {verdict.flagged} of {verdict.tools.length} tools flagged
                {verdict.rug_pull && " · rug pull detected"}
              </span>
            </div>
          )}

          {/* ---- history ---- */}
          <section className="history">
            <h2 className="rail-title">History</h2>
            {runs.length === 0 && <p className="muted">No scans yet.</p>}
            <ul className="runs">
              {runs.map((r) => (
                <li key={r.id}>
                  <button
                    className="run-row"
                    onClick={() => getRun(r.id).then(setDetail)}
                  >
                    <span className="run-id">#{r.id}</span>
                    <span className="run-scenario">{r.scenario}</span>
                    <span className={`run-verdict ${VERDICT_CLASS[r.overall]}`}>
                      {r.overall}
                    </span>
                    <span className="run-flagged">
                      {r.flagged}/{r.tool_count}
                    </span>
                    {r.rug_pull ? <span className="run-rug">rug</span> : null}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </main>
      </div>

      {/* ---- run detail drawer ---- */}
      {detail && !detail.error && (
        <div className="drawer-scrim" onClick={() => setDetail(null)}>
          <div className="drawer" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-head">
              <div>
                <span className="drawer-id">Run #{detail.id}</span>
                <h3>{detail.scenario}</h3>
                <p className="muted">{detail.started_at}</p>
              </div>
              <button className="ghost close" onClick={() => setDetail(null)}>
                Close
              </button>
            </div>
            <ul className="channels">
              {detail.tools.map((c) => (
                <li key={c.index} className={`channel ${VERDICT_CLASS[c.verdict]}`}>
                  <div className="channel-row">
                    <span className="ch-name">{c.name}</span>
                    <span className={`ch-verdict ${VERDICT_CLASS[c.verdict]}`}>
                      {c.verdict}
                    </span>
                    {c.pin && c.pin.startsWith("CHANGED") && (
                      <span className="ch-pin">rug pull</span>
                    )}
                  </div>
                  {c.findings.length > 0 && (
                    <ul className="findings">
                      {c.findings.map((f, i) => (
                        <li key={i} className={`finding sev-${f.severity}`}>
                          <span className="sev">{f.severity}</span> {f.label}
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
