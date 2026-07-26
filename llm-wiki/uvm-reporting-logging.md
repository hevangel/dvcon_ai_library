# UVM Reporting, Logging, and Verbosity

> *"It is 2am, a regression just went red, and you are staring at a 40-gigabyte log file trying to find the one line that explains why test 4,317 hung. We have all been there. UVM gives you four severity macros — `uvm_info`, `uvm_warning`, `uvm_error`, `uvm_fatal` — and a verbosity ladder from `UVM_NONE` to `UVM_FULL`, and the naive promise is that you just crank verbosity up when you debug and back down when you ship. The reality, as Sam Mellor and the ARM team behind Enhanced Verbosity Methodology will tell you, is that verbosity is a blunt instrument: turn it up to track one transaction through a BFM and you drown in output for every transaction; leave it down and the 2am log is useless. So a small subculture of DVCon papers has spent the last decade teaching UVM how to filter messages intelligently, categorize them by purpose, and read them back with machine learning. Let's look at what the reporting machinery actually does — and why everyone keeps reinventing it."*

## What it is

Every UVM component inherits from `uvm_report_object` and gains the four reporting macros plus a configurable **report server** that decides what gets printed, where, and with what action (`UVM_DISPLAY`, `UVM_LOG`, `UVM_COUNT`, `UVM_EXIT`, `UVM_CALL_HOOK`). Each message carries an **ID string**, a **severity**, and a **verbosity level**; the report server compares the effective verbosity (set per-component, per-ID, or globally via `set_verbosity`) against the message's requested level and drops anything below the threshold [User Programmable Targeted UVM Debug Verbosity Escalation, 2025]. On top of this, **`uvm_report_catcher`** is a callback class whose `catch()` method sees every message before it is emitted and can demote, promote, or suppress it — exposing severity, verbosity, id, message text, filename, and line number for fine-grained filtering [Qualification of a Verification IP under Requirement Based Verification standards An approach to the verification of the verification, 2018].

The architecture looks clean on paper, but it has a structural performance problem: message filtering happens *after* the message is constructed. By the time the report server decides to drop a `uvm_info` call, the `$sformatf` that built its string has already run, and on a large vertically integrated testbench those string substitutions and I/O calls are what dominate simulation time [Enhanced Verbosity Methodology, 2026]. This is why `uvm_report_enabled()` exists as a pre-check — you call it before building the string — but most engineers forget, and the macro itself does not enforce it.

## How it's used in practice

The most common pain point is **verbosity escalation for a single interesting transaction**. You want to see every BFM beat for one address, but turning verbosity to `UVM_FULL` emits that detail for *every* address. Mellor's solution wraps each debug call in a tiny pre-check that hashes the address and computes the effective verbosity per-call, so only matching transactions get `UVM_NONE`-level detail and the rest stay quiet [User Programmable Targeted UVM Debug Verbosity Escalation, 2025]:

```
    uvm_verbosity verbosity;
    verbosity = is_debugging_address(address_) ? UVM_NONE : UVM_FULL;
    `uvm_info("MEM_MODEL", $sformatf("Writing to address 0x%0h", address_), verbosity)
```

The catch, Mellor notes, is that this "does not scale very well for escalating verbosity for different transactions" once you want to filter across monitor, driver, scoreboard, and sequence simultaneously.

Vékony and Mózer attack the same problem at ARM with **Enhanced Verbosity Methodology (EVM)**. EVM separates messages into purpose-driven categories — build, header, detail, item — stores verbosity settings in a runtime-parsed **JSON descriptor** addressed by group, class type, instance name, or full hierarchical name, and pushes the verbosity decision *before* string construction so quiet messages cost nothing. It rolls out without breaking existing hierarchies by injecting an opaque EVM layer into class inheritance chains, and each component reads its category values through helper macros like `EVM_BUILD` [Enhanced Verbosity Methodology, 2026]. Beyond raw verbosity, report catchers do double duty as qualification machinery: Cerisier et al. extend `uvm_report_catcher` so a VIP under DO-254 or ISO 26262 can prove it *caught* expected errors and failed a `MIN COUNT NOT REACHED` check when an expected error never arrived [Qualification of a Verification IP under Requirement Based Verification standards An approach to the verification of the verification, 2018]. And verbosity discipline extends past text: Chan et al. mirror the same ladder onto waveform probing — `NONE` probes nothing, `LOW` probes ports, `MEDIUM` probes internals, `HIGH` probes memories, `FULL` probes delta cycles — driven by a tcl wrapper around the simulator's probe command [Can You Even Debug a 200M+ Gate Design?, 2013].

## Pitfalls and where the field is heading

The recurring pitfall is that **the log is the artifact, and it is unstructured**. Chinni et al. put it bluntly: simulation logs capture tool messages, signal activities, assertion results, testbench warnings, and errors in a single unstructured stream, and "the structure, semantics, and verbosity of the simulation log files frequently differ when the same test is run across several labels of a design," making manual comparison error-prone [A novel ML-Driven Simulation Log Debugger, 2026]. Their response is an ML-driven log debugger that learns the semantics of a project's log format and clusters failures across runs — pointing at where human-readable reporting stops and machine-readable reporting should begin.

The second pitfall is **verbosity coupling across vertical levels**. What counts as `UVM_LOW` at block level may be noise at SoC level, and "it is hard to differentiate between what is useful and what seems useless" once hundreds of components are shouting at once [Enhanced Verbosity Methodology, 2026]. EVM's answer is category-based decoupling so a setting at one integration level does not silently flood another. Mellor's targeted escalation tackles the symmetric problem: a debug need at one transaction should not require global verbosity. Looking forward, the field is clearly moving toward two converging ideas — runtime-reconfigurable, descriptor-driven verbosity (EVM's JSON, Mellor's address hashing) so settings can change without recompiling, and ML-assisted log triage so the 2am engineer stops grepping and starts querying. The reporting macros themselves will not change; the intelligence around them will.

## See also

- [UVM Phasing and Objections](uvm-phasing-objections.md) — objections and the report server together decide when a test ends and why.
- [uvm_component vs uvm_object — the Object Graph](uvm-component-object-graph.md) — the component hierarchy that reporting and verbosity are scoped to.
- [Debug Techniques and Tools](debug-techniques.md) — waveform triage and root-cause analysis that consume these logs.
- [Regression Triage and Root-Cause Automation](regression-triage.md) — where ML-driven log clustering lives in the modern flow.
- [UVM Configuration Database (config_db)](uvm-config-db.md) — the parallel mechanism for propagating settings, including verbosity.

## Grounded in these DVCon papers

- **Enhanced Verbosity Methodology** (2026, DVCon US) — Gergő Vékony and József Mózer. EVM: JSON-driven, category-based, runtime-reconfigurable verbosity that filters before string construction.
- **User Programmable Targeted UVM Debug Verbosity Escalation** (2025, DVCon US) — Sam Mellor. Per-transaction verbosity escalation using address hashing so only interesting traffic gets full detail.
- **A novel ML-Driven Simulation Log Debugger** (2026, DVCon US) — Narasimha Rao Chinni, Sunil Shrirangrao Kashide and Garima Srivastava. ML clustering of unstructured simulation logs across design labels.
- **Qualification of a Verification IP under Requirement Based Verification standards An approach to the verification of the verification** (2018, DVCon Europe) — Francois Cerisier, Adrien Carmagnat and Alessandro Basili. Uses `uvm_report_catcher` to qualify VIPs under DO-254 / ISO 26262.
- **Can You Even Debug a 200M+ Gate Design?** (2013, DVCon US) — Horace Chan, Brian Vandegriend and Deepali Joshi. Mirrors the verbosity ladder onto waveform probing for a 200M-gate design.
- **VHDL 2018: New and Noteworthy** (2018, DVCon US) — L. Lemiengre and H. Eeckhaut. Notes interface bundling that reduces instantiation verbosity, the structural cousin of message verbosity.
- **UPF Power Models: Empowering the power intent specification** (2018, DVCon Europe) — Amit Srivastava and Harsh Chilwal. Power-intent code explosion that drives up log volume and debug cost.
- **Automated Safety Verification for Automotive Microcontrollers** (2016, DVCon US) — H. Busch. ISO 26262 flows where reporting artifacts are part of the safety case.
- **How rich descriptions enable early detection of hookup issues** (2022, DVCon Europe) — Peter Birch and Thomas Brown. Concise intent descriptions (Soumak) that shrink and clarify the assembly-time report stream.

---

*Part of the [DVCon LLM Wiki](index.md). 50+1 concepts synthesized from 1,852 DVCon papers (2010-2026).*
