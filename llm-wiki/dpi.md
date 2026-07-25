# DPI — Direct Programming Interface

> *"Every UVM team eventually hits the same wall: there's a perfect C/C++ reference model, a Linux driver, a MATLAB golden model, or a packet-decoder library that already does exactly what you need — and your SystemVerilog testbench can't talk to it. That gap is what **DPI-C** was built to close. The Direct Programming Interface is a thin, fast, native calling convention between SystemVerilog and C that lets you import a C function as if it were a task and export a SystemVerilog routine back to C with no foreign-function boilerplate. Used well, it lets you reuse millions of lines of existing code inside your testbench. Used badly, it turns into a copy-marshalling nightmare that quietly halves your simulation speed. Let's see how to keep it on the right side of that line."*

## What DPI is, and how the call works

SystemVerilog DPI-C is, at its core, a C calling convention. When SystemVerilog imports a C function — `import "DPI-C" function int f(input int i);` — the simulator builds the same stack a C compiler would and jumps to the C symbol; the reverse works for `export "DPI-C"`. The shared header `dpiheader.h` carries the ANSI prototypes and the type map. In benchmarking, simple DPI-C calls "should execute like any other C code calls, with little or no extra overhead" [Making Your DPI-C Interface a Fast River of Data, 2021].

Simple native C types map one-to-one to SystemVerilog types — `int` to `int`, `long long` to `longint`, `double` to `real`, `void *` to `chandle` — and these are the cheapest calls you can make [Making Your DPI-C Interface a Fast River of Data, 2021]. Packed structs, enums, and (with care) arrays are also passable, but the golden rule from "DPI Redux" is blunt: keep DPI-C calls simple, let C do the integer work, let SystemVerilog do the 4-state logic work, and design large arrays as "arrays of ints" so they pass by reference rather than by copy [DPI Redux. Functionality. Speed. Optimization, 2017]. For code that needs to survive across calls or use pthreads, the DPI-C call semantics need explicit management — but plain import/export is exactly the function-call mechanism it appears to be.

## How teams actually use it

The most common pattern is the C reference model plugged into a UVM scoreboard. "UVM and C — Perfect Together" sketches the canonical shapes: a golden C model invoked via `import`, a C-side bus transfer generator that does not know it is running inside a simulator, and a top-level C test program driven from a SystemVerilog shell [UVM and C — Perfect Together, 2018]. Modern variants integrate DPI-C directly into UVM **Register Abstraction Layer (RAL)** adapters so that the C model stays in lockstep with bus traffic, automating what would otherwise be a hand-written predictor [Real-Time Synchronization of C model with UVM Testbench, 2025]. For complex protocols like PCIe the C side has to handle concurrency, and tooling now exists for threading, acceleration, and reuse from emulation down to post-silicon ["C" you on the faster side, 2014].

Larger efforts push the boundary further. **CVM** is a unified C++/SystemVerilog library for messaging, configuration, and topology across the language line, slated for open-source release [CVM — A Library for Unified C++ and SystemVerilog Testbench Development, 2025]. A 2026 framework reuses mature Linux drivers as bare-metal drivers by replacing kernel services with a "kernel proxy" C++ class exposed through DPI-C [Accelerating Bare Metal Driver Development with Linux Drivers and System Verilog DPI-C, 2026]. AMS teams now auto-generate DPI-C models from system-level circuit models so analog and digital share one golden reference [Reuse of System-level Circuit Models in Mixed-Signal Verification, 2025].

## Pitfalls: when DPI-C stops being cheap

For all its power, DPI-C has well-known performance cliffs. The first is data marshalling: every `int` is essentially free, but every unpacked struct, multi-dimensional array, or string crossing the boundary costs a copy. For a heavy-traffic scoreboard this dominates runtime, which is why Velickovic and Bozinovic explicitly compare DPI-C-bound C models against static pre-computed value tables and report cases where the table approach wins on raw speed at the cost of reusability [Functional Verification Using C Model: DPI-C VS Static Value Tables, 2024].

The second is build/runtime friction: mixing DPI-C and UVM testbenches in a legacy monolithic flow requires custom harness work to manage build, scenario development, and debug turn-around time [Practical Scheme to Enhance Verification Turn-Around-Time by Using Reusable Harness Interface (RHI), 2018]. The third is portability — Aynsley's early guidance was explicit that DPI-C integration of C/C++/SystemC into OVM/VMM testbenches must avoid simulator-specific constructs to remain portable across simulators [SystemVerilog Meets C++, 2010]. The fourth, and increasingly relevant, is mixed-language UVM sequencing: blending UVM sequences with DPI-C tasks requires careful task/function syntax in both the SystemVerilog interface and the UVM sequence layer, but is a powerful reuse pattern [Having Your Cake and Eating It Too Programming UVM Sequences with DPI-C, 2024]. Used with discipline, DPI-C is invisible; used carelessly, it is the bottleneck you will spend a week profiling.

## See also

- [SystemVerilog](systemverilog.md) — DPI is part of the IEEE 1800 SystemVerilog standard.
- [SystemC (IEEE 1666)](systemc.md) — SystemC TLM models are a primary C-side target for DPI.
- [UVM Scoreboards and Predictors](uvm-scoreboards.md) — C reference models typically plug in here via DPI-C.

## Grounded in these DVCon papers

- **Accelerating Bare Metal Driver Development with Linux Drivers and System Verilog DPI-C** (2026, DVCon US) — Suchir Gupta, Amit Sharma and Suneetha Suryadevara. A "kernel proxy" C++ class exposed via DPI-C reuses mature Linux drivers as bare-metal drivers for IP verification and embedded development.
- **DPI Redux. Functionality. Speed. Optimization** (2017, DVCon US) — Rich Edelman, Rohit Jain and Hui Yin. The canonical guide to common and optimal DPI-C usage, including the "arrays of ints" rule and threading pitfalls.
- **"C" you on the faster side: Accelerating SV DPI based co-simulation** (2014, DVCon US) — Parag Goel, Amit Sharma and Hari Vinodh Balisetty. Techniques for C/C++ testbench concurrency (PCIe and friends), with reuse paths to emulation and post-silicon.
- **CVM — A Library for Unified C++ and SystemVerilog Testbench Development** (2025, DVCon India) — Varun Koyyalagunta, Jiahan Zhang and Mansoor Anees. Open-source library for messaging, configuration, logging, and topology across the C++/SystemVerilog boundary.
- **Real-Time Synchronization of C model with UVM Testbench** (2025, DVCon US) — Kirtan Mehta. Integrates DPI-C into UVM RAL adapters to keep a C golden model in lockstep with bus traffic, automating the predictor.
- **Making Your DPI-C Interface a Fast River of Data** (2021, DVCon US) — Rich Edelman. Practical walkthrough of the call mechanism, type mapping, and performance optimization for maximum throughput.
- **UVM and C — Perfect Together** (2018, DVCon US) — Rich Edelman. Canonical integration patterns: golden C model, C-side bus generator, and C test program driven from a SystemVerilog shell.
- **Practical Scheme to Enhance Verification Turn-Around-Time by Using Reusable Harness Interface (RHI)** (2018, DVCon US) — Jongpil Jung, Hyunju Lee and Jaejin Ha. Merging a legacy DPI-C testbench with a UVM one to cut SoC verification TAT.
- **SystemVerilog Meets C++: Re-use of Existing C/C++ Models Just Got Easier** (2010, DVCon US) — John Aynsley. Portability guidance for integrating C/C++/SystemC into OVM/VMM testbenches without simulator-specific lock-in.
- **Reuse of System-level Circuit Models in Mixed-Signal Verification** (2025, DVCon US) — Bahaa Osman, Bhanu Singh and Minghua Li. Auto-generates SystemVerilog DPI-C models from AMS system models so analog and digital share one golden reference.
- **Functional Verification Using C Model: DPI-C VS Static Value Tables** (2024, DVCon Europe) — Djordje Velickovic and Katarina Bozinovic. Head-to-head comparison of DPI-C-bound C models against static pre-generated value tables on effort, performance, and reusability.
- **Having Your Cake and Eating It Too Programming UVM Sequences with DPI-C** (2024, DVCon Japan) — Rich Edelman and Tomoki Watanabe. Mechanisms and syntax for blending UVM sequences with DPI-C tasks and functions in both directions.

---

*Part of the [DVCon LLM Wiki](index.md). Synthesized from 1,852 DVCon papers (2010–2026).*
