# DVCon LLM Wiki

> *A synthesized wiki of EDA / functional-verification knowledge, built from the 1,852-paper DVCon corpus (2010–2026). Every page opens with a Karpathy-style hook, drops into neutral reference prose, and cites 8–15 real DVCon papers so every claim is traceable to the source.*

**100 of 100 pages written** · ~157,105 words total · 1284 paper citations across the wiki.

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

### UVM mechanics (5 pages)

- **[UVM TLM Ports, Exports, and the Analysis Fabric](uvm-tlm-ports.md)** — How uvm_analysis_port, exports, imps, and subscribers wire a UVM env together so monitors, scoreboards, and predictors stay decoupled.
- **[UVM Reporting, Logging, and Verbosity](uvm-reporting-logging.md)** — uvm_info / uvm_warning / uvm_error / uvm_fatal, report catchers, verbosity filtering, and the logs that actually get read at 2am.
- **[uvm_component vs uvm_object — the Object Graph](uvm-component-object-graph.md)** — Why components live forever in a hierarchy but objects are transient, and what that means for factory, cloning, and printing.
- **[UVM Transaction Recording and Waveform Annotation](uvm-recording-transaction.md)** — emit_recording, begin_child / end_tr, transaction databases, and how UVM talks to waveform viewers so engineers can read what just happened.
- **[BFMs, Virtual Interfaces, and Clocking Blocks](uvm-bfm-virtual-interface.md)** — The seam between the dynamic UVM world and the static RTL: virtual interfaces, clocking blocks, drive/sample, and the great BFM-vs-Agent debate.

### Methodology and flow (10 pages)

- **[Constrained-Random Verification (CRV)](constrained-random-verification.md)** — The central bet of modern DV: write constraints once, let the solver explore, hit corners humans would miss. And the closure tax it imposes.
- **[Verification Signoff Criteria and the Tapeout Gate](verification-signoff-criteria.md)** — What 'we're done' actually means: coverage thresholds, bug slopes, waiver lists, and the signoff matrix that gates the tapeout.
- **[Coverage-Driven Generation](coverage-driven-generation.md)** — Closing coverage by generating more stimulus where it's missing — coverage targets, sequence budgets, intelligent seeds, and the closing loop.
- **[Regression Management and Infrastructure](regression-management.md)** — Nightly regressions, distributed farms, seed tracking, snapshot policies, and the dashboards everyone stares at at 9am.
- **[VIP Integration and Reuse](vip-integration-reuse.md)** — Packaging a verification IP so the next team drops it in, not rewrites it: interfaces, config, layered sequences, and the QVIP/VIP catalog problem.
- **[Shift-Left Verification](shift-left-verification.md)** — Move verification earlier: virtual platforms, executable specs, model-driven checks, and the economic case for catching bugs before RTL exists.
- **[Agile Hardware Development and Continuous Verification](agile-verification.md)** — Two-week tapeouts aren't real, but the mindset is: continuous integration for RTL, frequent regressions, and verif embedded in the dev loop.
- **[Metric-Driven Verification Flow](metric-driven-flow.md)** — MDV end-to-end: plans → features → coverage → results → dashboards. The KPI-driven pipeline that turns 'are we done?' into a number.
- **[Regression Triage and Root-Cause Automation](regression-triage.md)** — When the nightly run drops 200 failures: triage queues, fingerprinting, dedup, and AI-assisted root-cause clustering at batch scale.
- **[Tapeout Case Studies — What Actually Worked](tapeout-case-studies.md)** — Real chips, real teams, real flows. What the industry learned shipping silicon under deadline: the good, the buggy, and the almost-too-late.

### Standards and protocols (10 pages)

- **[AXI, AHB, and APB — ARM AMBA Protocol Verification](axi-amba-protocols.md)** — The buses that stitch most SoCs together: AXI4, ACE, AHB-Lite, APB. How to verify the protocol, the interconnect, and the corner cases.
- **[PCIe Verification (and CXL)](pcie-verification.md)** — PCI Express Gen5/Gen6, the CXL cache-coherent overlay, TLP/PLL/DLL layers, and the verification IP that has to be right.
- **[USB Verification (1.1 through USB4)](usb-verification.md)** — From full-speed to USB4 over Thunderbolt: packet layer, link training, protocol analyzers, and the legacy-compatibility tax.
- **[Ethernet and Networking MAC Verification](ethernet-networking-mac.md)** — 10G/100G/400G Ethernet MAC, PCS/PMA, time-sensitive networking, and the verification that keeps packets honest.
- **[DDR and LPDDR Memory Interface Verification](ddr-memory-verification.md)** — DDR5/LPDDR5 PHY, controller, training, refresh, and the long tail of JEDEC corner cases that bite at cold corner.
- **[Serial Low-Pin-Count Protocols — I2C, SPI, UART, CAN-FD](serial-low-pin-protocols.md)** — Tiny protocols, huge aggregate risk: every SoC has a dozen, and the corner cases (clock stretching, multi-master, bit stuffing) all matter.
- **[Cache Coherency Verification](cache-coherency-verification.md)** — MESI/MOESI, snoop vs directory, ACE/CHI coherency fabrics — the protocol-level verification that keeps multi-core systems from silently corrupting.
- **[Network-on-Chip (NoC) and Interconnect Verification](noc-interconnect-verification.md)** — NoCs, meshes, rings, and the routers/links/VCs that move terabytes per second between dozens of masters and slaves.
- **[Interrupt Controller Verification (GIC, PLIC, IOAPIC)](interrupt-controller-verification.md)** — ARM GIC, RISC-V PLIC/ACLINT, x86 APIC — priority, affinity, virtualization, and the latency-sensitive corner cases.
- **[Memory Maps and Register Block Verification](memory-map-register-blocks.md)** — Address decode, register blocks, CSR access patterns, SystemRDL/IP-XACT, and the UVM RAL seam that ties it together.

### Power, clock, and analog (6 pages)

- **[Clock Generation — PLL, DLL, and CDR Verification](clock-generation-pll-dll.md)** — Phase- and delay-locked loops, clock-data recovery, jitter/phase noise, and how to verify an analog block that has to lock in ps.
- **[Power Isolation, Retention, and Level Shifters](power-isolation-retention.md)** — The cells that let you power-gate and still wake up sane: isolation cells, retention registers, level shifters, and always-on domains.
- **[DVFS — Dynamic Voltage and Frequency Scaling Verification](dvfs-verification.md)** — Operating Performance Points, voltage scaling on the fly, and the verification that the chip throttles, boosts, and survives transitions.
- **[RTL Power Estimation and Analysis](power-estimation-rtl.md)** — Switching activity, leakage models, SAIF/VCD/FSDB, and the toolchain that estimates a chip's wall-plug number before silicon exists.
- **[Real Number Modeling (RNM) for AMS](real-number-modeling.md)** — wreal and SystemVerilog real-number models: a fast functional stand-in for analog blocks so digital testbenches don't have to wait for SPICE.
- **[Verilog-AMS for Mixed-Signal Verification](verilog-ams-real.md)** — The analog/mixed-signal HDL: discipline, electrical vs wreal, connect modules, and where Verilog-AMS still wins over RNM.

### Functional safety and security (5 pages)

- **[ISO 26262 — Automotive Functional Safety](iso-26262-automotive-safety.md)** — ASIL A-D, HARA, safety goals, FMEDA, and the verification chain that has to prove 'no single point of failure harms the driver'.
- **[DO-254 — Airborne Electronic Hardware](do-254-avionics.md)** — The avionics counterpart to ISO 26262: DAL A-E, requirements traceability, and the verification artifacts the FAA expects to see.
- **[Fault Injection and Single-Event Upset Verification](fault-injection-seu.md)** — Injecting stuck-at, transient, and SEU faults at RTL/emulation to validate that safety mechanisms detect them inside the FTTI window.
- **[Side-Channel and Physical Security Verification](side-channel-physical-security.md)** — DPA/CPA, EM and timing leakage, tamper detection, and the verification of countermeasures that has to assume the attacker is smart.
- **[X-Propagation and 4-State Verification](x-propagation-4-state.md)** — Why SystemVerilog has X, when 2-state fast仿真 hides bugs, and how to verify that unknowns are caught not propagated to the output.

### Tools and ecosystem (8 pages)

- **[Cocotb — Python-Driven Verification](cocotb-python-verification.md)** — Coroutines-on-the-simulator: writing testbenches in Python, the appeal (no SystemVerilog), the tradeoffs (no UVM, slower), and where it shines.
- **[OSVVM — Open Source VHDL Verification Methodology](osvvm-vhdl.md)** — The VHDL world's answer to UVM: OSVVM util packages, coverage models, and verification methodology that still ships in many FPGA flows.
- **[SystemC TLM-2.0 and Virtual Prototypes](systemc-tlm2-virtual-prototypes.md)** — Transaction-level modeling for software-bringup-before-RTL: loosely timed vs approximately timed, AT-style, and the speed-vs-accuracy tradeoff.
- **[C/C++ Reference Models in UVM (via DPI)](uvm-c-reference-model.md)** — The golden C model pattern: reuse the architect's reference, call it through DPI, and let the scoreboard compare — and the performance tax it costs.
- **[Cloud and Distributed Verification Farms](cloud-distributed-verification.md)** — Spinning up thousands of EDA licenses and simulator cores in the cloud: burst capacity, security, license economics, and the SaaS-verif pitch.
- **[CI/CD for RTL — Pipelines for Hardware](ci-cd-rtl-pipeline.md)** — Jenkins/GitLab/GitHub-Actions running lint, build, sim regressions on every commit: the same DevOps playbook, retuned for hardware.
- **[Constrained-Random Tuning — Solver Hints and Performance](constrained-random-tuning.md)** — When randomize() takes 10 minutes: solve...before, rand_mode, constraint_mode, soft constraints, and the solver tuning that rescues a slow testbench.
- **[Random Stability, Seeds, and Reproducibility](random-stability-seeds.md)** — Why a test passes on Tuesday and fails on Wednesday: RNG version drift, thread-order nondeterminism, and the quest for bit-exact replay.

### SoC and system depth (6 pages)

- **[Software-Driven Verification and Firmware Bring-Up](sw-driven-verification.md)** — When the real test is a booting OS: C test programs, U-Boot/Linux bring-up in sim and emulation, and the SW/HW co-verification pivot.
- **[Glitch and Metastability Verification](glitch-metastability-verification.md)** — CDC metastability wrap-up, async reset deassertion, glitch-free clock switching, and the verification of the boundaries where digital fails.
- **[Pre-Silicon to Post-Silicon Handoff](pre-silicon-to-post-silicon.md)** — Test plans, coverage continuity, bug-escape analysis, and the artifacts that bridge the pre-sil sim world to the post-sil lab.
- **[Post-Silicon Validation in the Lab](post-silicon-validation.md)** — Bring-up boards, ATE testers, scan debug, the corner cases that only show up on real silicon, and the slowness of one chip per cycle.
- **[Chip-to-Board System Verification](chip-to-board-system-verification.md)** — The chip works, the board works, the system doesn't: signal integrity, power delivery, thermal, and the verification that crosses the PCB seam.
- **[SerDes, CDR, and High-Speed I/O Verification](serdes-cdr-high-speed-io.md)** — Multi-gigabit serial links, equalization (CTLE/DFE/FFE), clock-data recovery, link training, and the mixed-signal verif that has to lock at 112G.

---

## How this wiki was built

1. **Source extraction** (`build_sources.py`): for each topic, the script queries `data/dvcon.db` and picks the 8–15 most relevant DVCon papers + 5–10 most relevant chunks + 8 most-cited references. Result: one JSON file per topic under `_sources/`.
2. **Page synthesis**: an LLM agent (GLM-5.2) reads each source JSON and writes a markdown page in two voices — a Karpathy-style motivational hook, then neutral reference prose with inline citations.
3. **Cross-linking**: every page links to 3–6 related pages via the `see_also` slugs in `_topics.json`. The index you're reading is generated from that same manifest.

See [`README.md`](README.md) for regeneration instructions.

---

## Methodology notes

- **No external sources.** Every claim is grounded in a real DVCon paper. If a page mentions IEEE 1800 or UPF, it's because DVCon papers cite those standards — not because the wiki authors looked them up independently.
- **Citation format.** Inline citations look like `[Paper Title, 2018]` and the full reference appears in the page's "Grounded in these DVCon papers" section.
- **Voice.** The hook is first-person and motivational (Karpathy-style). The body is neutral and reference-like. The two voices are deliberately different — the hook pulls you in, the body teaches you.
- **Coverage.** The 100 topics span the full DVCon domain: foundations (SystemVerilog, UVM, UPF, SystemC), UVM deep dives and mechanics, formal verification, coverage, AI/ML for verification, methodology and flow, standards and protocols (AXI, PCIe, USB, Ethernet, DDR, NoC, cache coherency, register blocks), power/clock/analog, functional safety (ISO 26262, DO-254), tools and ecosystem (cocotb, OSVVM, SystemC TLM-2.0, cloud), and SoC/system depth (SW-driven, post-silicon, chip-to-board).
- **Gaps.** Some topics have thinner source material than others (e.g. UVM callbacks had only 6 papers in the corpus). Those pages are necessarily shorter and rely more heavily on the smaller set of sources.

*Last regenerated: 100 pages, ~157,105 words, 1284 citations. Run `docs/.venv/Scripts/python.exe llm-wiki/build_index.py` to refresh this index.*