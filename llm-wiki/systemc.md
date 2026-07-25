# SystemC (IEEE 1666)

> *Before the RTL even exists, the software team wants to start writing drivers. Before the bus protocol is finalized, the architect wants to know if the cache will be the bottleneck. Both questions need a model that runs fast and is "good enough" — not cycle-accurate, just *behaviorally* accurate. That model is what SystemC is for. It is a C++ library that lets you build virtual prototypes of a whole SoC and boot real firmware on them months before tapeout, all by raising the level of abstraction above RTL. The Transaction Level Modeling (TLM-2.0) standard layered on top gave the ecosystem just enough interoperability that IP from different vendors could be plugged together. The catch: TLM-2.0 only really nailed *memory-mapped busses*, leaving every other kind of interface — interrupts, streaming, serial — to be reinvented per project. So how do you build a coherent ESL flow on a foundation that is famously "good enough for busses"? Let's dig in.*

## What it is

**SystemC** (IEEE 1666) is a set of C++ classes and a simulation kernel for modeling concurrent hardware systems at abstractions ranging from RTL up to untimed transaction-level models. Its main industry vehicle is **TLM-2.0**, a library of classes — generic payload, sockets, blocking and non-blocking transport interfaces — that standardized how memory-mapped bus models exchange transactions [TLM-2.0 in SystemVerilog, 2011]. The result is the **virtual platform**: a fast, executable SoC model on which software teams bring up drivers and operating systems long before silicon returns.

Barnasconi's overview maps the wider eco-system that surrounds the kernel: SystemC for modeling, TLM for transaction-level communication, **UVM-SystemC** for layered verification, and **CCI** (Configuration, Control and Inspection) for instrumenting models so they can be configured at creation time and run time, not just compile time [Building a coherent ESL design and verification eco-system, 2016]. The ambition is a single coherent stack; the reality is that each standard grew somewhat independently and the seams between them still show.

## How it's used in practice

The dominant use case is the virtual platform for early software development, and the second is test-equipment development. Barrau et al. show SystemC-TLM being used to build virtual prototypes not only of the product under design but also of the test equipment that will eventually exercise it, so test sequences can be prepared before real hardware exists [Acceleration of product and test environment development, 2018]. On the verification side, Singh and Verma extend functional-coverage methodology into SystemC and VHDL environments to measure completion when exhaustive enumeration is impossible [Plugging the Holes, 2011], and Oliveira et al.'s SVM library layered domain-specific components — drivers, monitors, scoreboards — on the OVM-SystemC base for advanced TLM verification [A SystemC Library for Advanced TLM Verification, 2012].

A persistent theme is connecting SystemC to SystemVerilog UVM. Long and Aynsley compare the popular open-source bridges — UVM Connect and UVM-ML — for inserting untimed or loosely-timed SystemC models into a UVM environment, and explore what approximately-timed models additionally require [UVM and SystemC Transactions, 2016]. Dahir et al. show UVM-ML enabling reuse of TLM-2.0 reference models inside UVM testbenches [Using UVM-ML library, 2018]. The transaction classes look similar on both sides but differ in philosophy: in TLM-2.0 the byte-array payload is a pointer to extension data, while in UVM it lives in dynamic arrays inside the transaction object — a small difference that complicates bridging.

Configuration crosses the language boundary too. Bhattacharya et al. extend CCI parameters from SystemC out to the SystemVerilog/SystemC boundary, defining the syntax and semantics of passing parameters from a SystemVerilog parent to a SystemC child [Parameter Passing from SystemVerilog to SystemC, 2015]. And UVM-SystemC itself, described by Barnasconi et al. and by Akhila M, brings the layered UVM testbench architecture to native C++ so SystemC models can be verified in their own idiom rather than wrapped into SystemVerilog [Advancing system-level verification using UVM in SystemC, 2014] [UVM Made Language Agnostic, 2017].

## Pitfalls and where the field is heading

The single most-cited pitfall is that **TLM-2.0 only really works for memory-mapped busses**. Delbergue et al. and Vanthournout and Burton both document that interrupt signals, serial protocols, and Ethernet-like streams don't fit the generic payload cleanly, forcing teams into custom interfaces or fallback to `sc_signal` semantics that are incompatible with TLM — prompting the TLM Working Group to extend the standard for general model-to-model communication [Analysis of TLM-2.0, 2016] [TLM Beyond Memory Mapped Busses, 2016]. Synchronization is the other gap: SystemC lacks features for synchronizing TLM communication across simulators, host processes, or threads, and for synchronizing time across quantum domains — addressed by proposed new SystemC features for inter-kernel synchronization [The missing SystemC and TLM asynchronous features, 2016].

The frontier is co-simulation with other engineering domains. Albu et al. wrap SystemC TLM components as FMI 3.0 Co-Simulation Functional Mock-up Units, with an open-source tool that requires no modification of the SystemC source — letting cyber-physical and automotive models from mechanical, electrical, and control domains run alongside hardware models [Integrating SystemC TLM into FMI 3.0, 2025]. Fault-injection tooling like SCFIT, which drives the GNU debugger from Python to inject faults into compiled SystemC models, is maturing the safety-case story [Runtime Fault-Injection Tool, 2014]. Memory-debugging tools built on TLM-2.0's `transport_dbg` show that the standard, when it does fit, enables reusable debug infrastructure across any virtual prototype [Memory Debugging of Virtual Prototypes, 2012]. The trajectory is clear: SystemC-TLM is becoming one node in a larger multi-domain co-simulation graph rather than a standalone hardware-only island.

## See also

- [Emulation and Prototyping](emulation-prototyping.md) — the other pre-silicon execution engines SystemC virtual platforms complement and feed.
- [AMS (Analog/Mixed-Signal) Verification](ams-verification.md) — where SystemC real-number models meet analog blocks.
- [DPI — Direct Programming Interface](dpi.md) — the lighter-weight C/C++ bridge from SystemVerilog, often a stepping stone before a full SystemC model.

## Grounded in these DVCon papers

- **Analysis of TLM-2.0 and it's Applicability to Non Memory Mapped Interfaces** (2016, DVCon US) — Guillaume Delbergue, Mark Burton, Bertrand Le Gal and Christophe Jego. Diagnoses TLM-2.0's memory-mapped bias and proposes extensions for non-memory-mapped protocols.
- **Building a coherent ESL design and verification eco-system with SystemC, TLM, UVM-SystemC, and CCI** (2016, DVCon Europe) — Martin Barnasconi. The canonical map of the SystemC/TLM/UVM-SystemC/CCI eco-system and how to make it coherent.
- **UVM and SystemC Transactions — An Update** (2016, DVCon US) — David Long and John Aynsley. Compares UVM Connect and UVM-ML for bridging SystemC TLM into UVM, untimed and approximately-timed.
- **Plugging the Holes: SystemC and VHDL Functional Coverage Methodology** (2011, DVCon US) — Pankaj Singh and Gaurav Kumar Verma. Brings functional-coverage discipline to SystemC/VHDL environments.
- **Acceleration of product and test environment development using SystemC-TLM** (2018, DVCon Europe) — Florian Barrau, Alexandre Piccini and Alexandre Nabais Moreno. Uses SystemC-TLM virtual platforms to develop both product and test equipment before hardware exists.
- **TLM Beyond Memory Mapped Busses** (2016, DVCon Europe) — Bart Vanthournout and Mark Burton. The TLM Working Group's case for extending TLM-2.0 to general model-to-model communication.
- **Runtime Fault-Injection Tool for Executable SystemC Models** (2014, DVCon India) — Bogdan-Andrei Tabacaru, Moomen Chaari and Wolfgang Ecker. Introduces SCFIT, a GDB-driven fault-injection tool for SystemC TLM/RTL models.
- **Integrating SystemC TLM into FMI 3.0 Co-Simulations with an Open-Source Approach** (2025, DVCon Europe) — Andrei Mihai Albu, Giovanni Pollo and Alessio Burrello. Wraps SystemC TLM as FMI 3.0 FMUs for multi-domain co-simulation.
- **Using UVM-ML library to enable reuse of TLM2.0 models in UVM test benches** (2018, DVCon Europe) — Sarmad Dahir, Hans-Martin Bluethgen, Rafael Zuralski and Nils Luetke-Steinhorst. Reuses SystemC TLM-2.0 reference models inside UVM via UVM-ML.
- **UVM Made Language Agnostic — Introducing UVM For SystemC** (2017, DVCon Europe) — Akhila M. A field report on the UVM-SystemC library for layered native-C++ testbenches.
- **The missing SystemC and TLM asynchronous features enabling inter-simulation synchronization** (2016, DVCon Europe) — Guillaume Delbergue, Mark Burton, Bertrand Le Gal and Christophe Jego. Proposes SystemC features for multi-kernel and multi-thread TLM synchronization.
- **Parameter Passing from SystemVerilog to SystemC for Highly Configurable Mixed-Language Designs** (2015, DVCon US) — Bishnupriya Bhattacharya, Samik Das and Zhiting Duan. Extends CCI parameters across the SystemVerilog/SystemC boundary.
- **Advancing system-level verification using UVM in SystemC** (2014, DVCon US) — Martin Barnasconi, François Pêcheux and Thilo Vörtler. The UVM-SystemC proof-of-concept class library for structured, reusable C++ testbenches.
- **TLM-2.0 in SystemVerilog** (2011, DVCon US) — Mark Glasser and Janick Bergeron. Describes the translation of TLM-2.0 from SystemC into SystemVerilog UVM.
- **Memory Debugging of Virtual Prototypes with TLM 2.0** (2012, DVCon US) — George F. Frazier, Qizhang Chao and Neeti Bhatnagar. Builds generic memory-debug tools on the TLM-2.0 `transport_dbg` interface.

---

*Part of the [DVCon LLM Wiki](index.md). Synthesized from 1,852 DVCon papers (2010–2026).*
