# Verification Planning and Metric-Driven Verification

> *"Verification planning is the unglamorous discipline that decides whether your project ships. Most engineers would rather write a clever sequence than a coverage plan, and that's exactly why projects slip — you spend six months generating random stimulus and still can't answer the question 'are we done?' Metric-driven verification (MDV) flips the question: decide what done means first, then drive stimulus and regressions toward those metrics. The DVCon corpus is full of papers trying to make this loop tight, automated, and honest. We'll walk through what a verification plan actually is, how metrics close the loop, and why the field keeps reaching for tools — and now LLMs — to keep the plan honest. Let's dig in."*

## What it is

A **verification plan** is the executable bridge between design requirements and coverage closure. Ehlers et al. argue that creating meaningful verification plans is "an art form yet to be fully codified" and lay out a codified process: requirements and design assessment, verification scope (block vs SoC, directed vs random vs formal), implementation planning, closure planning with coverage correlated back to the plan, and reviews [Best Practices in Verification Planning, 2013]. The plan is not just a document — it should be an "executable and living" artifact that drives the regression list itself.

**Metric-driven verification (MDV)** closes the loop: every feature in the plan maps to coverage points, every coverage point feeds back into stimulus generation, and completion criteria are quantitative. Khan et al. describe MDV as scaling "from a single IP block to a full system-on-a-chip" while remaining compatible with existing digital-only methodologies [Metric Driven Verification of Mixed-Signal Designs, 2011]. Graham emphasizes that as MDV moves from IP to SoC, the volume of coverage, regression, and defect data demands EDA tools that integrate with enterprise applications — defect trackers, requirements managers, source control — because the metrics generated inside simulators are otherwise stranded [Connecting Enterprise Applications to Metric Driven Verification, 2014].

## How it's used in practice

The dominant pattern is to keep requirements, plan, and regression in lockstep. Kreisinger and Chatterjee describe authoring the verification plan inside the same requirements-management tool (Jama Connect) as the design requirements, so changes propagate immediately and traceability is automatic; a REST-API script generates the regression list straight from the plan items [Verification Plan in Requirements Management Tool: Simple Traceability and Automated Interface to Regression Manager, 2024]. Ehlers et al. similarly push for a built-for-purpose planning tool whose source format supports scripting, so the plan can emit the regression testcase list with per-test simulation targets such as RTL, GLS, or AMS [Best Practices in Verification Planning, 2013].

MDV has expanded beyond digital into mixed-signal, firmware, and safety. Yang et al. and Brownell and Schmitt extend MDV to mixed-signal ASSPs using UVM-MS and real-number modeling [Metric Driven Mixed-Signal Verification Methodology and Practices for Complex Mixed-signal ASSPs, 2014] [Digitizing Mixed Signal Verification, 2014]. Savić applies a metric-driven flow to on-die firmware with in-house SystemVerilog and Perl tooling [A Metric-driven Methodology For Firmware Verification, 2016]. For ISO 26262, Rohleder et al. show how recent MDV tool advances lift the old limitation of combining results across simulation, formal, and emulation for functional-safety devices [Enhancements of metric driven verification for the ISO26262, 2016]. Multi-variant coverage modeling helps when one DUT has conformance, exhaustive, and application-level intents simultaneously [Multi-Variant Coverage: Effective Planning and Modelling, 2018].

## Pitfalls and where the field is heading

The classic pitfall is subjective coverage: defining functional coverage is "a subjective and dependent process largely based on human intellects," so whether your stimulus space is "random enough" is hard to answer objectively [Use Stimulus Domain for Systematic Exploration of Time Dimension and Automatic Testcase Construction, 2018]. Ega et al. make the same point for GLS, where a metric-driven methodology is needed just to gauge the quality of the stimuli that feed timing verification [Leveraging more from GLS: Using metric driven GLS stimuli to boost Timing Verification, 2018]. Without an executable plan, distributed teams produce inconsistent plans that never coalesce into clear reporting [Best Practices in Verification Planning, 2013].

The field is now turning to LLMs and GenAI to take the subjectivity out. Hyun et al. use design metadata and LLMs to define coverage bins early, before simulation runs, as Common Task Coverage [An Early Stage Coverage Measurement Methodology For Common Features Of System-On-Chip Verification, Using Design Metadata And Large Language Models, 2025]. Krushnan et al. describe SIGMA, a GenAI-augmented formal sign-off flow that automates plan extraction, environment setup, and claim development [SIGMA: Sign-off Intelligence with GenAI for Methodical Assurance in Formal Verification, 2026]. The trajectory is clear: the plan is becoming machine-readable and machine-queryable, with coverage measured earlier and traceability enforced by automation rather than by reviews.

## See also

- [Coverage Closure and Convergence](coverage-closure.md) — what you do when the metrics plateau.
- [Functional Coverage and Covergroups](functional-coverage.md) — the SystemVerilog construct behind most plan metrics.
- [Regression Optimization](regression-optimization.md) — running the plan's tests efficiently every night.

## Grounded in these DVCon papers

- **Verification Plan in Requirements Management Tool: Simple Traceability and Automated Interface to Regression Manager** (2024, DVCon US) — Jan Kreisinger and Sanjay Chatterjee. Co-locates plan and requirements in Jama Connect for automated regression generation.
- **Best Practices in Verification Planning** (2013, DVCon US) — Benjamin Ehlers, Carmen Vargas and Paul Carzola. A codified, executable verification planning methodology.
- **SIGMA: Sign-off Intelligence with GenAI for Methodical Assurance in Formal Verification** (2026, DVCon US) — R C Sanjay Krushnan, Moola Jeevan Chaitanya Goud and Sakthivel Ramaiah. GenAI-augmented formal sign-off flow that automates plan and claim authoring.
- **An Early Stage Coverage Measurement Methodology For Common Features Of System-On-Chip Verification, Using Design Metadata And Large Language Models** (2025, DVCon US) — Myeongwhan Hyun, Jaehyeok Lee and Jin Choi. LLM-derived Common Task Coverage bins measured pre-simulation.
- **Leveraging more from GLS: Using metric driven GLS stimuli to boost Timing Verification** (2018, DVCon US) — Sowmya Ega, Richardson Jeyapaul and Kunal Jani. MDV applied to gate-level stimuli quality and timing verification.
- **Use Stimulus Domain for Systematic Exploration of Time Dimension and Automatic Testcase Construction** (2018, DVCon Europe) — Ning Chen and Martin Ruhwandl. Stimulus-domain modeling to objectively assess randomization quality.
- **Multi-Variant Coverage: Effective Planning and Modelling** (2018, DVCon Europe) — Vikas Sharma and Manoj Manu. Reusable multi-variant coverage model for differing verification intents.
- **A Metric-driven Methodology For Firmware Verification** (2016, DVCon Europe) — Goran Savić. MDV for on-die firmware using SystemVerilog and free tooling.
- **Enhancements of metric driven verification for the ISO26262** (2016, DVCon Europe) — Michael Rohleder, Clemens Röttgermann and Stephan Rüttiger. Combining MDV methods for functional-safety devices.
- **Connecting Enterprise Applications to Metric Driven Verification** (2014, DVCon Europe) — Matt Graham. Integrating defect tracking, requirements, and source control with MDV data.
- **Metric Driven Mixed-Signal Verification Methodology and Practices for Complex Mixed-signal ASSPs** (2014, DVCon US) — Frank Yang, Andy Sha and Morton Zhao. MDV extended to mixed-signal ASSPs.
- **Digitizing Mixed Signal Verification** (2014, DVCon US) — David Brownell and Courtney Schmitt. Applying digital MDV techniques to AMS blocks.
- **Plan & Metric Driven Mixed-Signal Verification for Medical Devices** (2011, DVCon US) — Gregg Sarkinen. Plan- and metric-driven verification of a mixed-signal medical IC.
- **Metric Driven Verification of Mixed-Signal Designs** (2011, DVCon US) — Neyaz Khan, Yaron Kashai and Hao Fang. MDV methodology scaling from IP to SoC for mixed-signal.

---

*Part of the [DVCon LLM Wiki](index.md). Synthesized from 1,852 DVCon papers (2010–2026).*
