# UPF — Power Intent (IEEE 1801)

> *Your RTL describes what the chip does. But which parts of it are switched off to save battery, which registers survive a power collapse, and which level shifters translate between a 1.0 V island and a 0.7 V island? None of that belongs in the RTL — and that is the problem UPF was invented to solve. The Unified Power Format is a *side file* that annotates a design with power domains, isolation cells, retention registers, level shifters, and power switches, separate from the functional code so the same RTL can be reused across power configurations. The catch: that side file is consumed by every stage of the flow — RTL sim, gate-level sim, synthesis, place-and-route — and each stage wants a slightly different flavor. Teams have spent months stitching UPF variants together by hand. So how did a single standard grow six language reference manuals, and how do you keep one UPF honest from RTL to tapeout? Let's dig in.*

## What it is

**UPF** (Unified Power Format), standardized as IEEE 1801, captures the *power intent* of an electronic system independently of its RTL. Its central concept, introduced in UPF 1.0 in early 2007, is to let users define and manage power for any design without touching the design itself [What's New in IEEE 1801 and Why?, 2025]. The standard has since grown through six language reference manuals — UPF 1.0, 2.0, 2.1, 3.0, 3.1, and the upcoming 4.0 — each adding constructs to address gaps the previous release exposed.

At its core, UPF lets you declare **supply nets**, **power domains**, and the special cells that connect them: **isolation cells** clamp signals at domain boundaries so powered-down logic doesn't drive garbage into live logic; **retention registers** preserve state across a power collapse; **level shifters** translate between supply voltages; and **power switches** gate the supply itself [Mixed Signal Verification of UPF based designs, 2015]. Early versions described the power intent but not the library cells implementing it; UPF 2.1 introduced library commands to capture intent for special power-management cells and hard macros, so designers no longer had to fall back on Liberty formats alone [The UPF 2.1 library commands, 2015].

The reason this is hard is that low-power SoCs now have many power domains and hundreds of power modes. Power-aware verification has to confirm the chip works correctly in every domain and every mode transition — a combinatorial problem that demands planning, not just ad hoc tests [Power Aware Verification Strategy for SoCs, 2013].

## How it's used in practice

UPF is consumed across the entire flow, and that is where the real pain lives. **Hierarchical UPF** — one UPF file per block, composed at the SoC top — is the natural way to write it: lower-level blocks (IPs) are designed independently with their own power intent, then integrated. Historically, however, back-end tools could not consume hierarchical UPF cleanly because of IP-level power-intent conflicts, power-state-table conflicts in child UPFs, power-domain explosions, and feedthrough-routing issues. Teams were forced to generate **merged UPF** by flattening and merging equivalent supplies — a script-driven, buggy process that consumed about 70% extra effort and roughly two months per initial bring-up at Intel [Hierarchical UPF, 2022]. The recent proof-of-concept work shows hierarchical UPF can finally be consumed directly by back-end flows, with guidelines for third-party IP integration.

The same fragmentation shows up verification-side. The UPF written for RTL simulation usually has to be refined for gate-level simulation because of design-hierarchy changes, cell placements, and cell connections — producing different UPF flavors that lack consistency [REUSABLE UPF, 2018]. Logical equivalence checking between the variants is risky and slow, and full confidence often arrives only at GLS, very late in the cycle. Modeling is another gap: UPF has no native construct for low-dropout regulators (LDOs), so verification engineers model them by hand in SystemVerilog — a burden that multiplies as LDO counts grow [Low Power Verification With LDO, 2016].

To make power intent programmatically inspectable, UPF provides query functions and `bind_checker` constructs that let assertions reference power-management objects [Low-Power Verification Methodology using UPF Query functions, 2016]. **Generic references** extend this so a single retention strategy can target cells whose restore pins agree but whose clocks differ [UPF GENERIC REFERENCES, 2016]. Srivastava et al. pushed further with PA-APIs and the **UPF Information Model**, exposing power-management objects as APIs so UVM testbenches can interact with low-power designs in a standardized, non-proprietary way [PA-APIs, 2015] [UVM and UPF, 2019]. Power models built on top of the Information Model tame the explosion of UPF code that occurs when hundreds of instances of a hard IP each carry their own intent [UPF Power Models, 2018].

## Pitfalls and where the field is heading

The dominant pitfall is fragmentation: six LRMs, three or four UPF flavors per project, and tools that interpret the standard differently. Khondkar's retrospective on the LRM timeline makes clear that adoption is "painfully difficult" precisely because diversified power-reduction schemes, varying design characteristics, and overlapping standard releases all coexist [What's New in IEEE 1801 and Why?, 2025]. The shift-left trend is pushing virtual-instrumentation-based predictive analysis earlier so generated UPF is validated before it ever reaches simulation [Next-Gen Low Power Verification, 2024]. The throughline of the corpus is simple: write hierarchical UPF once, validate it with queryable APIs, and refuse to maintain parallel flavors by hand.

## See also

- [Low-Power Verification with UPF](low-power-verification.md) — verifying that power domains, isolation, and retention actually behave correctly.
- [Power-Aware Verification](power-aware-verification.md) — making the testbench itself power-aware so it checks behavior across modes.
- [SystemVerilog](systemverilog.md) — the host RTL/testbench language that UPF annotates and that fills UPF's modeling gaps (e.g., LDOs).

## Grounded in these DVCon papers

- **Hierarchical UPF: Uniform UPF across FE & BE** (2022, DVCon US) — Dipankar Narendra Arya, Balaji Vishwanath Krishnamurthy and Aditi Nigam. The proof-of-concept and guidelines that finally let back-end flows consume hierarchical UPF instead of merged UPF.
- **Mixed Signal Verification of UPF based designs — A Practical Example** (2015, DVCon US) — Andrew Milne and Damian Roberts. A worked Sigma-Delta ADC example showing power domains, isolation, retention, and level shifters in practice.
- **Power Aware Verification Strategy for SoCs** (2013, DVCon US) — Boobalan Anantharaman and Arunkumar Nara. Lays out why power-aware verification requires planning across many domains and modes.
- **What's New in IEEE 1801 and Why?** (2025, DVCon US) — Progyna Khondkar. The historical timeline of all six UPF LRMs and guidance on which release to adopt.
- **Next-Gen Low Power Verification: Empowering Shift-Left Predictive Analysis with Virtual Instrumentation** (2024, DVCon India) — Sachin Bansal, Yi Liu and M. Vaishnavi Reddy. Shift-left validation of physical-aware generated UPF.
- **REUSABLE UPF: Transitioning from RTL to Gate Level Verification** (2018, DVCon US) — Durgesh Prasad, Jitesh Bansal and Madhur Bhargava. Catalogs the differences between RTL UPF and GLS UPF and how to minimize rework.
- **Low-Power Verification Methodology using UPF Query functions and Bind checkers** (2014, DVCon Europe) — Madhur Bhargava and Durgesh Prasad. Uses UPF query functions and assertions to validate power control sequences.
- **UVM and UPF: an application of UPF Information Model** (2019, DVCon US) — Amit Srivastava, Harsh Chilwal and Srivatsa Vasudevan. Standardizes UVM/UPF interoperation via the UPF Information Model APIs.
- **UPF GENERIC REFERENCES: UNLEASHING THE FULL POTENTIAL** (2016, DVCon US) — Durgesh Prasad and Jitesh Bansal. Extends `bind_checker` to strategies whose cells share control but differ in clocks.
- **UPF Power Models: Empowering the power intent specification** (2018, DVCon Europe) — Amit Srivastava and Harsh Chilwal. Tames the explosion of UPF code for massively replicated hard/soft IPs.
- **Low Power Verification With LDO** (2016, DVCon US) — Shang-Wei Tu, Amol Herlekar and Yu-Juei Chen. Addresses UPF's lack of native LDO modeling.
- **The UPF 2.1 library commands: Truly unifying the power specification formats** (2015, DVCon US) — Amit Srivastava, Awashesh Kumar and Vinay Singh. Introduces library commands for special power-management cells and hard macros.
- **PA-APIs: Looking beyond power intent specification formats** (2015, DVCon US) — Amit Srivastava and Awashesh Kumar. Argues for queryable power-management APIs beyond static UPF.
- **Low Power Verification with UPF: Principle and Practice** (2010, DVCon US) — Jianfeng Liu, Mi-Sook Hong, Bong Hyun Lee and JungYun Choi. An early articulation of low-power verification principles grounded in UPF.

---

*Part of the [DVCon LLM Wiki](index.md). Synthesized from 1,852 DVCon papers (2010–2026).*
