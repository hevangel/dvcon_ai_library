"""Build per-topic source files for the llm-wiki.

For each of the 50 topics, query data/dvcon.db and write a JSON source file
to llm-wiki/_sources/<slug>.json containing:
  - 8-15 most relevant papers (title, year, authors, abstract excerpt)
  - 5-10 most relevant chunks (heading + body excerpt + paper title)
  - top references cited by those papers
  - cross-link targets (other topics in the wiki)

Also writes llm-wiki/_topics.json -- the canonical topic manifest.

Usage:
    docs/.venv/Scripts/python.exe llm-wiki/build_sources.py
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "dvcon.db"
WIKI_DIR = REPO_ROOT / "llm-wiki"
SOURCES_DIR = WIKI_DIR / "_sources"


# ---------- the 50-topic manifest ----------
# Each entry: slug, title, category, blurb (1-line), keywords (regex alternation
# used for paper matching), see_also (slugs of other topics to cross-link).
TOPICS: list[dict] = [
    # --- Foundations (8) ---
    {"slug": "systemverilog", "title": "SystemVerilog",
     "category": "Foundations",
     "blurb": "The hardware description and verification language (IEEE 1800) that almost every DVCon paper assumes you already know.",
     "keywords": r"systemverilog|system verilog|\bsv\b|\bsvh\b",
     "see_also": ["uvm-overview", "uvm-register-layer", "assertion-sva", "dpi"]},
    {"slug": "uvm-overview", "title": "Universal Verification Methodology (UVM)",
     "category": "Foundations",
     "blurb": "The standard methodology layered on SystemVerilog for building reusable testbenches. The single most-discussed topic at DVCon.",
     "keywords": r"\buvm\b|universal verification methodology",
     "see_also": ["systemverilog", "ovm-vmm", "uvm-testbench-architecture", "uvm-sequences"]},
    {"slug": "upf", "title": "UPF — Power Intent (IEEE 1801)",
     "category": "Foundations",
     "blurb": "The Unified Power Format: how you describe power domains, isolation cells, retention, and level shifters separate from the RTL.",
     "keywords": r"\bupf\b|unified power format|power intent|\bcpf\b|common power format",
     "see_also": ["low-power-verification", "power-aware-verification", "systemverilog"]},
    {"slug": "systemc", "title": "SystemC (IEEE 1666)",
     "category": "Foundations",
     "blurb": "C++-based modeling library used for virtual prototypes, TLM-2.0, and early software bring-up before RTL is ready.",
     "keywords": r"\bsystemc\b|system c\b|\btlm\b|transaction level modeling",
     "see_also": ["emulation-prototyping", "ams-verification", "dpi"]},
    {"slug": "ovm-vmm", "title": "OVM and VMM — the methodologies UVM replaced",
     "category": "Foundations",
     "blurb": "Open Verification Methodology and Verification Methodology Manual. The pre-2011 methodologies whose ideas still echo in UVM today.",
     "keywords": r"\bovm\b|open verification methodology|\bvmm\b|verification methodology manual",
     "see_also": ["uvm-overview", "uvm-sequences", "systemverilog"]},
    {"slug": "design-patterns", "title": "Design Patterns in Verification",
     "category": "Foundations",
     "blurb": "How the Gang of Four patterns (factory, observer, strategy, template method) show up in UVM and modern testbenches.",
     "keywords": r"design pattern|factory|callback|uvm factory|object oriented|\boop\b",
     "see_also": ["uvm-factory", "uvm-callbacks", "uvm-overview"]},
    {"slug": "verification-planning-mdv", "title": "Verification Planning and Metric-Driven Verification",
     "category": "Foundations",
     "blurb": "Planning what to verify before you write a single sequence; closing the loop with coverage as the exit criterion.",
     "keywords": r"verification plan|vplan|metric driven|metric-driven|\bmdb\b|verification management|kpi",
     "see_also": ["coverage-closure", "functional-coverage", "regression-optimization"]},
    {"slug": "dvcon-conference", "title": "The DVCon Conference",
     "category": "Foundations",
     "blurb": "What the Design & Verification Conference is, where it runs, and why this corpus exists.",
     "keywords": r"dvcon|design and verification|verification conference",
     "see_also": ["uvm-overview", "verification-planning-mdv"]},

    # --- UVM deep dives (10) ---
    {"slug": "uvm-testbench-architecture", "title": "UVM Testbench Architecture",
     "category": "UVM deep dives",
     "blurb": "env, agent, driver, monitor, scoreboard — the layered cake that every UVM testbench is built from.",
     "keywords": r"uvm.*testbench|testbench architecture|uvm.*env|\bagent\b|uvm.*environment",
     "see_also": ["uvm-overview", "uvm-sequences", "uvm-scoreboards"]},
    {"slug": "uvm-sequences", "title": "UVM Sequences and Sequence Layering",
     "category": "UVM deep dives",
     "blurb": "How stimulus is generated: sequences, virtual sequences, sequence layering, and the eternal debate on when to layer vs when to nested.",
     "keywords": r"uvm.*sequence|sequence layering|virtual sequence|\bsequencer\b",
     "see_also": ["uvm-testbench-architecture", "uvm-overview", "pss"]},
    {"slug": "uvm-register-layer", "title": "UVM Register Abstraction Layer (RAL)",
     "category": "UVM deep dives",
     "blurb": "The register layer that lets you predict, drive, and check CPU-accessible registers without writing 5,000 lines of boilerplate.",
     "keywords": r"uvm.*register|uvm ral|\bral\b|register abstraction|register layer|register model",
     "see_also": ["uvm-testbench-architecture", "uvm-overview"]},
    {"slug": "uvm-factory", "title": "UVM Factory and Overrides",
     "category": "UVM deep dives",
     "blurb": "The polymorphism engine that lets one test swap a driver, monitor, or sequence without touching the testbench.",
     "keywords": r"uvm.*factory|factory pattern|set_type_override|set_inst_override|type override",
     "see_also": ["design-patterns", "uvm-testbench-architecture"]},
    {"slug": "uvm-phasing-objections", "title": "UVM Phasing and Objections",
     "category": "UVM deep dives",
     "blurb": "The phase machinery that organizes a testbench's life cycle, and the objection mechanism that decides when a test is done.",
     "keywords": r"uvm.*phase|build phase|run phase|objection|raise objection|uvm.*phase.*domain",
     "see_also": ["uvm-testbench-architecture", "uvm-overview"]},
    {"slug": "uvm-callbacks", "title": "UVM Callbacks",
     "category": "UVM deep dives",
     "blurb": "The hook mechanism that predates factory overrides and still shows up in legacy VIPs.",
     "keywords": r"uvm.*callback|callback hook|uvm_callback|callback mechanism",
     "see_also": ["design-patterns", "uvm-factory"]},
    {"slug": "uvm-config-db", "title": "UVM Configuration Database (config_db)",
     "category": "UVM deep dives",
     "blurb": "How testbench configuration propagates from the test down to the deepest driver — and why it sometimes silently fails.",
     "keywords": r"uvm_config_db|config_db|uvm_resource|configuration database|resource database",
     "see_also": ["uvm-testbench-architecture", "uvm-phasing-objections"]},
    {"slug": "uvm-vips", "title": "UVM Verification IP (VIP)",
     "category": "UVM deep dives",
     "blurb": "Reusable protocol agents (AXI, PCIe, Ethernet, USB, …) that you plug into your testbench instead of writing your own.",
     "keywords": r"verification ip|\bvip\b|uvm.*vip|protocol agent|axi vip|pcie vip|ethernet vip",
     "see_also": ["uvm-testbench-architecture", "uvm-sequences", "ip-xact"]},
    {"slug": "uvm-scoreboards", "title": "UVM Scoreboards and Predictors",
     "category": "UVM deep dives",
     "blurb": "The reference model that decides whether the DUT's output is right — and the predictors that feed it.",
     "keywords": r"uvm.*scoreboard|scoreboard|predictor|reference model|\bbfm\b",
     "see_also": ["uvm-testbench-architecture", "uvm-sequences"]},
    {"slug": "uvm-reuse", "title": "UVM Reuse — Vertical and Horizontal",
     "category": "UVM deep dives",
     "blurb": "Reusing a block-level testbench at the subsystem and SoC level (vertical), and across projects (horizontal). The Holy Grail of UVM.",
     "keywords": r"vertical reuse|horizontal reuse|testbench reuse|ip reuse|reuse.*uvm|uvm.*reuse",
     "see_also": ["uvm-testbench-architecture", "uvm-vips", "uvm-config-db"]},

    # --- Formal verification (6) ---
    {"slug": "formal-property-verification", "title": "Formal Property Verification (FPV)",
     "category": "Formal verification",
     "blurb": "Mathematical proof that a design satisfies its properties — no stimulus needed, but plenty of pitfalls.",
     "keywords": r"formal property|formal verif|\bfpv\b|formal proof|formal analysis|jaspergold|vc formal|model checking",
     "see_also": ["assertion-sva", "formal-connectivity", "formal-hybrid"]},
    {"slug": "formal-connectivity", "title": "Formal Connectivity Checking",
     "category": "Formal verification",
     "blurb": "Proving that every pin on your SoC is wired to the right place — a formal app that has replaced miles of directed tests.",
     "keywords": r"connectivity check|connectivity verif|formal.*connect|port connectivity|pin connectivity",
     "see_also": ["formal-property-verification", "soc-ip-integration"]},
    {"slug": "formal-hybrid", "title": "Formal + Simulation Hybrid Verification",
     "category": "Formal verification",
     "blurb": "Where formal proves local properties and simulation checks system behavior. The two methods are complementary, not competing.",
     "keywords": r"formal.*simulation|hybrid formal|formal hybrid|simulation.*formal|co-verification",
     "see_also": ["formal-property-verification", "assertion-sva"]},
    {"slug": "equivalence-checking", "title": "Equivalence Checking (LEC / SEC)",
     "category": "Formal verification",
     "blurb": "Logic Equivalence Checking (RTL vs netlist) and Sequential Equivalence Checking (RTL vs RTL).",
     "keywords": r"equivalence check|\blec\b|sequential equivalence|\bsec\b|logic equivalence",
     "see_also": ["formal-property-verification"]},
    {"slug": "formal-security", "title": "Formal Verification for Security and Trust",
     "category": "Formal verification",
     "blurb": "Using formal methods to hunt for hardware trojans, side channels, and information leaks.",
     "keywords": r"formal.*security|security.*formal|hardware trojan|taint analysis|information flow|trust.*formal",
     "see_also": ["formal-property-verification", "security-trust"]},
    {"slug": "formal-coverage-signoff", "title": "Formal Coverage and Signoff",
     "category": "Formal verification",
     "blurb": "How do you know your formal proof was complete enough to sign off? Coverage metrics for formal, and bounded-proof signoff strategies.",
     "keywords": r"formal coverage|formal signoff|sign-off.*formal|bounded proof|formal sign-off",
     "see_also": ["formal-property-verification", "coverage-closure"]},

    # --- Coverage (5) ---
    {"slug": "functional-coverage", "title": "Functional Coverage and Covergroups",
     "category": "Coverage",
     "blurb": "The SystemVerilog covergroup construct and how to model what you actually want to verify (not just what the code does).",
     "keywords": r"functional coverage|covergroup|cover property|cover cross|coverage model",
     "see_also": ["coverage-closure", "code-coverage", "assertion-sva"]},
    {"slug": "coverage-closure", "title": "Coverage Closure and Convergence",
     "category": "Coverage",
     "blurb": "The last 10% of coverage takes 90% of the effort. Strategies for closing the gap without burning more compute.",
     "keywords": r"coverage closure|coverage convergence|coverage hole|closing coverage|100% coverage",
     "see_also": ["functional-coverage", "ml-coverage", "regression-optimization"]},
    {"slug": "code-coverage", "title": "Code Coverage (Line, Branch, Toggle)",
     "category": "Coverage",
     "blurb": "The structural coverage metrics that tell you what code your tests exercised — necessary but never sufficient.",
     "keywords": r"code coverage|line coverage|branch coverage|toggle coverage|condition coverage|expression coverage",
     "see_also": ["functional-coverage", "coverage-closure"]},
    {"slug": "regression-optimization", "title": "Regression Optimization",
     "category": "Coverage",
     "blurb": "Running 100,000 tests every night, finishing before morning, and not missing the one bug that matters.",
     "keywords": r"regression|regression suite|regression optimi[sz]|sim farm|compute farm|regression.*throughput",
     "see_also": ["coverage-closure", "ml-regression-selection", "emulation-prototyping"]},
    {"slug": "coverage-data-management", "title": "Coverage Data Management and Exchange",
     "category": "Coverage",
     "blurb": "Merging coverage across runs, projects, and tools — and the surprisingly messy data formats that make it possible.",
     "keywords": r"coverage merge|coverage data|coverage exchange|coverage management|coverage database|ucdb",
     "see_also": ["functional-coverage", "regression-optimization"]},

    # --- AI/ML for verification (4) ---
    {"slug": "ml-coverage", "title": "ML for Coverage Closure",
     "category": "AI/ML for verification",
     "blurb": "Using machine learning to pick which seeds, which tests, and which constraints will close coverage fastest.",
     "keywords": r"machine learning.*coverage|coverage.*machine learning|ml.*coverage|coverage.*\bml\b|bayesian.*coverage|reinforcement.*coverage",
     "see_also": ["coverage-closure", "ml-regression-selection"]},
    {"slug": "llm-testbench-generation", "title": "LLMs for Testbench Generation",
     "category": "AI/ML for verification",
     "blurb": "Can a large language model write UVM code that actually compiles? The newest and most hyped topic at DVCon.",
     "keywords": r"large language model|\bllm\b|gpt|chatgpt|testbench generation|generative ai|generative.*verification",
     "see_also": ["uvm-testbench-architecture", "future-of-verification"]},
    {"slug": "ai-formal", "title": "AI for Formal Verification",
     "category": "AI/ML for verification",
     "blurb": "ML assistants that help formal engineers write properties, debug failures, and abduce reachability constraints.",
     "keywords": r"ai.*formal|formal.*ai|ml.*formal|formal.*ml|ai formal engineer|machine learning.*formal",
     "see_also": ["formal-property-verification", "ml-coverage"]},
    {"slug": "ml-regression-selection", "title": "Smart Regression and Test Selection",
     "category": "AI/ML for verification",
     "blurb": "Predicting which tests are likely to find bugs given a code change, so you don't run the whole regression on every commit.",
     "keywords": r"test selection|regression selection|predictive regression|smart regression|test prioritiz",
     "see_also": ["regression-optimization", "ml-coverage"]},

    # --- Domain-specific (10) ---
    {"slug": "cdc-verification", "title": "CDC (Clock Domain Crossing) Verification",
     "category": "Domain-specific",
     "blurb": "Where two clocks meet, metastability waits. The methodologies, tools, and signoff criteria for CDC correctness.",
     "keywords": r"clock domain crossing|\bcdc\b|metastab|synchronizer|async.*clock",
     "see_also": ["rdc-verification", "formal-property-verification", "assertion-sva"]},
    {"slug": "rdc-verification", "title": "RDC (Reset Domain Crossing) Verification",
     "category": "Domain-specific",
     "blurb": "CDC's quieter, nastier cousin: what happens when two reset domains interact without proper synchronization.",
     "keywords": r"reset domain crossing|\brdc\b|reset.*async|reset.*synchron",
     "see_also": ["cdc-verification", "low-power-verification"]},
    {"slug": "low-power-verification", "title": "Low-Power Verification with UPF",
     "category": "Domain-specific",
     "blurb": "Verifying that power domains turn on and off correctly, isolation cells clamp, retention registers save state, and the chip still works.",
     "keywords": r"low power.*verif|low-power.*verif|power verif|power domain.*verif|\bupf\b.*verif",
     "see_also": ["upf", "power-aware-verification", "rdc-verification"]},
    {"slug": "power-aware-verification", "title": "Power-Aware Verification",
     "category": "Domain-specific",
     "blurb": "Verifying functionality in the presence of power management — power-aware testbenches, sequences, and checks.",
     "keywords": r"power aware|power-aware|power.*test.*verif|power state|isolation cell.*verif",
     "see_also": ["low-power-verification", "upf", "uvm-testbench-architecture"]},
    {"slug": "emulation-prototyping", "title": "Emulation and Prototyping",
     "category": "Domain-specific",
     "blurb": "When the design is too big for simulation: FPGA prototyping and emulation bring software and full-system workloads into pre-silicon.",
     "keywords": r"emulation|emulator|prototyping|fpga prototyp|palladium|veloce|protium",
     "see_also": ["systemc", "soc-ip-integration", "regression-optimization"]},
    {"slug": "ams-verification", "title": "AMS (Analog/Mixed-Signal) Verification",
     "category": "Domain-specific",
     "blurb": "How to verify chips that mix digital RTL with analog blocks — Real Number Models, mixed-simulation, and the AMS debugging rabbit hole.",
     "keywords": r"mixed signal|mixed-signal|analog.*verif|\bams\b|real number model|\brnm\b|verilog.?ams|spice.*verif",
     "see_also": ["systemverilog", "systemc", "uvm-scoreboards"]},
    {"slug": "assertion-sva", "title": "Assertion-Based Verification and SVA",
     "category": "Domain-specific",
     "blurb": "SystemVerilog Assertions — the formal-friendly, simulation-friendly way to express 'this property must hold'.",
     "keywords": r"assertion|\bsva\b|systemverilog assertion|immediate assertion|concurrent assertion|cover property|assert property",
     "see_also": ["formal-property-verification", "functional-coverage", "systemverilog"]},
    {"slug": "security-trust", "title": "Security and Trust Verification",
     "category": "Domain-specific",
     "blurb": "Verifying that hardware is secure: side-channel resistance, secure boot, crypto correctness, and ISO 21434.",
     "keywords": r"security verif|secure boot|side channel|hardware trojan|fips|iso 21434|security.*hardware",
     "see_also": ["formal-security", "assertion-sva"]},
    {"slug": "risc-v-verification", "title": "RISC-V Processor Verification",
     "category": "Domain-specific",
     "blurb": "Verifying open instruction sets: compliance, custom extensions, and property-driven development on RISC-V cores.",
     "keywords": r"risc-v|riscv|processor verif|instruction set|isa verif|\bcpu\b.*verif",
     "see_also": ["formal-property-verification", "assertion-sva", "emulation-prototyping"]},
    {"slug": "soc-ip-integration", "title": "SoC and IP Integration Verification",
     "category": "Domain-specific",
     "blurb": "Stitching hundreds of IPs into a working SoC — connectivity, address maps, integration regressions, and the integration engineer's nightmares.",
     "keywords": r"\bsoc\b|system-on-chip|system on chip|ip integration|chiplet|multi-die|\bucie\b|die-to-die",
     "see_also": ["formal-connectivity", "uvm-reuse", "ip-xact"]},

    # --- Modern/emerging (7) ---
    {"slug": "pss", "title": "PSS — Portable Stimulus Standard",
     "category": "Modern and emerging",
     "blurb": "Accellera's attempt to write stimulus once and run it on simulation, emulation, and post-silicon alike.",
     "keywords": r"\bpss\b|portable stimulus|portable test and stimulus",
     "see_also": ["uvm-sequences", "emulation-prototyping"]},
    {"slug": "chiplet-ucie", "title": "Chiplet and Multi-Die (UCIe) Verification",
     "category": "Modern and emerging",
     "blurb": "The new frontier: verifying die-to-die connectivity, multi-die boot, and the UCIe standard that connects them.",
     "keywords": r"chiplet|multi-die|multi die|\bucie\b|die-to-die|multi-chip",
     "see_also": ["soc-ip-integration", "emulation-prototyping", "formal-connectivity"]},
    {"slug": "property-driven-development", "title": "Property-Driven Development",
     "category": "Modern and emerging",
     "blurb": "Writing assertions before RTL — using properties as an executable spec, with RISC-V as the canonical case study.",
     "keywords": r"property driven|property-driven|assertion.*first|spec.*assertion|executable spec",
     "see_also": ["risc-v-verification", "assertion-sva", "formal-property-verification"]},
    {"slug": "dpi", "title": "DPI — Direct Programming Interface",
     "category": "Modern and emerging",
     "blurb": "The bridge between SystemVerilog and C/C++: reusing reference models, SW models, and even ML inference inside a UVM testbench.",
     "keywords": r"\bdpi\b|direct programming interface|dpi-c|dpi-cpp|\bsvdpi\b|systemverilog.*c\+\+",
     "see_also": ["systemverilog", "systemc", "uvm-scoreboards"]},
    {"slug": "ip-xact", "title": "IP-XACT and VIP Integration",
     "category": "Modern and emerging",
     "blurb": "The IEEE 1685 standard for describing IPs and stitching them together — and how it interacts with UVM VIPs.",
     "keywords": r"ip-?xact|ieee 1685|spirit|ip packaging",
     "see_also": ["uvm-vips", "soc-ip-integration"]},
    {"slug": "debug-techniques", "title": "Debug Techniques and Tools",
     "category": "Modern and emerging",
     "blurb": "When the test fails at 2am: trace infrastructures, waveform triage, root-cause analysis, and AI-assisted debugging.",
     "keywords": r"\bdebug\b|debugging|trace.*infra|root cause|waveform|verdi|triage|failure analysis",
     "see_also": ["regression-optimization", "llm-testbench-generation"]},
    {"slug": "future-of-verification", "title": "The Future of Verification",
     "category": "Modern and emerging",
     "blurb": "Where the field is heading: LLM agents, AI co-engineers, self-healing regressions, and what humans will still do.",
     "keywords": r"future.*verif|llm.*agent|ai.*agent|autonomous verif|verif.*2030|next gen.*verif",
     "see_also": ["llm-testbench-generation", "ai-formal", "debug-techniques"]},

    # ====================================================================
    # Batch 2 -- 50 more concepts (brings the wiki to 100 pages).
    # Organized into 6 new sections that complement the original 7.
    # ====================================================================

    # --- UVM mechanics deeper (5) ---
    {"slug": "uvm-tlm-ports", "title": "UVM TLM Ports, Exports, and the Analysis Fabric",
     "category": "UVM mechanics",
     "blurb": "How uvm_analysis_port, exports, imps, and subscribers wire a UVM env together so monitors, scoreboards, and predictors stay decoupled.",
     "keywords": r"uvm_analysis_port|analysis_port|tlm.?port|tlm.?export|uvm_tlm|analysis_fifo|uvm_subscriber|get_next_item|item_done|tlm-?2\.0",
     "see_also": ["uvm-testbench-architecture", "uvm-scoreboards", "systemverilog"]},
    {"slug": "uvm-reporting-logging", "title": "UVM Reporting, Logging, and Verbosity",
     "category": "UVM mechanics",
     "blurb": "uvm_info / uvm_warning / uvm_error / uvm_fatal, report catchers, verbosity filtering, and the logs that actually get read at 2am.",
     "keywords": r"uvm_info|uvm_warning|uvm_error|uvm_fatal|uvm_report|report_catcher|uvm_verbosity|verbosity|\bmessage.*catcher\b|report_object|severity",
     "see_also": ["uvm-phasing-objections", "uvm-component-object-graph", "debug-techniques"]},
    {"slug": "uvm-component-object-graph", "title": "uvm_component vs uvm_object — the Object Graph",
     "category": "UVM mechanics",
     "blurb": "Why components live forever in a hierarchy but objects are transient, and what that means for factory, cloning, and printing.",
     "keywords": r"uvm_component|uvm_object|uvm_transaction|uvm_seq_item|class.*systemverilog|uvm_tree_printer|uvm_table_printer|sprint\(|clone\(\)|create\(|phase.*ready_to_end",
     "see_also": ["uvm-factory", "uvm-phasing-objections", "uvm-sequences"]},
    {"slug": "uvm-recording-transaction", "title": "UVM Transaction Recording and Waveform Annotation",
     "category": "UVM mechanics",
     "blurb": "emit_recording, begin_child / end_tr, transaction databases, and how UVM talks to waveform viewers so engineers can read what just happened.",
     "keywords": r"uvm_recorder|emit_recording|begin_tr|end_tr|begin_child|uvm_transaction_recording|transaction.*recording|recording.*tr|waveform.*annotation|set_transaction_id|tr_database",
     "see_also": ["uvm-component-object-graph", "debug-techniques", "uvm-scoreboards"]},
    {"slug": "uvm-bfm-virtual-interface", "title": "BFMs, Virtual Interfaces, and Clocking Blocks",
     "category": "UVM mechanics",
     "blurb": "The seam between the dynamic UVM world and the static RTL: virtual interfaces, clocking blocks, drive/sample, and the great BFM-vs-Agent debate.",
     "keywords": r"bus.*functional.*model|\bbfm\b|transactor|virtual.*interface|clocking.*block|modport|\bvif\b|uvm_config_db.*vif|drive.*sample|active.*passive.*agent",
     "see_also": ["uvm-vips", "uvm-testbench-architecture", "uvm-config-db"]},

    # --- Methodology and flow (10) ---
    {"slug": "constrained-random-verification", "title": "Constrained-Random Verification (CRV)",
     "category": "Methodology and flow",
     "blurb": "The central bet of modern DV: write constraints once, let the solver explore, hit corners humans would miss. And the closure tax it imposes.",
     "keywords": r"constrained.?random|crv|random.*verif|constraint.*solver|solve.*before|rand.*variable|randomize\(\)|random.*stab|random.*regression",
     "see_also": ["coverage-closure", "constrained-random-tuning", "verification-planning-mdv", "uvm-sequences"]},
    {"slug": "verification-signoff-criteria", "title": "Verification Signoff Criteria and the Tapeout Gate",
     "category": "Methodology and flow",
     "blurb": "What 'we're done' actually means: coverage thresholds, bug slopes, waiver lists, and the signoff matrix that gates the tapeout.",
     "keywords": r"signoff|sign-off|tape.?out|tapeout.*verif|waiver|bug.*rate|bug.*slope|exit.*criteria|signoff.*matrix|signoff.*report",
     "see_also": ["coverage-closure", "regression-optimization", "metric-driven-flow"]},
    {"slug": "coverage-driven-generation", "title": "Coverage-Driven Generation",
     "category": "Methodology and flow",
     "blurb": "Closing coverage by generating more stimulus where it's missing — coverage targets, sequence budgets, intelligent seeds, and the closing loop.",
     "keywords": r"coverage.*driven|coverage.*target|sequence.*budget|coverage.*closure|gen.*from.*cov|coverage.*feedback|goal.*oriented|smart.*seed|coverage.*hole.*fill",
     "see_also": ["coverage-closure", "constrained-random-verification", "ml-coverage", "uvm-sequences"]},
    {"slug": "regression-management", "title": "Regression Management and Infrastructure",
     "category": "Methodology and flow",
     "blurb": "Nightly regressions, distributed farms, seed tracking, snapshot policies, and the dashboards everyone stares at at 9am.",
     "keywords": r"regression.*manag|regression.*infra|nightly.*regression|regression.*suite|distributed.*regression|lsf|verif.*farm|job.*schedul|regression.*dashboard",
     "see_also": ["regression-optimization", "regression-triage", "metric-driven-flow", "ci-cd-rtl-pipeline"]},
    {"slug": "vip-integration-reuse", "title": "VIP Integration and Reuse",
     "category": "Methodology and flow",
     "blurb": "Packaging a verification IP so the next team drops it in, not rewrites it: interfaces, config, layered sequences, and the QVIP/VIP catalog problem.",
     "keywords": r"vip.*reuse|vip.*sharing|vip.*catalog|verification.*ip.*packaging|qvip|vip.*integrat|test.*reuse.*ip|ip.*reuse.*verif|reuse.*horizontal|vip.*config",
     "see_also": ["uvm-vips", "uvm-reuse", "ip-xact", "soc-ip-integration"]},
    {"slug": "shift-left-verification", "title": "Shift-Left Verification",
     "category": "Methodology and flow",
     "blurb": "Move verification earlier: virtual platforms, executable specs, model-driven checks, and the economic case for catching bugs before RTL exists.",
     "keywords": r"shift.*left|shift.*verify|pre.?silicon|early.*verif|model.*driven|virtual.*platform|executable.*spec|pre.?rtl|shift.*verification",
     "see_also": ["systemc-tlm2-virtual-prototypes", "verification-planning-mdv", "property-driven-development"]},
    {"slug": "agile-verification", "title": "Agile Hardware Development and Continuous Verification",
     "category": "Methodology and flow",
     "blurb": "Two-week tapeouts aren't real, but the mindset is: continuous integration for RTL, frequent regressions, and verif embedded in the dev loop.",
     "keywords": r"agile.*hardware|agile.*verif|agile.*silicon|continuous.*verif|dev.*ops.*rtl|iterative.*verif|agile.*eda|agile.*chip",
     "see_also": ["ci-cd-rtl-pipeline", "shift-left-verification", "regression-management"]},
    {"slug": "metric-driven-flow", "title": "Metric-Driven Verification Flow",
     "category": "Methodology and flow",
     "blurb": "MDV end-to-end: plans → features → coverage → results → dashboards. The KPI-driven pipeline that turns 'are we done?' into a number.",
     "keywords": r"metric.driven|metric.*verif|\bmdv\b|kpi.*verif|verif.*dashboard|verif.*flow.*manage|plan.*track.*close|quantitative.*verif|verif.*status.*report",
     "see_also": ["verification-planning-mdv", "coverage-closure", "verification-signoff-criteria", "regression-management"]},
    {"slug": "regression-triage", "title": "Regression Triage and Root-Cause Automation",
     "category": "Methodology and flow",
     "blurb": "When the nightly run drops 200 failures: triage queues, fingerprinting, dedup, and AI-assisted root-cause clustering at batch scale.",
     "keywords": r"triage|root.*cause.*auto|failure.*cluster|failure.*fingerprint|signature.*fail|dedup.*fail|bug.*signature|fail.*bucket|regression.*triage",
     "see_also": ["debug-techniques", "regression-management", "ml-regression-selection"]},
    {"slug": "tapeout-case-studies", "title": "Tapeout Case Studies — What Actually Worked",
     "category": "Methodology and flow",
     "blurb": "Real chips, real teams, real flows. What the industry learned shipping silicon under deadline: the good, the buggy, and the almost-too-late.",
     "keywords": r"tape.*out.*case|silicon.*case|chip.*tapeout|tapeout.*story|production.*chip|silicon.*success|silicon.*bug|lessons.*learned.*silicon|chip.*bring.*up",
     "see_also": ["verification-signoff-criteria", "debug-techniques", "future-of-verification"]},

    # --- Standards, languages, and protocols (10) ---
    {"slug": "axi-amba-protocols", "title": "AXI, AHB, and APB — ARM AMBA Protocol Verification",
     "category": "Standards and protocols",
     "blurb": "The buses that stitch most SoCs together: AXI4, ACE, AHB-Lite, APB. How to verify the protocol, the interconnect, and the corner cases.",
     "keywords": r"\baxi\b|amba|\bahb\b|\bapb\b|axi.*lite|axi.*stream|ace.*coherency|axi.*outstanding|\bace\b.*cache|amba.*protocol",
     "see_also": ["uvm-vips", "noc-interconnect-verification", "cache-coherency-verification"]},
    {"slug": "pcie-verification", "title": "PCIe Verification (and CXL)",
     "category": "Standards and protocols",
     "blurb": "PCI Express Gen5/Gen6, the CXL cache-coherent overlay, TLP/PLL/DLL layers, and the verification IP that has to be right.",
     "keywords": r"\bpcie\b|pci express|\bcxl\b|compute express link|tlp|data link layer|transaction layer|gen5|gen6|\.0.*pcie",
     "see_also": ["uvm-vips", "cache-coherency-verification", "serdes-cdr-high-speed-io"]},
    {"slug": "usb-verification", "title": "USB Verification (1.1 through USB4)",
     "category": "Standards and protocols",
     "blurb": "From full-speed to USB4 over Thunderbolt: packet layer, link training, protocol analyzers, and the legacy-compatibility tax.",
     "keywords": r"\busb\b|universal serial|usb.*3|usb.*4|usb4|thunderbolt|usb.*type.?c|usb.*phy|link.*training.*usb|superSpeed.*usb",
     "see_also": ["uvm-vips", "serdes-cdr-high-speed-io", "pcie-verification"]},
    {"slug": "ethernet-networking-mac", "title": "Ethernet and Networking MAC Verification",
     "category": "Standards and protocols",
     "blurb": "10G/100G/400G Ethernet MAC, PCS/PMA, time-sensitive networking, and the verification that keeps packets honest.",
     "keywords": r"\bethernet\b|\bmac\b.*ethernet|gige|gigabit.*ethernet|\bpcs\b.*pma|mii.*gmii|xgmii|tsn|time.*sensitive.*net|preamble.*crc",
     "see_also": ["uvm-vips", "axi-amba-protocols", "serdes-cdr-high-speed-io"]},
    {"slug": "ddr-memory-verification", "title": "DDR and LPDDR Memory Interface Verification",
     "category": "Standards and protocols",
     "blurb": "DDR5/LPDDR5 PHY, controller, training, refresh, and the long tail of JEDEC corner cases that bite at cold corner.",
     "keywords": r"\bddr\b|dram|\blpddr\b|ddr5|lpddr5|\bjedec\b|memory.*controller|memory.*phy|ddr.*training|refresh.*memory|read.*write.*timing",
     "see_also": ["uvm-vips", "ams-verification", "soc-ip-integration"]},
    {"slug": "serial-low-pin-protocols", "title": "Serial Low-Pin-Count Protocols — I2C, SPI, UART, CAN-FD",
     "category": "Standards and protocols",
     "blurb": "Tiny protocols, huge aggregate risk: every SoC has a dozen, and the corner cases (clock stretching, multi-master, bit stuffing) all matter.",
     "keywords": r"\bi2c\b|\bspi\b|\buart\b|\bcan\b.*fd|can.*flex.*data|low.pin.*count|two.*wire|i2c.*multi.*master|spi.*slave|uart.*verif",
     "see_also": ["uvm-vips", "axi-amba-protocols", "soc-ip-integration"]},
    {"slug": "cache-coherency-verification", "title": "Cache Coherency Verification",
     "category": "Standards and protocols",
     "blurb": "MESI/MOESI, snoop vs directory, ACE/CHI coherency fabrics — the protocol-level verification that keeps multi-core systems from silently corrupting.",
     "keywords": r"cache coh|coherency|coherence|\bsnoop\b|\bmesi\b|\bmoesi\b|\bchi\b.*cache|ace.*coherency|directory.*coh|coherency.*fabric",
     "see_also": ["axi-amba-protocols", "risc-v-verification", "formal-property-verification"]},
    {"slug": "noc-interconnect-verification", "title": "Network-on-Chip (NoC) and Interconnect Verification",
     "category": "Standards and protocols",
     "blurb": "NoCs, meshes, rings, and the routers/links/VCs that move terabytes per second between dozens of masters and slaves.",
     "keywords": r"\bnoc\b|network.on.chip|mesh.*interconnect|\bring.*bus\b|\brouter\b.*packet|virtual.*channel|wormhole|interconnect.*topology|packet.*switched|quality.of.service",
     "see_also": ["axi-amba-protocols", "soc-ip-integration", "cache-coherency-verification"]},
    {"slug": "interrupt-controller-verification", "title": "Interrupt Controller Verification (GIC, PLIC, IOAPIC)",
     "category": "Standards and protocols",
     "blurb": "ARM GIC, RISC-V PLIC/ACLINT, x86 APIC — priority, affinity, virtualization, and the latency-sensitive corner cases.",
     "keywords": r"\bgic\b|generic.*interrupt.*controller|\bplic\b|aclINT|ioapIC|lapic|interrupt.*controller|irq.*verif|interrupt.*priority|msi.*msi-x|affinity.*irq",
     "see_also": ["risc-v-verification", "soc-ip-integration", "axi-amba-protocols"]},
    {"slug": "memory-map-register-blocks", "title": "Memory Maps and Register Block Verification",
     "category": "Standards and protocols",
     "blurb": "Address decode, register blocks, CSR access patterns, SystemRDL/IP-XACT, and the UVM RAL seam that ties it together.",
     "keywords": r"memory.*map|address.*map|address.*decode|register.*block|csr.*verif|systemrdl|ip-?xact.*register|register.*abstract|ral.*model.*generat",
     "see_also": ["uvm-register-layer", "ip-xact", "soc-ip-integration"]},

    # --- Power, clock, and analog (6) ---
    {"slug": "clock-generation-pll-dll", "title": "Clock Generation — PLL, DLL, and CDR Verification",
     "category": "Power, clock, and analog",
     "blurb": "Phase- and delay-locked loops, clock-data recovery, jitter/phase noise, and how to verify an analog block that has to lock in ps.",
     "keywords": r"\bpll\b|\bdll\b|\bcdr\b|clock.*data.*recov|mmcm|phase.*lock|delay.*lock|jitter|phase.*noise|loop.*filter|vco|charge.*pump|lock.*detect",
     "see_also": ["ams-verification", "real-number-modeling", "cdc-verification"]},
    {"slug": "power-isolation-retention", "title": "Power Isolation, Retention, and Level Shifters",
     "category": "Power, clock, and analog",
     "blurb": "The cells that let you power-gate and still wake up sane: isolation cells, retention registers, level shifters, and always-on domains.",
     "keywords": r"isolation cell|level shifter|retention.*reg|retention.*cell|always.on.*domain|power.*gate.*verif|power.*switch.*cell|iso.*clamp|retain.*state",
     "see_also": ["upf", "low-power-verification", "power-aware-verification"]},
    {"slug": "dvfs-verification", "title": "DVFS — Dynamic Voltage and Frequency Scaling Verification",
     "category": "Power, clock, and analog",
     "blurb": "Operating Performance Points, voltage scaling on the fly, and the verification that the chip throttles, boosts, and survives transitions.",
     "keywords": r"\bdvfs\b|dynamic.voltage.frequency|operating.*performance.*point|\bopp\b|voltage.*scaling|frequency.*scaling|adaptive.*voltage|throttle.*boost|power.*state.*trans",
     "see_also": ["power-aware-verification", "low-power-verification", "upf"]},
    {"slug": "power-estimation-rtl", "title": "RTL Power Estimation and Analysis",
     "category": "Power, clock, and analog",
     "blurb": "Switching activity, leakage models, SAIF/VCD/FSDB, and the toolchain that estimates a chip's wall-plug number before silicon exists.",
     "keywords": r"power.*estimat|rtl.*power|switch.*power|leakage.*power|saif|activity.*factor|\bvcd\b.*power|fsdb.*power|toggle.*rate|dynamic.*power.*analy",
     "see_also": ["low-power-verification", "power-aware-verification", "upf"]},
    {"slug": "real-number-modeling", "title": "Real Number Modeling (RNM) for AMS",
     "category": "Power, clock, and analog",
     "blurb": "wreal and SystemVerilog real-number models: a fast functional stand-in for analog blocks so digital testbenches don't have to wait for SPICE.",
     "keywords": r"real.*number.*model|\brnm\b|wreal|real.*valued.*model|\brnms\b|electrical.*model.*sv|real.*pin.*sv|ams.*digital.*sim|ams.*fast.*funct",
     "see_also": ["ams-verification", "verilog-ams-real", "systemverilog"]},
    {"slug": "verilog-ams-real", "title": "Verilog-AMS for Mixed-Signal Verification",
     "category": "Power, clock, and analog",
     "blurb": "The analog/mixed-signal HDL: discipline, electrical vs wreal, connect modules, and where Verilog-AMS still wins over RNM.",
     "keywords": r"verilog.?ams|verilog ams|ams.*verif|mixed.signal.*verif|connect.*module|electrical.*discipline|discipline.*nature|analog.*block.*sim|analog.*verif",
     "see_also": ["ams-verification", "real-number-modeling", "assertion-sva"]},

    # --- Functional safety, security, and edges (6) ---
    {"slug": "iso-26262-automotive-safety", "title": "ISO 26262 — Automotive Functional Safety",
     "category": "Functional safety and security",
     "blurb": "ASIL A-D, HARA, safety goals, FMEDA, and the verification chain that has to prove 'no single point of failure harms the driver'.",
     "keywords": r"iso.*26262|\basil\b|\bhara\b|safety goal|safety mechanism|fmElda|ftfi|single.point.fault|spfm|lfm|safety.*analysis|automotive.*safety",
     "see_also": ["fault-injection-seu", "do-254-avionics", "verification-signoff-criteria"]},
    {"slug": "do-254-avionics", "title": "DO-254 — Airborne Electronic Hardware",
     "category": "Functional safety and security",
     "blurb": "The avionics counterpart to ISO 26262: DAL A-E, requirements traceability, and the verification artifacts the FAA expects to see.",
     "keywords": r"do.*254|\bdal\b.*a|dal.*b|airborne.*hardware|avionics.*safety|rtca.*do.*254|faa.*certif|requirements.*traceability.*certif",
     "see_also": ["iso-26262-automotive-safety", "verification-signoff-criteria", "fault-injection-seu"]},
    {"slug": "fault-injection-seu", "title": "Fault Injection and Single-Event Upset Verification",
     "category": "Functional safety and security",
     "blurb": "Injecting stuck-at, transient, and SEU faults at RTL/emulation to validate that safety mechanisms detect them inside the FTTI window.",
     "keywords": r"fault.*inject|injection.*campaign|single.event.*upset|\bseu\b|set.*single.*event|safety.*mechanism.*detect|ftti|fault.*campaign|stuck.*at.*fault|transient.*fault",
     "see_also": ["iso-26262-automotive-safety", "emulation-prototyping", "do-254-avionics"]},
    {"slug": "side-channel-physical-security", "title": "Side-Channel and Physical Security Verification",
     "category": "Functional safety and security",
     "blurb": "DPA/CPA, EM and timing leakage, tamper detection, and the verification of countermeasures that has to assume the attacker is smart.",
     "keywords": r"side.channel|dpa|cpa|electromagnetic.*leak|timing.*leak|tamper|physical.*security|countermeasure.*verif|correlation.*power.*analy|masking.*countermeasure",
     "see_also": ["security-trust", "formal-security", "fault-injection-seu"]},
    {"slug": "x-propagation-4-state", "title": "X-Propagation and 4-State Verification",
     "category": "Functional safety and security",
     "blurb": "Why SystemVerilog has X, when 2-state fast仿真 hides bugs, and how to verify that unknowns are caught not propagated to the output.",
     "keywords": r"x.prop|unknown.*prop|optimism.*verif|pessimism.*verif|two state|2 state|\bx.?state\b|isunknown|\b\$isunknown\b|\b\$onehot\b|x.*trap",
     "see_also": ["systemverilog", "assertion-sva", "formal-property-verification"]},

    # --- Tools, languages, and ecosystem (8) ---
    {"slug": "cocotb-python-verification", "title": "Cocotb — Python-Driven Verification",
     "category": "Tools and ecosystem",
     "blurb": "Coroutines-on-the-simulator: writing testbenches in Python, the appeal (no SystemVerilog), the tradeoffs (no UVM, slower), and where it shines.",
     "keywords": r"cocotb|python.*verif|python.*testbench|python.*hdl|python.*simul",
     "see_also": ["dpi", "systemverilog", "uvm-c-reference-model"]},
    {"slug": "osvvm-vhdl", "title": "OSVVM — Open Source VHDL Verification Methodology",
     "category": "Tools and ecosystem",
     "blurb": "The VHDL world's answer to UVM: OSVVM util packages, coverage models, and verification methodology that still ships in many FPGA flows.",
     "keywords": r"osvvm|verification.*vhdl|vhdl.*methodology|vhdl.*coverage|fpga.*verif.*vhdl|coverage.*vhdl|axi.*lite.*vhdl",
     "see_also": ["uvm-overview", "systemverilog", "functional-coverage"]},
    {"slug": "systemc-tlm2-virtual-prototypes", "title": "SystemC TLM-2.0 and Virtual Prototypes",
     "category": "Tools and ecosystem",
     "blurb": "Transaction-level modeling for software-bringup-before-RTL: loosely timed vs approximately timed, AT-style, and the speed-vs-accuracy tradeoff.",
     "keywords": r"tlm-?2\.0|tlm.*loosely.*timed|tlm.*approximately.*timed|tlm.*payload|virtual.*platform.*tlm|tlm.*socket|loosely.timed|approximately.timed|generic.*payload",
     "see_also": ["systemc", "shift-left-verification", "sw-driven-verification"]},
    {"slug": "uvm-c-reference-model", "title": "C/C++ Reference Models in UVM (via DPI)",
     "category": "Tools and ecosystem",
     "blurb": "The golden C model pattern: reuse the architect's reference, call it through DPI, and let the scoreboard compare — and the performance tax it costs.",
     "keywords": r"reference.*model.*c\+\+|c.*reference.*model|\bdpi.*reference\b|golden.*model.*c|sw.*model.*verif|c\+\+.*golden|dpi-c.*model|reference.*design.*dpi",
     "see_also": ["dpi", "uvm-scoreboards", "systemc"]},
    {"slug": "cloud-distributed-verification", "title": "Cloud and Distributed Verification Farms",
     "category": "Tools and ecosystem",
     "blurb": "Spinning up thousands of EDA licenses and simulator cores in the cloud: burst capacity, security, license economics, and the SaaS-verif pitch.",
     "keywords": r"cloud.*verif|saas.*verif|distrib.*verif|verif.*farm.*cloud|cloud.*compute.*rtl|elastic.*regression|burstable.*verif|cloud.*eda|cloud.*farm",
     "see_also": ["regression-management", "ci-cd-rtl-pipeline", "emulation-prototyping"]},
    {"slug": "ci-cd-rtl-pipeline", "title": "CI/CD for RTL — Pipelines for Hardware",
     "category": "Tools and ecosystem",
     "blurb": "Jenkins/GitLab/GitHub-Actions running lint, build, sim regressions on every commit: the same DevOps playbook, retuned for hardware.",
     "keywords": r"continuous integration|\bjenkins\b|gitlab.*ci|github.*action.*rtl|\bci.*cd\b|rtl.*pipeline|pre.commit.*rtl|auto.*regression.*commit",
     "see_also": ["regression-management", "agile-verification", "cloud-distributed-verification"]},
    {"slug": "constrained-random-tuning", "title": "Constrained-Random Tuning — Solver Hints and Performance",
     "category": "Tools and ecosystem",
     "blurb": "When randomize() takes 10 minutes: solve...before, rand_mode, constraint_mode, soft constraints, and the solver tuning that rescues a slow testbench.",
     "keywords": r"solve.*before|rand_mode|constraint_mode|soft.*constraint|solver.*hint|randomize.*performance|constraint.*solver.*perf|rand.*state|pre.*randomize|post.*randomize",
     "see_also": ["constrained-random-verification", "coverage-driven-generation", "systemverilog"]},
    {"slug": "random-stability-seeds", "title": "Random Stability, Seeds, and Reproducibility",
     "category": "Tools and ecosystem",
     "blurb": "Why a test passes on Tuesday and fails on Wednesday: RNG version drift, thread-order nondeterminism, and the quest for bit-exact replay.",
     "keywords": r"random.*stab|reproduce.*random|seed.*verif|rng.*stability|prng.*determ|\brand.*state\b|reproducibility.*verif|nondeterm.*verif|thread.*order.*sim",
     "see_also": ["constrained-random-verification", "regression-triage", "constrained-random-tuning"]},

    # --- SoC integration depth (5) ---
    {"slug": "sw-driven-verification", "title": "Software-Driven Verification and Firmware Bring-Up",
     "category": "SoC and system depth",
     "blurb": "When the real test is a booting OS: C test programs, U-Boot/Linux bring-up in sim and emulation, and the SW/HW co-verification pivot.",
     "keywords": r"software.driven.*verif|sw.*verif|firmware.*verif|embedded.*test|\bc test\b.*verif|host.*test.*program|boot.*linux.*emul|uefi.*verif|bootrom.*verif",
     "see_also": ["emulation-prototyping", "systemc-tlm2-virtual-prototypes", "shift-left-verification"]},
    {"slug": "glitch-metastability-verification", "title": "Glitch and Metastability Verification",
     "category": "SoC and system depth",
     "blurb": "CDC metastability wrap-up, async reset deassertion, glitch-free clock switching, and the verification of the boundaries where digital fails.",
     "keywords": r"glitch.*verif|metastab|async.*reset.*deassert|clock.*switch.*glitch|reset.*synchronizer|glitch.free.*clock|noise.*margin|synchronizer.*chain|\bmtbf\b.*meta",
     "see_also": ["cdc-verification", "rdc-verification", "clock-generation-pll-dll"]},
    {"slug": "pre-silicon-to-post-silicon", "title": "Pre-Silicon to Post-Silicon Handoff",
     "category": "SoC and system depth",
     "blurb": "Test plans, coverage continuity, bug-escape analysis, and the artifacts that bridge the pre-sil sim world to the post-sil lab.",
     "keywords": r"pre.silicon.*post.silicon|pre.?sil.*post.?sil|silicon.*handoff|escape.*analysis|post.silicon.*plan|chip.*bring.*up.*handoff|silicon.*debug.*handoff",
     "see_also": ["regression-management", "tapeout-case-studies", "debug-techniques"]},
    {"slug": "post-silicon-validation", "title": "Post-Silicon Validation in the Lab",
     "category": "SoC and system depth",
     "blurb": "Bring-up boards, ATE testers, scan debug, the corner cases that only show up on real silicon, and the slowness of one chip per cycle.",
     "keywords": r"post.silicon.*valid|\blab.*valid\b|\bate\b.*tester|silicon.*bring.*up|scan.*debug.*silicon|silicon.*bug.*root.*cause|first.*silicon|tester.*program|production.*test",
     "see_also": ["pre-silicon-to-post-silicon", "tapeout-case-studies", "debug-techniques"]},
    {"slug": "chip-to-board-system-verification", "title": "Chip-to-Board System Verification",
     "category": "SoC and system depth",
     "blurb": "The chip works, the board works, the system doesn't: signal integrity, power delivery, thermal, and the verification that crosses the PCB seam.",
     "keywords": r"chip.*to.*board|board.*level.*verif|system.*level.*verif|si.pi.*verif|signal.*integrity.*power.*integrity|thermal.*verif|pcb.*verif|system.*integration.*board",
     "see_also": ["soc-ip-integration", "pre-silicon-to-post-silicon", "ams-verification"]},
    {"slug": "serdes-cdr-high-speed-io", "title": "SerDes, CDR, and High-Speed I/O Verification",
     "category": "SoC and system depth",
     "blurb": "Multi-gigabit serial links, equalization (CTLE/DFE/FFE), clock-data recovery, link training, and the mixed-signal verif that has to lock at 112G.",
     "keywords": r"serdes|serializer|deserializer|\bcdr\b|clock.*data.*recov|ctle|dfe|ffe|equaliz|link.*training|pam4|nrz|112g|56g.*pam4|eye.*diagram|high.speed.*io",
     "see_also": ["pcie-verification", "ethernet-networking-mac", "usb-verification"]},
]


# ---------- DB helpers ----------

def _norm_authors(text: str) -> str:
    """Collapse a comma-separated authors_text blob into 'A, B and C'."""
    parts = [p.strip() for p in re.split(r"[;,]", text or "") if p.strip()]
    # drop emails and junk
    parts = [re.sub(r"\s+", " ", p)[:40] for p in parts if "@" not in p and len(p) > 2]
    parts = parts[:3]
    if not parts:
        return "Anonymous"
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def score_paper(text: str, patterns: list[re.Pattern]) -> int:
    """Higher = more relevant."""
    return sum(len(p.findall(text)) for p in patterns)


def main() -> None:
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # load all papers once
    print("Loading papers ...")
    papers = cur.execute("""
        SELECT id, year, location, title, abstract, authors_text, affiliations_text
        FROM paper
        WHERE abstract IS NOT NULL AND abstract != ''
    """).fetchall()
    print(f"  {len(papers)} papers with abstracts")

    # load all chunks once, group by paper
    print("Loading chunks ...")
    chunks_by_paper: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in cur.execute("SELECT paper_id, heading, text FROM chunk"):
        if row["paper_id"] is not None:
            chunks_by_paper[row["paper_id"]].append(row)
    print(f"  {sum(len(v) for v in chunks_by_paper.values())} chunks across {len(chunks_by_paper)} papers")

    # load references once
    print("Loading references ...")
    refs_by_paper: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in cur.execute("SELECT paper_id, citation_text, normalized_title FROM referenceentry"):
        if row["paper_id"] is not None:
            refs_by_paper[row["paper_id"]].append(row)
    print(f"  {sum(len(v) for v in refs_by_paper.values())} references across {len(refs_by_paper)} papers")

    # write the canonical topic manifest (without the giant keyword blob)
    print("Writing _topics.json ...")
    manifest = [
        {
            "slug": t["slug"],
            "title": t["title"],
            "category": t["category"],
            "blurb": t["blurb"],
            "see_also": t["see_also"],
        }
        for t in TOPICS
    ]
    (WIKI_DIR / "_topics.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    # per-topic source extraction
    print("Extracting per-topic sources ...")
    n_ok = 0
    n_warn = 0
    for topic in TOPICS:
        slug = topic["slug"]
        patterns = [re.compile(alt.strip(), re.IGNORECASE)
                    for alt in re.split(r"\|", topic["keywords"]) if alt.strip()]

        # score every paper; pick top 15
        scored = []
        for p in papers:
            text = (p["title"] or "") + " " + (p["abstract"] or "")
            s = score_paper(text, patterns)
            if s > 0:
                scored.append((s, p))
        scored.sort(key=lambda x: -x[0])
        top_papers = [p for _, p in scored[:15]]

        # collect the most relevant chunks from those top papers
        # (score each chunk against the patterns too, take top 10)
        candidate_chunks = []
        for p in top_papers[:8]:
            for ch in chunks_by_paper.get(p["id"], []):
                chunk_text = (ch["heading"] or "") + " " + (ch["text"] or "")
                s = score_paper(chunk_text, patterns)
                if s > 0:
                    candidate_chunks.append((s, p, ch))
        candidate_chunks.sort(key=lambda x: -x[0])
        top_chunks = candidate_chunks[:10]

        # references from those top papers, deduped by normalized title
        ref_counter: Counter = Counter()
        ref_lookup: dict[str, sqlite3.Row] = {}
        for p in top_papers:
            for r in refs_by_paper.get(p["id"], []):
                key = (r["normalized_title"] or r["citation_text"][:80]).strip().lower()
                if not key or "references" in key and len(key) < 20:
                    continue
                ref_counter[key] += 1
                ref_lookup[key] = r
        top_refs = [(key, n) for key, n in ref_counter.most_common(8)]

        source = {
            "slug": slug,
            "title": topic["title"],
            "category": topic["category"],
            "blurb": topic["blurb"],
            "see_also": topic["see_also"],
            "papers": [
                {
                    "id": p["id"],
                    "year": p["year"],
                    "location": p["location"],
                    "title": p["title"],
                    "authors": _norm_authors(p["authors_text"]),
                    "affiliations": (p["affiliations_text"] or "")[:200].replace("\n", " ").strip(),
                    "abstract": (p["abstract"] or "")[:700].replace("\n", " ").strip(),
                    "score": score_paper((p["title"] or "") + " " + (p["abstract"] or ""), patterns),
                }
                for p in top_papers
            ],
            "chunks": [
                {
                    "paper_id": p["id"],
                    "paper_title": p["title"],
                    "paper_year": p["year"],
                    "heading": ch["heading"] or "(untitled)",
                    "text": (ch["text"] or "")[:900].strip(),
                    "score": s,
                }
                for s, p, ch in top_chunks
            ],
            "references": [
                {
                    "citation": (ref_lookup[key]["citation_text"] or "")[:200].replace("\n", " ").strip(),
                    "count": n,
                }
                for key, n in top_refs
            ],
            "stats": {
                "n_papers_matched": len(scored),
                "n_papers_used": len(top_papers),
                "n_chunks_used": len(top_chunks),
            },
        }
        out = SOURCES_DIR / f"{slug}.json"
        out.write_text(json.dumps(source, indent=2, ensure_ascii=False), encoding="utf-8")

        flag = "ok"
        if len(top_papers) < 8:
            flag = "WARN-few-papers"
            n_warn += 1
        elif len(top_chunks) < 5:
            flag = "WARN-few-chunks"
            n_warn += 1
        else:
            n_ok += 1
        print(f"  [{flag:18s}] {slug:36s} papers={len(top_papers):3d}  "
              f"chunks={len(top_chunks):3d}  refs={len(top_refs):3d}  "
              f"matched={len(scored):4d}")

    conn.close()
    print(f"\nDone. {n_ok} topics OK, {n_warn} with warnings, {len(TOPICS)} total.")


if __name__ == "__main__":
    main()
