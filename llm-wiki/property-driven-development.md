# Property-Driven Development

> *"Most verification teams work backwards: someone writes the RTL, then someone else bolts on assertions to catch the bugs they thought of afterwards. What if you flipped the whole flow — wrote the properties first, and let them drive the RTL? That's the bet behind **Property-Driven Development (PDD)**, a top-down methodology crystallized by the Kaiserslautern group and demonstrated on an open RISC-V CPU. You start from an abstract SystemC model, mechanically extract a formal property suite from it, then refine the RTL against those properties until it's provably equivalent to the spec. It's design-by-contract for hardware, and it's one of the few ideas at DVCon that genuinely changes the order in which you draw things on the whiteboard. Let's dig in."*

## The core idea: properties first, RTL second

PDD starts from an abstract, transaction-level SystemC model and produces a fully and formally verified RTL implementation [Property-Driven Development of a RISC-V CPU, 2019]. The model is converted into a **Path Predicate Abstraction (PPA)** — a colored control-flow graph in which "important states" are abstracted and the transitions between them become formal properties. An open-source tool called **DeSCAM** automates the extraction: given a SystemC-PPA-compliant model, it produces a property suite, an RTL skeleton, and the macros and functions that map abstract variables to concrete RTL signals.

The designer then writes RTL under full microarchitectural freedom — pipelining, timing, datapath bit-widths — while the property suite is concurrently refined with cycle-accurate details. At any moment the partial RTL can be checked against the properties, guaranteeing it is a sound refinement of the system-level model. Because both the abstract model and the RTL satisfy the same property suite, what is proven at the system level carries down to the implementation.

Crucially, no higher-order logic or exotic language is required: everything is expressible in standard **SystemVerilog Assertions (SVA)**, and all proofs reduce to SAT-based bounded property checking. The methodology was deliberately formulated so that ordinary design and verification engineers — not formal-methods specialists — can apply it.

## Properties as an executable specification

PDD is the sharpest version of a broader trend: treating assertions as the spec, not as an afterthought. At Xilinx, a single SVA library capturing legal IP configurations was used to validate configurations, kill X-propagation and bus-contention bugs, harden simulation, and tighten the software spec — "four birds with one stone," replacing a manual and error-prone simulation flow [How to Kill 4 Birds with 1 Stone, 2013]. In the automotive space, Bosch formalizes the SoC spec in SysML and generates SystemVerilog Assertions from it, so that the spec and the checkers can never drift apart [Model-based Automation of Verification Development for automotive SOCs, 2020]. Intel extended SVA-like temporal assertions into SystemC itself, automatically converted to SVA during high-level synthesis [Temporal assertions in SystemC, 2020]. Even SPICE-level netlists can now host PSL/SVA assertions, bridging electrical and digital views [PSL/SVA Assertions in SPICE, 2012]. The common thread: write the property once, derive checkers, coverage, and documentation from it.

## Where it shines — and where it still hurts

On the RISC-V R32I case study the payoff is dramatic. SystemC-PPA simulation runs roughly 270–300x faster than RTL, and the property proofs complete in 10–23 minutes for both an industrial and a redesigned SONET/SDH framer [Property-Driven Development of a RISC-V CPU, 2019]. For safety-critical mixed-signal ASICs at CERN, formal property verification with SVA found "a large number of faults" and proved the main functionality despite several counters in the design [Formal Property Verification of the Digital Section of an Ultra-Low Current Digitizer ASIC, 2021]. Deadlocks — among the hardest bugs to hit in simulation because you cannot distinguish "locked up" from "waiting for stimulus" — yield cleanly to formal property proofs [Using Formal to Prevent Deadlocks, 2020].

But the methodology is not free. Counter-heavy and heavily-pipelined designs still stress formal engines; HLS-based multi-pipeline designs with resource sharing need explicit design-for-verification hooks [Using HLS to improve Design-for-Verification of multi-pipeline designs with resource sharing, 2020]. And when a property does fail, root-cause analysis across multi-cycle counterexamples is painful enough that LLM-driven assistants like **FVDebug** are now being built to automate it [FVDebug, 2026].

## See also

- [RISC-V Processor Verification](risc-v-verification.md) — PDD's canonical case study is a RISC-V CPU.
- [Assertion-Based Verification and SVA](assertion-sva.md) — SVA is the property language PDD targets.
- [Formal Property Verification (FPV)](formal-property-verification.md) — PDD's refinement proofs are FPV underneath.

## Grounded in these DVCon papers

- **Property-Driven Development of a RISC-V CPU** (2019, DVCon US) — Tobias Ludwig, Michael Schwarz and Joakim Urdahl. The defining paper: a top-down methodology that starts from SystemC and produces a formally verified RISC-V RTL implementation.
- **How to Kill 4 Birds with 1 Stone: Using Formal Verification to Validate Legal Configurations, Find Design Bugs, and Improve Testbench and Software Specifications** (2013, DVCon US) — Saurabh Shrivastava, Kavita Dangi and Darrow Chu. Uses a single SVA library to drive configuration validation, bug hunting, simulation hardening, and software-spec tightening.
- **PSL/SVA Assertions in SPICE** (2012, DVCon US) — Donald O'Riordan and Prabal Bhattacharya. Extends PSL/SVA assertion semantics down to SPICE-level netlists for mixed-signal designs.
- **FVDebug: An LLM-Driven Debugging Assistant for Automated Root Cause Analysis of Formal Verification Failures** (2026, DVCon US) — Yunsheng Bai, Ghaith Bany Hamad and Chia-Tung Ho. Automates the painful root-cause analysis step when PDD-style properties fail.
- **Formal Property Verification of the Digital Section of an Ultra-Low Current Digitizer ASIC** (2021, DVCon Europe) — Katharina Ceesay-Seitz, Sarath Kundumattathil Mohanan and Hamza Boukabache. Concrete FPV-with-SVA case study on a CERN safety-critical ASIC.
- **Using Formal to Prevent Deadlocks** (2020, DVCon Europe) — Abdelouahab Ayari, Mark Eslinger and Joe Hupcey III. Argues that deadlocks — simulation-resistant by nature — are a prime target for formal property proofs.
- **Model-based Automation of Verification Development for automotive SOCs** (2020, DVCon Europe) — Aljoscha Kirchner, Jan-Hendrik Oetjens and Oliver Bringmann. Generates SVA from a SysML model of the SoC spec.
- **Temporal assertions in SystemC** (2020, DVCon Europe) — Mikhail Moiseev, Leonid Azarenkov and Ilya Klotchkov. Brings SVA-like temporal assertions into SystemC, auto-converted during HLS.
- **Using HLS to improve Design-for-Verification of multi-pipeline designs with resource sharing** (2021, DVCon Europe) — Sarmad Dahir, Nils Luetke-Steinhorst and Christian Sauer. Design-for-verification hooks for resource-shared multi-pipeline IPs.
- **Low Power Static Verification — Beyond Linting and Corruption Semantics** (2011, DVCon US) — Kaustav Guha, Ankush Bagotra and Neha Bajaj. UPF2.0 power-state assertions as a chip-level verification lever.
- **Implementation of a closed loop CDC verification methodology** (2014, DVCon Europe) — Andrew Cunningham and Ireneusz Sobanski. Extends CDC analysis to automatically filter and verify false violations through tapeout.
- **Using Machine Learning in Register Automation and Verification** (2019, DVCon US) — Nikita Gulliya, Abhishek Bora and Nitin Chaudhary. ML-assisted capture of design intent into a specification that drives design and verification code generation.
- **Yikes! Why is My SystemVerilog Still So Slooooow?** (2019, DVCon US) — Cliff Cummings, John Rose and Adam Sherer. Performance characteristics of modern SystemVerilog — relevant context for moving verification up to the system level.
- **Common Challenges and Solutions to Integrating a UVM Testbench in Place of a Legacy Monolithic Testing Environment** (2018, DVCon US) — Frank Verhoorn and Michael Baird. Migration-path realism for teams moving to a UVM-based methodology.
- **Architecting "Checker IP" for AMBA protocols** (2017, DVCon US) — Srinivasan Venkataramanan and Ajeetha Ku. Architecting reusable assertion-based Checker IP for protocol verification.

---

*Part of the [DVCon LLM Wiki](index.md). Synthesized from 1,852 DVCon papers (2010–2026).*
