# The DVCon Conference

> *"DVCon — the Design & Verification Conference — is where the chip industry argues about how to prove a chip works before you tape it out. If you've ever read a UVM paper, a UPF tutorial, or a CDC methodology guide, odds are it premiered on a DVCon stage. There are now five of them: the original US conference, plus India, Europe, Japan, and China, each with its own proceedings. The corpus this wiki is built from spans 1,852 papers from 2010 to 2026, and it captures the field's whole arc — from OVM-to-UVM migration, through CDC and low-power signoff, to today's LLM-assisted verification. So how did we get here, and what does DVCon actually cover? Let's dig in."*

## What it is

DVCon is a conference and exhibition dedicated to the design and verification of electronic systems, organized around the languages, standards, and methodologies that the chip industry actually uses — SystemVerilog, UVM, UPF (IEEE 1801), SystemC, SVA, and IP-XACT. Its papers are highly applied: case studies from teams at Intel, Samsung, NXP, AMD, CERN, and Lockheed Martin, rather than academic theory. The conferences are geographically distributed — DVCon US, DVCon India, DVCon Europe, DVCon Japan, and DVCon China — and each runs its own call for papers and proceedings, which is why the same topic (low-power verification, say) appears with regional variation across the corpus.

The recurring subject matter tracks whatever the industry is wrestling with that year. Recent years foreground low-power and power-aware verification built on UPF [Addressing the Complex Challenges in Low-Power Design and Verification, 2016] [Debug Challenges in Low-Power Design and Verification, 2015] [An Improved Methodology for Debugging UPF Issues at SoC level Power Aware Simulations, 2023]; CDC and RDC signoff [Next-generation Power Aware CDC Verification - What have we learned?, 2015] [A Specification-Driven Methodology for the Design and Verification of Reset Domain Crossing Logic, 2018] [A Systematic Take on Addressing Dynamic CDC Verification Challenges, 2019]; and system-level ESL ecosystems combining SystemC, TLM, UVM-SystemC, and CCI [Building a coherent ESL design and verification eco-system with SystemC, TLM, UVM-SystemC, and CCI, 2016].

## How the papers fit the verification flow

DVCon papers tend to map onto the standard verification flow. At the front end are requirements and planning papers — for example, automated traceability of requirements for ISO 26262 safety-critical mixed-signal systems [Automated traceability of requirements in the design and verification process of safety-critical mixed-signal systems, 2021]. In the middle are stimulus and testbench papers — reactive UVM stimulus techniques across multiple interfaces [Advanced UVM, Multi-Interface, Reactive Stimulus Techniques, 2021], constraint-based SystemC AMS verification [Using Constraints for SystemC AMS Design and Verification, 2018], and unified MiL/HiL methodologies for mixed-signal prototyping [Unified Model/Hardware-in-the-Loop Methodology for Mixed-Signal System Design and Hardware Prototyping, 2021].

At the back end are register automation and IP packaging, like the SystemRDL-driven register design and VMM verification flow [Automated approach to Register Design and Verification of complex SOC, 2011]. The corpus also reaches into specialized domains: CERN's SEE-tolerant ASIC methodologies for the LHC [Design and Verification of SEE-Tolerant ASICs at CERN: Methodologies and Challenges, 2024], the CPAS Cocotb-based open-source power-aware simulation framework [CPAS: Cocotb Power Aware Simulation Framework, 2024], and successive refinement of UPF to decouple front-end and back-end power intent [Successive Refinement - An approach to decouple Front-End and Back-end Power Intent, 2021]. Read across the proceedings and you see the field's center of gravity migrating up the abstraction ladder — from RTL and gate-level toward system-level, software-aware, and AI-assisted verification.

## Where the field is heading

If you read the proceedings chronologically, three trends jump out. First, the move from directed tests to metric-driven and coverage-driven flows, then to portable stimulus (PSS) that runs across simulation, emulation, and post-silicon. Second, the steady absorption of safety and security standards — ISO 26262, DO-254 — into the mainstream flow, dragging requirements traceability along with them [Automated traceability of requirements in the design and verification process of safety-critical mixed-signal systems, 2021] [A Specification-Driven Methodology for the Design and Verification of Reset Domain Crossing Logic, 2018]. Third, the arrival of open-source and Python-fronted tooling [CPAS: Cocotb Power Aware Simulation Framework, 2024] and, most recently, of LLMs and AI agents throughout the flow. The conference itself is the most reliable record of where verification engineers actually spend their time — which makes its proceedings the right substrate for a wiki like this one.

## See also

- [Universal Verification Methodology (UVM)](uvm-overview.md) — the single most-discussed topic at DVCon.
- [Verification Planning and Metric-Driven Verification](verification-planning-mdv.md) — the front-end discipline that many DVCon papers presume.

## Grounded in these DVCon papers

- **Addressing the Complex Challenges in Low-Power Design and Verification** (2016, DVCon Europe) — Madhur Bhargava, Durgesh Prasad and Jitesh Bansal. Debug methodology for sophisticated low-power management architectures.
- **Automated traceability of requirements in the design and verification process of safety-critical mixed-signal systems** (2021, DVCon US) — Gabriel Pachiana, Maximilian Grunwald and Thomas Markwirth. Tool flow for automated ISO 26262 requirements traceability across AMS environments.
- **A Specification-Driven Methodology for the Design and Verification of Reset Domain Crossing Logic** (2018, DVCon US) — Priya Viswanathan, Kurt Takara and Chris Kwok. A repeatable three-step RDC methodology with requirements traceability.
- **Building a coherent ESL design and verification eco-system with SystemC, TLM, UVM-SystemC, and CCI** (2016, DVCon Europe) — Martin Barnasconi. Combining SystemC, TLM, UVM-SystemC, and CCI into one ESL flow.
- **Next-generation Power Aware CDC Verification - What have we learned?** (2015, DVCon US) — Kurt Takara, Chris Kwok and Naman Jain. Lessons from CDC verification across power and voltage domains.
- **Debug Challenges in Low-Power Design and Verification** (2015, DVCon US) — Durgesh Prasad, Madhur Bhargava and Jitesh Bansal. In-depth analysis of low-power debug problems and techniques.
- **Automated approach to Register Design and Verification of complex SOC** (2011, DVCon US) — Ballori Banerjee, Subashini Rajan and Silpa Naidu. SystemRDL-driven register design and VMM verification.
- **An Improved Methodology for Debugging UPF Issues at SoC level Power Aware Simulations** (2023, DVCon Europe) — Ruchi Misra, S Shrinidhi Rao and Alok Kumar. Triage methodology for UPF syntax and strategy issues.
- **CPAS: Cocotb Power Aware Simulation Framework** (2024, DVCon Europe) — Ahmed Alsawi, Liam O'Reilly and Evin Hughes. Open-source Python and Cocotb framework for power-aware simulation.
- **Design and Verification of SEE-Tolerant ASICs at CERN: Methodologies and Challenges** (2024, DVCon Europe) — Adithya Pulli, Matteo Lupi and Stefano Esposito. Radiation-tolerant ASIC verification for the LHC.
- **Successive Refinement - An approach to decouple Front-End and Back-end Power Intent** (2021, DVCon Europe) — Rohit Kumar Sinha. UPF 3.1 successive refinement for process-agnostic power intent.
- **Unified Model/Hardware-in-the-Loop Methodology for Mixed-Signal System Design and Hardware Prototyping** (2021, DVCon Europe) — Martin Barnasconi, Wil Kitzen and Thieu Lammers. MiL/HiL unification of system design and hardware prototyping.
- **Advanced UVM, Multi-Interface, Reactive Stimulus Techniques** (2021, DVCon US) — Clifford E. Cummings, Stephen DOnofrio and Jeff Wilcox. Reactive stimulus across multiple FIFO interfaces.
- **A Systematic Take on Addressing Dynamic CDC Verification Challenges** (2019, DVCon US) — Sukriti Bisht, Sulabh Kumar Khare and Ashish Hari. Systematic approach to dynamic CDC verification.
- **Using Constraints for SystemC AMS Design and Verification** (2018, DVCon Europe) — Thilo Vörtler, Karsten Einwich and Muhammad Hassan. CRAVE-extended constraints for mixed-signal virtual prototypes.

---

*Part of the [DVCon LLM Wiki](index.md). Synthesized from 1,852 DVCon papers (2010–2026).*
