# DVCon LLM Wiki

> *A synthesized wiki of EDA / functional-verification knowledge, built from the 1,852-paper DVCon corpus (2010–2026). Every page opens with a Karpathy-style hook, drops into neutral reference prose, and cites 8–15 real DVCon papers so every claim is traceable to the source.*

**50 of 50 pages written** · ~74,490 words total · 673 paper citations across the wiki.

---

## Table of contents

### Foundations (8 pages)

- **[SystemVerilog](systemverilog.md)** — The hardware description and verification language (IEEE 1800) that almost every DVCon paper assumes you already know.
- **[Universal Verification Methodology (UVM)](uvm-overview.md)** — The standard methodology layered on SystemVerilog for building reusable testbenches. The single most-discussed topic at DVCon.
- **[UPF — Power Intent (IEEE 1801)](upf.md)** — The Unified Power Format: how you describe power domains, isolation cells, retention, and level shifters separate from the RTL.
- **[SystemC (IEEE 1666)](systemc.md)** — C++-based modeling library used for virtual prototypes, TLM-2.0, and early software bring-up before RTL is ready.
- **[OVM and VMM — the methodologies UVM replaced](ovm-vmm.md)** — Open Verification Methodology and Verification Methodology Manual. The pre-2011 methodologies whose ideas still echo in UVM today.
- **[Design Patterns in Verification](design-patterns.md)** — How the Gang of Four patterns (factory, observer, strategy, template method) show up in UVM and modern testbenches.
- **[Verification Planning and Metric-Driven Verification](verification-planning-mdv.md)** — Planning what to verify before you write a single sequence; closing the loop with coverage as the exit criterion.
- **[The DVCon Conference](dvcon-conference.md)** — What the Design & Verification Conference is, where it runs, and why this corpus exists.

### UVM deep dives (10 pages)

- **[UVM Testbench Architecture](uvm-testbench-architecture.md)** — env, agent, driver, monitor, scoreboard — the layered cake that every UVM testbench is built from.
- **[UVM Sequences and Sequence Layering](uvm-sequences.md)** — How stimulus is generated: sequences, virtual sequences, sequence layering, and the eternal debate on when to layer vs when to nested.
- **[UVM Register Abstraction Layer (RAL)](uvm-register-layer.md)** — The register layer that lets you predict, drive, and check CPU-accessible registers without writing 5,000 lines of boilerplate.
- **[UVM Factory and Overrides](uvm-factory.md)** — The polymorphism engine that lets one test swap a driver, monitor, or sequence without touching the testbench.
- **[UVM Phasing and Objections](uvm-phasing-objections.md)** — The phase machinery that organizes a testbench's life cycle, and the objection mechanism that decides when a test is done.
- **[UVM Callbacks](uvm-callbacks.md)** — The hook mechanism that predates factory overrides and still shows up in legacy VIPs.
- **[UVM Configuration Database (config_db)](uvm-config-db.md)** — How testbench configuration propagates from the test down to the deepest driver — and why it sometimes silently fails.
- **[UVM Verification IP (VIP)](uvm-vips.md)** — Reusable protocol agents (AXI, PCIe, Ethernet, USB, …) that you plug into your testbench instead of writing your own.
- **[UVM Scoreboards and Predictors](uvm-scoreboards.md)** — The reference model that decides whether the DUT's output is right — and the predictors that feed it.
- **[UVM Reuse — Vertical and Horizontal](uvm-reuse.md)** — Reusing a block-level testbench at the subsystem and SoC level (vertical), and across projects (horizontal). The Holy Grail of UVM.

### Formal verification (6 pages)

- **[Formal Property Verification (FPV)](formal-property-verification.md)** — Mathematical proof that a design satisfies its properties — no stimulus needed, but plenty of pitfalls.
- **[Formal Connectivity Checking](formal-connectivity.md)** — Proving that every pin on your SoC is wired to the right place — a formal app that has replaced miles of directed tests.
- **[Formal + Simulation Hybrid Verification](formal-hybrid.md)** — Where formal proves local properties and simulation checks system behavior. The two methods are complementary, not competing.
- **[Equivalence Checking (LEC / SEC)](equivalence-checking.md)** — Logic Equivalence Checking (RTL vs netlist) and Sequential Equivalence Checking (RTL vs RTL).
- **[Formal Verification for Security and Trust](formal-security.md)** — Using formal methods to hunt for hardware trojans, side channels, and information leaks.
- **[Formal Coverage and Signoff](formal-coverage-signoff.md)** — How do you know your formal proof was complete enough to sign off? Coverage metrics for formal, and bounded-proof signoff strategies.

### Coverage (5 pages)

- **[Functional Coverage and Covergroups](functional-coverage.md)** — The SystemVerilog covergroup construct and how to model what you actually want to verify (not just what the code does).
- **[Coverage Closure and Convergence](coverage-closure.md)** — The last 10% of coverage takes 90% of the effort. Strategies for closing the gap without burning more compute.
- **[Code Coverage (Line, Branch, Toggle)](code-coverage.md)** — The structural coverage metrics that tell you what code your tests exercised — necessary but never sufficient.
- **[Regression Optimization](regression-optimization.md)** — Running 100,000 tests every night, finishing before morning, and not missing the one bug that matters.
- **[Coverage Data Management and Exchange](coverage-data-management.md)** — Merging coverage across runs, projects, and tools — and the surprisingly messy data formats that make it possible.

### AI/ML for verification (4 pages)

- **[ML for Coverage Closure](ml-coverage.md)** — Using machine learning to pick which seeds, which tests, and which constraints will close coverage fastest.
- **[LLMs for Testbench Generation](llm-testbench-generation.md)** — Can a large language model write UVM code that actually compiles? The newest and most hyped topic at DVCon.
- **[AI for Formal Verification](ai-formal.md)** — ML assistants that help formal engineers write properties, debug failures, and abduce reachability constraints.
- **[Smart Regression and Test Selection](ml-regression-selection.md)** — Predicting which tests are likely to find bugs given a code change, so you don't run the whole regression on every commit.

### Domain-specific (10 pages)

- **[CDC (Clock Domain Crossing) Verification](cdc-verification.md)** — Where two clocks meet, metastability waits. The methodologies, tools, and signoff criteria for CDC correctness.
- **[RDC (Reset Domain Crossing) Verification](rdc-verification.md)** — CDC's quieter, nastier cousin: what happens when two reset domains interact without proper synchronization.
- **[Low-Power Verification with UPF](low-power-verification.md)** — Verifying that power domains turn on and off correctly, isolation cells clamp, retention registers save state, and the chip still works.
- **[Power-Aware Verification](power-aware-verification.md)** — Verifying functionality in the presence of power management — power-aware testbenches, sequences, and checks.
- **[Emulation and Prototyping](emulation-prototyping.md)** — When the design is too big for simulation: FPGA prototyping and emulation bring software and full-system workloads into pre-silicon.
- **[AMS (Analog/Mixed-Signal) Verification](ams-verification.md)** — How to verify chips that mix digital RTL with analog blocks — Real Number Models, mixed-simulation, and the AMS debugging rabbit hole.
- **[Assertion-Based Verification and SVA](assertion-sva.md)** — SystemVerilog Assertions — the formal-friendly, simulation-friendly way to express 'this property must hold'.
- **[Security and Trust Verification](security-trust.md)** — Verifying that hardware is secure: side-channel resistance, secure boot, crypto correctness, and ISO 21434.
- **[RISC-V Processor Verification](risc-v-verification.md)** — Verifying open instruction sets: compliance, custom extensions, and property-driven development on RISC-V cores.
- **[SoC and IP Integration Verification](soc-ip-integration.md)** — Stitching hundreds of IPs into a working SoC — connectivity, address maps, integration regressions, and the integration engineer's nightmares.

### Modern and emerging (7 pages)

- **[PSS — Portable Stimulus Standard](pss.md)** — Accellera's attempt to write stimulus once and run it on simulation, emulation, and post-silicon alike.
- **[Chiplet and Multi-Die (UCIe) Verification](chiplet-ucie.md)** — The new frontier: verifying die-to-die connectivity, multi-die boot, and the UCIe standard that connects them.
- **[Property-Driven Development](property-driven-development.md)** — Writing assertions before RTL — using properties as an executable spec, with RISC-V as the canonical case study.
- **[DPI — Direct Programming Interface](dpi.md)** — The bridge between SystemVerilog and C/C++: reusing reference models, SW models, and even ML inference inside a UVM testbench.
- **[IP-XACT and VIP Integration](ip-xact.md)** — The IEEE 1685 standard for describing IPs and stitching them together — and how it interacts with UVM VIPs.
- **[Debug Techniques and Tools](debug-techniques.md)** — When the test fails at 2am: trace infrastructures, waveform triage, root-cause analysis, and AI-assisted debugging.
- **[The Future of Verification](future-of-verification.md)** — Where the field is heading: LLM agents, AI co-engineers, self-healing regressions, and what humans will still do.

---

## How this wiki was built

1. **Source extraction** (`build_sources.py`): for each of the 50 topics, the script queries `data/dvcon.db` and picks the 8–15 most relevant DVCon papers + 5–10 most relevant chunks + 8 most-cited references. Result: one JSON file per topic under `_sources/`.
2. **Page synthesis**: an LLM agent (GLM-5.2) reads each source JSON and writes a markdown page in two voices — a Karpathy-style motivational hook, then neutral reference prose with inline citations.
3. **Cross-linking**: every page links to 3–6 related pages via the `see_also` slugs in `_topics.json`. The index you're reading is generated from that same manifest.

See [`README.md`](README.md) for regeneration instructions.

---

## Methodology notes

- **No external sources.** Every claim is grounded in a real DVCon paper. If a page mentions IEEE 1800 or UPF, it's because DVCon papers cite those standards — not because the wiki authors looked them up independently.
- **Citation format.** Inline citations look like `[Paper Title, 2018]` and the full reference appears in the page's "Grounded in these DVCon papers" section.
- **Voice.** The hook is first-person and motivational (Karpathy-style). The body is neutral and reference-like. The two voices are deliberately different — the hook pulls you in, the body teaches you.
- **Coverage.** The 50 topics span the full DVCon domain: foundations (SystemVerilog, UVM, UPF, SystemC), UVM deep dives, formal verification, coverage, AI/ML for verification, domain-specific topics (CDC, RDC, low-power, AMS, RISC-V, security), and emerging themes (PSS, chiplets, LLMs for verification, the future of the field).
- **Gaps.** Some topics have thinner source material than others (e.g. UVM callbacks had only 6 papers in the corpus). Those pages are necessarily shorter and rely more heavily on the smaller set of sources.

*Last regenerated: 50 pages, ~74,490 words, 673 citations. Run `docs/.venv/Scripts/python.exe llm-wiki/build_index.py` to refresh this index.*