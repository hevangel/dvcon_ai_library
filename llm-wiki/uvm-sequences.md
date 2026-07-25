# UVM Sequences and Sequence Layering

> *"In UVM, a sequence is where the test lives. Everything else — agents, drivers, monitors — is plumbing; the sequence decides what transactions get sent and in what order. The hard part isn't writing one sequence, it's coordinating many of them across multiple interfaces without your testbench turning into a tangle of hierarchical paths. For years the standard answer was the virtual sequencer, a placeholder component stuffed with sequencer handles. Cummings and Glasser have spent the last few DVCons arguing that virtual sequencers are a maintenance nightmare and offering a better answer: sequencer containers. So how do sequences actually work, and why is the coordination problem still being argued in 2025? Let's dig in."*

## What it is

A **sequence** generates `uvm_sequence_item` transactions and sends them to a **sequencer**, which hands them to a **driver** that wiggles pins. Sequences are launched with the `start()` task, which takes an optional sequencer handle. Supply a real sequencer and you get a *normal sequence*, bound to that one interface. Omit it (or pass `null`) and you get a *virtual sequence*, which has no sequencer of its own and must somehow obtain handles to the real sequencers it coordinates [Sequencer Containers - A Unified and Simple Technique to Execute Both Sequences and Virtual Sequences, 2025]. UVM is famously "silent on how virtual sequences obtain sequencer handles," which is why the testbench has to invent a mechanism.

The traditional mechanism is the **virtual sequencer** — a sequencer that "serves as a container for sequencer handles and does not function as a typical sequencer." Virtual sequences reach into it through the `p_sequencer` macro to grab the handles they need [A Summary and Examination of UVM Virtual Sequence Techniques, 2025]. Below this coordination layer, the sequencer–driver handshake is built on a TLM-derived port pair (`seq_item_export`) that provides get, put, and peek — but Goyal and Refice argue it "isn't strictly UVM TLM1" and doesn't cleanly handle the back-and-forth handshake, motivating backward-compatible TLM2-based updates [Exploring UVM TLM2 based Sequence, Sequencer and Driver in UVM, 2026].

## How it's used in practice

Sequence **layering** adds an intermediary sequence between a high-level scenario and the leaf sequencer, enabling protocol-independent test development. Shariff et al. layer an adapter sequence above RAL register sequences for PCIe and SPI, achieving finer granularity with only minor RAL model modifications [UVM Sequence Layering for Register Sequences, 2023]. Reactive stimulus takes layering further: the sequence reads response items fed back from the driver through the sequencer and chooses the next transaction accordingly — Cummings et al. show this for a multi-interface FIFO DUT where a master sequence reacts to FIFO status [Advanced UVM, Multi-Interface, Reactive Stimulus Techniques, 2021].

For coordination, the modern recommendation is the **sequencer container**. A *sequencer pool* is a singleton into which every agent's sequencer registers itself by a unique, friendly name; the test (or virtual sequence) then retrieves handles by name with no hierarchical pathing and no `uvm_resource_db` lookup [Sequencer Containers - A Unified and Simple Technique to Execute Both Sequences and Virtual Sequences, 2025]. A *sequencer aggregator* is a non-singleton variant for when you need multiple distinct handle collections [A Summary and Examination of UVM Virtual Sequence Techniques, 2025]. The pay-off is that "the sequencer handle could update itself as the testbench structure evolves" — fixed paths, the source of "bugs as a testbench evolves," disappear [Sequencer Containers - A Unified and Simple Technique to Execute Both Sequences and Virtual Sequences, 2025]. Beyond coordination, the relevance API lets sequences prioritize composition over inheritance using mixins and the visitor pattern [Keeping Your Sequences Relevant, 2017], and an interactive debug library can create, randomize, and start a sequence on any sequencer at runtime through SV-DPI [UVM Interactive Debug Library: Shortening the Debug Turnaround Time, 2017].

## Pitfalls and where the field is heading

Virtual sequencers are the central pitfall. Because they are populated by referring to their hierarchical location, "any component that requires a partial or complete component path is not hierarchically independent"; relocating a virtual sequencer means rewriting pathnames everywhere [Sequencer Containers - A Unified and Simple Technique to Execute Both Sequences and Virtual Sequences, 2025]. Peryer's earlier critique of the sequencer–driver relationship argues the legacy stimulus architecture was inherited unchanged from OVM and "isn't handled properly by UVM TLM1," sowing handshake complexity [There's something wrong between Sally Sequencer and Dirk Driver, 2012]. Even with good containers, you must keep sequencer names unique — including inside agent arrays — or a virtual sequence can land on the wrong sequencer [Sequencer Containers - A Unified and Simple Technique to Execute Both Sequences and Virtual Sequences, 2025].

The field is pushing sequence authoring up the abstraction ladder. PSS lets you specify scenarios once and execute them across simulation, emulation, and post-silicon, and layered register sequences show the same instinct applied inside UVM [UVM Sequence Layering for Register Sequences, 2023]. There is also a parallel "sequencer" meaning in the SoC world — the embedded micro-sequencer that generates real-time radar ramp control signals [Leveraging RISC-V for Flexible and Adaptive Real-Time Radar Sequencing, 2025] — whose program-counter-level coverage has to be mapped back to high-level source to close coverage [Sequencer Coverage Exclusion Optimiser: Streamlining Coverage Closure in Dynamic Sequencer-Based Designs, 2025]. The UVM sequence concept and the embedded sequencer concept are distinct, but both share the same core problem: coordinating many timed events correctly.

## See also

- [UVM Testbench Architecture](uvm-testbench-architecture.md) — the env and agents whose sequencers these sequences drive.
- [Universal Verification Methodology (UVM)](uvm-overview.md) — the methodology that defines sequences and sequencers.
- [PSS — Portable Stimulus Standard](pss.md) — the higher-level, platform-portable successor to hand-written sequences.

## Grounded in these DVCon papers

- **Sequencer Containers - A Unified and Simple Technique to Execute Both Sequences and Virtual Sequences** (2025, DVCon US) — Clifford E. Cummings and Mark Glasser. Introduces sequencer pools and aggregators as replacements for virtual sequencers.
- **A Summary and Examination of UVM Virtual Sequence Techniques** (2025, DVCon India) — Clifford E. Cummings, Mark Glasser and Smita Kulkarni. Comparative survey of the four virtual sequence techniques.
- **Exploring UVM TLM2 based Sequence, Sequencer and Driver in UVM** (2026, DVCon US) — N. Goyal and J. Refice. Backward-compatible TLM2 updates to the legacy sequencer–driver handshake.
- **UVM Sequence Layering for Register Sequences** (2023, DVCon India) — Muneeb Ulla Shariff, Sangeetha Sekar and Ravi Reddy. Adapter-layer sequences over RAL for PCIe and SPI.
- **Advanced UVM, Multi-Interface, Reactive Stimulus Techniques** (2021, DVCon US) — Clifford E. Cummings, Stephen DOnofrio and Jeff Wilcox. Reactive sequences that consume driver response feedback.
- **Verification strategy for pipeline type of design** (2018, DVCon US) — Djuro Grubor. Sequenced strategy for verifying multi-stage pipelined IP.
- **Weathering the Verification Storm: Methodology Enhancements used on a Next Generation Weather Satellite C&DH Program** (2013, DVCon US) — Michael Donnelly and Michael Horn. Layered sequence and agent methodology for satellite FPGAs.
- **Keeping Your Sequences Relevant** (2017, DVCon US) — Nicholas Zicha and Eric Combes. The relevance API plus mixins and the visitor pattern for sequences.
- **There's something wrong between Sally Sequencer and Dirk Driver** (2012, DVCon US) — Mark Peryer. Critique of the OVM-inherited sequencer–driver stimulus architecture.
- **Leveraging RISC-V for Flexible and Adaptive Real-Time Radar Sequencing** (2025, DVCon Europe) — Michael Atzmüller, Rainer Findenig and Bernhard Greslehner-Nimmervoll. RISC-V-based FMCW radar sequencer design.
- **Sequencer Coverage Exclusion Optimiser: Streamlining Coverage Closure in Dynamic Sequencer-Based Designs** (2025, DVCon India) — Alisha Parvez, Preethi Ashok Kumar and Ravi Mangal. Automated mapping of PC coverage to HLL source for embedded sequencers.
- **UVM Interactive Debug Library: Shortening the Debug Turnaround Time** (2017, DVCon US) — Horace Chan. SV-DPI library to start sequences on any sequencer at runtime.

---

*Part of the [DVCon LLM Wiki](index.md). Synthesized from 1,852 DVCon papers (2010–2026).*
