# Security and Trust Verification

> *You spent two years building a chip that passes every functional test, hits 100% code coverage, and runs your firmware flawlessly. Then a grad student flips one bit through a side channel you never thought about, and the whole security story collapses. That's hardware security verification in a nutshell: it's not about whether your design *works*, it's about whether your design can be made to *misbehave*. Functional DV asks "did the design do the right thing?"; security DV asks "can an adversary make it do the wrong thing?" — and that second question is wilder, messier, and much younger as a discipline. The good news is the last decade of DVCon papers has converged on a workable playbook. So how did we get here?*

## What security verification actually means

The field organizes itself around the **CIA triad** — **Confidentiality, Integrity, and Availability** — borrowed straight from classical information security and re-cast for hardware assets [Formal Verification + CIA Triad, 2023]. A security asset is anything an adversary wants to read (a key), corrupt (a configuration register), or deny (a service), and the verification goal is to prove those assets stay protected under attack. The catch is that "protected" is not a single property you can write one assertion for; it has to be decomposed into a taxonomy of concrete weaknesses.

That taxonomy is where **MITRE's Common Weakness Enumeration (CWE)** for hardware has become the lingua franca [Effective Methodologies to Accelerate Security Verification, 2026]. The CWE catalog lists hundreds of weakness classes — from improper access control to insecure reset behavior — and modern flows map each applicable CWE into a set of verification goals, then derive checkers, assertions, or formal properties from them [Uncovering Hardware Vulnerabilities, 2025]. A second, complementary lens is **information flow tracking (IFT)**, which assigns security labels to data and watches where they propagate, rooting out unauthorized flows that a functional test would never catch [Securing Silicon, 2024]. Together, CWE-driven property generation and IFT give the security engineer something that "verify the design is secure" never did: a concrete to-do list.

## How it gets verified in practice

Real flows rarely pick one technique. Pre-silicon security verification today is a layered combination of **security-focused linting** for RTL hygiene, **dynamic information flow tracking** for confidentiality, **Formal Property Verification (FPV)** for property-level proof, and **Security Path Verification (SPV)** for showing sensitive paths are properly gated [Security Verification in Practice, 2026]. Simulation still plays a role for control logic like secure boot, crypto engines, and locking mechanisms, where checkers and reference models behave much like ordinary functional DV [Making Security Verification "SECURE", 2018].

What distinguishes security work from functional DV is the emphasis on **negative testing** and a shared-ownership mindset. The verification engineer has to assume the role of the attacker and ask "what could break this?", which requires sitting down with designers and architects early to build a threat model around the asset [Security Verification in Practice, 2026]. Tooling has followed: **Portable Stimulus (PSS)** is increasingly used to scale security scenarios across SoC configurations [Securing Silicon, 2024], and PSS-based flows have been demonstrated specifically for RISC-V **Physical Memory Protection (PMP)** verification [RISC-V Security Verification using Perspec, 2023]. Coverage — long a signoff metric in functional DV — is still being worked out for security, but stimuli- and property-based coverage models are emerging as the missing quantitative layer [Securing Silicon, 2024].

## Pitfalls and where the field is heading

The biggest open problem is cultural, not technical: hardware security verification is far less mature than functional verification, there are no widely agreed standard practices, and most of the methodology stays locked inside individual companies [Security Verification in Practice, 2026]. Threats also keep evolving, so a flow that was "good enough" last year may miss this year's attack class. Third-party IP is a persistent headache — in-house and vendor RTL can harbor **hardware Trojans**, and trusted golden models to compare against are rarely available outside of well-specified cores like RISC-V [An Automated Pre-silicon IP Trustworthiness Assessment, 2020][A Methodology to Verify Functionality, Security, and Trust for RISC-V Cores, 2020]. Even neural-network accelerators are now a target, with Trojans demonstrated on DNN hardware and detectable through formal means [Hardware Trojan Design and Detection, 2021].

The frontier is moving fast on two fronts. Protocol-level security is extending into high-speed links like **PCIe/CXL** with the **Layered IDE** framework, where state transitions and resource management hide subtle verification blind spots [Guardians of the Chip, 2025]. And the rise of **LLM-generated RTL** has produced a flood of designs that look plausible but embed real CWEs — one study ran formal verification on 60,000 LLM-generated SystemVerilog modules and catalogued the vulnerabilities by CWE number [All Artificial, Less Intelligence, 2024]. Meanwhile, ISO 21434 and automotive flows are pushing security and safety verification together, including symbolic-execution approaches for embedded Rust [Minimally Intrusive Safety and Security Verification of Rust RTIC Applications, 2025]. The thread connecting all of it: security is becoming a first-class signoff criterion, not a late-stage afterthought.

## See also

- [Formal Verification for Security and Trust](formal-security.md) — the formal-methods companion page; FPV and SPV are the engines under most security flows.
- [Assertion-Based Verification and SVA](assertion-sva.md) — SVA checkers are how many security properties are expressed and proven.

## Grounded in these DVCon papers

- **Securing Silicon: A Scalable, Platform-independent Hardware Security Verification Methodology** (2024, DVCon Europe) — Muhammad Abdullah Al Faisal, Sebastian Simon and Jaimin Nagar. A PSS-driven, scalable security verification flow with a stimuli-coverage signoff model.
- **Effective Methodologies to Accelerate Security Verification** (2026, DVCon US) — Lee Anthony Grajo, Ponnambalam Lakshmanan and Anders Nordstrom. End-to-end flow from security requirement extraction to formal + simulation signoff, with CWE-based coverage.
- **Making Security Verification "SECURE"** (2018, DVCon US) — Subin Thykkoottathil and Nagesh Ranganat. Early articulation of how simulation and formal complement each other on a security SoC.
- **Security Verification in Practice: Lessons from Pre-Silicon Analysis of SoC Subsystems** (2026, DVCon US) — Yashwanth Kumar A R and Rachana Maitra. A pre-silicon framework combining security linting, IFT, and formal on real SoC subsystems.
- **Uncovering Hardware Vulnerabilities: Formal Verification for Security-Focused Negative Testing** (2025, DVCon India) — Vedprakash Mishra. A ten-category CIA + CWE taxonomy driving SPV and FPV property generation.
- **Hardware Trojan Design and Detection with Formal Verification to Deep Neural Network** (2021, DVCon US) — Si-Han Chen, Yu-Ting Huang and Yi-Chun Kao. Trojan attacks on NN hardware and formal-based detection.
- **An Automated Pre-silicon IP Trustworthiness Assessment for Hardware Assurance** (2020, DVCon Europe) — John Hallman, David Landoll and Sergio Marchese. Trojan-detection by scanning third-party RTL without requiring a golden model.
- **RISC-V Security Verification using Perspec/Portable Stimulus** (2023, DVCon US) — Junxia Wang, Siyan. Li and Leven. Li. PSS applied to RISC-V Physical Memory Protection verification.
- **A Methodology to Verify Functionality, Security, and Trust for RISC-V Cores** (2020, DVCon Europe) — W. W. Chen, N. Tusinschi and T. L. Anderson. Spanning compliance, vulnerability detection, and trust verification on RISC-V cores.
- **All Artificial, Less Intelligence: GenAI through the Lens of Formal Verification** (2024, DVCon US) — Deepak Narayan Gadde, Aman Kumar and Thomas Nalapat. Formal CWE verification across 60,000 LLM-generated SystemVerilog designs.
- **Virtual ECUs with QEMU and SystemC TLM-2.0 The Best of Both Worlds** (2023, DVCon Europe) — Lukas Jünger, Jan Henrik Weinstock and Munish Jassi. Virtual prototyping for automotive safety and security at scale.
- **Formal Verification + CIA Triad: Winning Formula for Hardware Security** (2023, DVCon India) — Vedprakash Mishra and Anshul Jain. Mapping the CIA triad to formal security properties on multi-master SoCs.
- **Minimally Intrusive Safety and Security Verification of Rust RTIC Applications** (2025, DVCon Europe) — Pawel Dzialo, Ivar Jönsson and Malte Münch. Symbolic execution over machine code for safety- and security-critical embedded Rust.
- **Guardians of the Chip: Mastering Next-Gen Security for SoCs and IPs** (2025, DVCon US) — Jagata Sridevi, Vishnu Prasad K V and Deep Mehta. Categorizing and verifying blind spots in PCIe/CXL Layered IDE security.

---

*Part of the [DVCon LLM Wiki](index.md). Synthesized from 1,852 DVCon papers (2010–2026).*
