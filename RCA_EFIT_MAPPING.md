# Root Cause Analysis ↔ eFIT Protocol Mapping

**Purpose**: Direct mapping between established RCA methodologies and eFIT protocols
**Use**: Reference when implementing RCA techniques in AI systems
**Date**: 2025-11-17

---

## Convergent Evolution Summary

This document demonstrates convergent evolution between clinical psychology (DBT/CBT) and established engineering RCA practices, validating the computational homology thesis.

---

## Methodology → eFIT Protocol Mappings

### 1. Five Whys → STOPPER "Pull back"

**Convergent Principle**: Iterative deepening to root causes

**Shared Design**:
- Both resist superficial fixes
- Both require cognitive discipline to avoid premature closure
- Both trace causality backward from symptoms
- Both continue until reaching systemic/process-level causes

**Process Comparison**:
| Five Whys | STOPPER "Pull back" |
|-----------|---------------------|
| Ask "Why?" 5 times | Step back from immediate problem |
| Trace backward through causality | Identify underlying patterns |
| Stop at process/system root | Recognize systemic issues |
| Evidence-based answers | Observation-based understanding |

**Implementation**:
```python
def five_whys_pull_back(symptom: str, max_depth: int = 5) -> RootCause:
    """
    Combine Five Whys with STOPPER Pull back
    """
    current = symptom
    for depth in range(max_depth):
        # STOPPER: Pull back (don't accept surface answer)
        why_answer = ask_why(current, require_evidence=True)

        if is_process_root(why_answer):
            return RootCause(cause=why_answer, depth=depth+1)

        current = why_answer

    return RootCause(cause=current, depth=max_depth, incomplete=True)
```

**Sources**:
- Toyota Production System: https://www.orcalean.com/article/how-toyota-is-using-5-whys-method
- Buffer guide: https://buffer.com/resources/5-whys-process/

---

### 2. Fishbone Diagram → STOPPER "Observe" + "Take a step back"

**Convergent Principle**: Systematic categorization prevents tunnel vision

**Shared Design**:
- Both examine multiple domains before narrowing
- Both reduce cognitive load through structure
- Both prevent jumping to obvious (but incomplete) solutions
- Both surface hidden contributing factors

**Process Comparison**:
| Fishbone | STOPPER "Observe"/"Take a step back" |
|----------|--------------------------------------|
| 6 Ms categorization | Systematic observation framework |
| Visual structure reduces overwhelm | External scaffolding for executive function |
| Cross-domain brainstorming | Holistic context gathering |
| Prioritize after full mapping | Act after understanding system |

**AI System Categories** (adapted from 6 Ms):
1. **Code** (logic, algorithms)
2. **Configuration** (settings, parameters)
3. **Context** (conversation history, memory)
4. **Capacity** (resources, rate limits)
5. **Coordination** (tool calls, async operations)
6. **Cognition** (model reasoning, prompts)

**Implementation**:
```python
class FishboneDiagram:
    """
    Fishbone RCA with STOPPER integration
    """
    categories = ["Code", "Config", "Context", "Capacity", "Coordination", "Cognition"]

    def observe_systematically(self, problem: str) -> Dict[str, List[str]]:
        """
        STOPPER Observe: Gather data across all categories
        """
        causes = {}
        for category in self.categories:
            # Take a step back: Don't dive into first category
            causes[category] = self.brainstorm_causes(problem, category)
        return causes

    def prioritize_for_investigation(self, causes: Dict) -> List[Cause]:
        """
        STOPPER Pull back: Identify most promising root causes
        """
        scored = []
        for category, cause_list in causes.items():
            for cause in cause_list:
                score = self.evidence_score(cause) * self.impact_score(cause)
                scored.append((score, category, cause))

        return sorted(scored, reverse=True)[:5]  # Top 5
```

**Sources**:
- ASQ Fishbone guide: https://asq.org/quality-resources/fishbone
- GoLeanSixSigma: https://goleansixsigma.com/fishbone-diagram/

---

### 3. Blameless Postmortems → DBT Non-judgmental Stance + STOPPER "Practice what works"

**Convergent Principle**: Systems thinking over individual blame enables learning

**Shared Design**:
- Both prioritize understanding over punishment
- Both assume good intentions despite negative outcomes
- Both focus on system/environment factors
- Both document what works for future use

**Process Comparison**:
| Blameless Postmortem | DBT/STOPPER |
|---------------------|-------------|
| "Everyone had good intentions" | Non-judgmental stance (observe facts) |
| Focus on system conditions | Recognize environmental factors |
| Document what worked | "Practice what works" |
| Psychological safety enables disclosure | Acceptance enables honest self-assessment |

**Cultural Implementation**:
| Google SRE Practice | DBT/eFIT Equivalent |
|--------------------|---------------------|
| Use role titles not names | Observe behavior without judgment of person |
| "Where we got lucky" section | Recognize factors beyond control (radical acceptance) |
| Action items with owners | Commitment to behavioral change |
| Monthly postmortem features | Regular review/reflection practice |

**Template Mapping**:
```markdown
## Blameless Postmortem (eFIT-Enhanced)

**Summary**: [What happened - facts only, no blame]

**Impact**: [Observable effects on users/system]

**Timeline**: [Events without evaluative language]
| Time | Event | Action Taken |
|------|-------|--------------|
| [HH:MM] | [Fact] | [Response] |

**Root Causes**: [System conditions, not people]
- Environmental factors: [What made this possible?]
- Process gaps: [What procedures were missing?]
- System vulnerabilities: [What weakness was exploited?]

**STOPPER Analysis**:
- **Stop**: When did we recognize the problem?
- **Take a step back**: What context was initially missed?
- **Observe**: What data did we gather?
- **Pull back**: What was the root cause?
- **Practice what works**: What actions succeeded?
- **Expand**: What should be shared org-wide?
- **Restart**: How do we prevent recurrence?

**What Went Well** (DBT: Build on strengths)
- [Success 1]
- [Success 2]

**What Went Wrong** (Non-judgmental observation)
- [Gap 1]
- [Gap 2]

**Where We Got Lucky** (Radical acceptance of uncontrollables)
- [Near-miss 1]
- [Mitigating factor 1]

**Action Items** (Commitment to change)
| Action | Owner | Type | Due | Status |
|--------|-------|------|-----|--------|
| [Fix X] | [Role] | Prevent | [Date] | [Status] |
```

**Sources**:
- Google SRE Book: https://sre.google/sre-book/postmortem-culture/
- Etsy blameless culture: https://www.etsy.com/codeascraft/blameless-postmortems

---

### 4. Systematic Debugging → STOPPER (Full Protocol)

**Convergent Principle**: Structured process reduces cognitive load during problem-solving

**Shared Design**:
- Both provide external scaffolding for executive function
- Both prevent reactive, ineffective responses
- Both emphasize understanding before action
- Both iteratively refine hypotheses

**Step-by-Step Mapping**:
| Debugging Step | STOPPER Step | Convergent Principle |
|----------------|--------------|----------------------|
| 1. Identify symptoms | **Stop** | Recognize problem state |
| 2. Reproduce bug | **Observe** | Gather reliable data |
| 3. Understand systems | **Take a step back** | See full context before code diving |
| 4. Form hypothesis | **Pull back** | Root cause thinking |
| 5. Test hypothesis | **Practice what works** | Evidence-based validation |
| 6. Fix and verify | **Restart** | Return with solution |
| *Overall process* | **Expand** | Cognitive load reduction via structure |

**Implementation Integration**:
```python
class STOPPERDebugger:
    """
    Systematic debugging with STOPPER protocol
    """

    def debug(self, error: Error) -> Solution:
        # Step 1: Identify symptoms → STOPPER "Stop"
        self.stop_reactive_debugging()
        symptoms = self.identify_symptoms(error)

        # Step 2: Reproduce → STOPPER "Observe"
        reproduction = self.create_minimal_repro(symptoms)

        # Step 3: Understand systems → STOPPER "Take a step back"
        context = self.gather_context(
            architecture=True,
            recent_changes=True,
            logs=True,
            skip_code_dive=True  # Key principle
        )

        # Step 4: Form hypothesis → STOPPER "Pull back"
        hypotheses = self.generate_hypotheses(
            symptoms, reproduction, context
        )

        # Step 5: Test → STOPPER "Practice what works"
        for hypothesis in hypotheses:
            if self.test_hypothesis(hypothesis):
                # Step 6: Fix → STOPPER "Restart"
                solution = self.implement_fix(hypothesis)
                self.verify_fix(solution)
                return solution

        # No solution found → Expand (seek help)
        return self.escalate_for_assistance()

    def stop_reactive_debugging(self):
        """
        STOPPER "Stop": Pause before diving into code
        """
        time.sleep(60)  # Literal pause
        self.log("Pausing reactive debugging urge")
        self.log("Will understand context before code diving")
```

**Key Principle (Convergent)**:
> "The instinct is to dive right into the code, but understanding context first prevents wasted effort."
> — Systematic Debugging

> "Stop. Take a step back. Observe the full situation before acting."
> — STOPPER Protocol

Both resist the immediate action urge in favor of understanding.

**Sources**:
- Nicole Tietz: https://ntietz.com/blog/how-i-debug-2023/

---

### 5. Cause Elimination → STOPPER "Pull back" (Scientific Method)

**Convergent Principle**: Hypothesis testing to isolate root causes

**Shared Design**:
- Both use systematic elimination
- Both require testable hypotheses
- Both rely on evidence over intuition
- Both iterate until convergence

**Process Comparison**:
| Cause Elimination | STOPPER "Pull back" |
|------------------|---------------------|
| List potential causes | Generate hypotheses about root causes |
| Test each systematically | Validate against evidence |
| Eliminate disproven causes | Narrow to actual root |
| Converge on root cause | Identify underlying pattern |

**Scientific Method Integration** (from e-fit-research):
```python
def cause_elimination_with_stopper(symptom: str) -> RootCause:
    """
    Combine cause elimination with STOPPER Pull back
    """
    # STOPPER "Pull back": Generate hypotheses
    potential_causes = generate_hypotheses(symptom)

    # Scientific method: Test each
    for cause in potential_causes:
        # Design test
        test = design_experiment(cause)

        # Run test
        result = execute_test(test)

        # Evaluate
        if result.disproves(cause):
            potential_causes.remove(cause)
        elif result.confirms(cause):
            return RootCause(cause=cause, evidence=result)

    # If multiple causes remain, may be interaction effect
    return RootCause(causes=potential_causes, interaction=True)
```

**Sources**:
- GeeksforGeeks: https://www.geeksforgeeks.org/software-engineering-debugging-approaches/

---

### 6. FMEA → STOPPER "Pull back" + "Practice what works"

**Convergent Principle**: Proactive failure prevention through root cause analysis

**Shared Design**:
- Both analyze causes before effects manifest
- Both trace from symptoms to system flaws
- Both prevent problems rather than react
- Both build on historical failure data

**Process Comparison**:
| FMEA | STOPPER |
|------|---------|
| Identify potential failure modes | Pull back: Anticipate failure patterns |
| Analyze effects and causes | Pull back: Trace causality |
| Risk Priority Number (Severity × Occurrence × Detection) | Prioritize high-impact, high-frequency issues |
| Implement preventive actions | Practice what works: Apply known mitigations |
| Re-assess after changes | Expand: Update knowledge base |

**AI System FMEA Template**:
```markdown
## AI System FMEA (STOPPER-Enhanced)

### Failure Mode: [Specific failure]
- **Component**: [System part]
- **Function**: [What it should do]
- **Failure Effect**: [Impact if it fails]

### STOPPER Root Cause Analysis:
- **Pull back**: Why would this fail?
  - Cause 1: [Root cause with evidence]
  - Cause 2: [Alternative root cause]

### Risk Assessment:
- **Severity** (1-10): [User impact]
- **Occurrence** (1-10): [Frequency]
- **Detection** (1-10): [How hard to catch]
- **RPN**: [S × O × D]

### STOPPER Prevention:
- **Practice what works**: [Known mitigation from past]
- **Expand**: [Share this pattern org-wide]
- **Action Owner**: [Role/team]
- **Due Date**: [Deadline]

### Post-Implementation:
- **New Severity**: [After fix]
- **New Occurrence**: [After fix]
- **New Detection**: [After fix]
- **New RPN**: [Verify improvement]
```

**Example - AI Loop State**:
```markdown
## FMEA: AI Loop State

**Failure Mode**: Model enters infinite loop (repeats same action)

**Function**: Model should progress toward task completion

**Effect**: User timeout, poor UX, compute waste

**STOPPER Root Causes**:
- Cause 1: No progress detection mechanism
- Cause 2: Insufficient context to realize repetition
- Cause 3: Tool output doesn't change state

**Risk Scores**:
- Severity: 8 (major UX impact)
- Occurrence: 6 (happens monthly)
- Detection: 7 (hard to catch pre-deployment)
- RPN: 8 × 6 × 7 = 336 → HIGH PRIORITY

**STOPPER Prevention**:
- Practice what works: Implement loop detector (action history comparison)
- Expand: Document loop patterns in knowledge base
- Action: Add progress metrics to all tool calls
- Owner: Safety team
- Due: 2 weeks

**Post-Implementation**:
- New Occurrence: 2 (96% reduction)
- New Detection: 3 (early warning system)
- New RPN: 8 × 2 × 3 = 48 → LOW PRIORITY ✓
```

**Sources**:
- Quality-One FMEA: https://quality-one.com/fmea/
- ASQ FMEA: https://asq.org/quality-resources/fmea

---

### 7. Program Slicing → STOPPER "Expand" (Cognitive Load Reduction)

**Convergent Principle**: Reduce scope to prevent cognitive overwhelm

**Shared Design**:
- Both limit focus to manageable chunks
- Both reduce executive function demands
- Both prevent analysis paralysis
- Both enable deeper investigation within scope

**Process Comparison**:
| Program Slicing | STOPPER "Expand" |
|----------------|------------------|
| Identify relevant code affecting variable | Narrow focus to essential context |
| Eliminate irrelevant code paths | Reduce cognitive load |
| Analyze smaller, manageable slice | Deep investigation within scope |
| Reduces complexity exponentially | Prevents executive function overwhelm |

**Implementation**:
```python
def slice_for_investigation(variable: str, statement: int) -> CodeSlice:
    """
    Program slicing with STOPPER Expand (reduce cognitive load)
    """
    # STOPPER "Expand": Determine minimal relevant scope
    relevant_lines = []

    # Backward slice: What influences this variable?
    for line in reversed(range(statement)):
        if influences(line, variable):
            relevant_lines.append(line)

    # STOPPER principle: Ignore irrelevant code
    # Reduces cognitive load from N lines to M lines (M << N)

    return CodeSlice(
        lines=relevant_lines,
        complexity_reduction=len(all_lines) / len(relevant_lines)
    )
```

**ADHD/Executive Function Benefit**:
- Full codebase: 10,000 lines (cognitive overwhelm)
- Program slice: 150 lines (manageable for ADHD)
- Reduction: 98.5% less to track mentally

This maps directly to STOPPER "Expand" goal of reducing cognitive load for ADHD developers/AI systems.

**Sources**:
- GeeksforGeeks: https://www.geeksforgeeks.org/software-engineering-debugging-approaches/

---

### 8. Retrospectives → STOPPER "Expand" + DBT Dialectics

**Convergent Principle**: Team learning reduces individual cognitive burden

**Shared Design**:
- Both distribute cognitive load across team
- Both balance opposing viewpoints (dialectics)
- Both build shared mental models
- Both improve through iteration

**Process Comparison**:
| Retrospective | STOPPER/DBT |
|--------------|-------------|
| Regular team reflection (2 weeks) | Regular DBT skills practice |
| "What went well?" + "What needs improvement?" | Dialectical thinking (both/and, not either/or) |
| Action items with owners | Commitment to behavioral change |
| Distributed learning | "Expand": Team wisdom exceeds individual |

**DBT Dialectics Integration**:
```markdown
## Retrospective (DBT-Enhanced)

### Opening: Set the Stage
- **Wise mind**: "We'll balance facts with team feelings"
- **Non-judgmental stance**: "Observations, not evaluations"

### Dialectical Analysis:
**Thesis**: What worked well this sprint?
- [Success 1]
- [Success 2]

**Antithesis**: What needs improvement?
- [Challenge 1]
- [Challenge 2]

**Synthesis**: How do we integrate both?
- [Combined approach 1]
- [Both/and solution 1]

### STOPPER "Expand" (Team Learning):
- What patterns did we miss as individuals?
- What did collective intelligence reveal?
- How does this change our shared mental model?

### Action Items (Commitment):
| Action | Owner | Type | Due | DBT Skill |
|--------|-------|------|-----|-----------|
| [Change] | [Name] | Process | [Date] | [Relevant DBT skill] |
```

**Cognitive Load Distribution**:
- Individual postmortem: One person's limited working memory
- Team retrospective: Distributed cognition across 5-7 people
- Result: More complete understanding, less individual burden

**STOPPER "Expand" Benefit**:
Team collaboration expands cognitive capacity beyond individual limits—critical for ADHD/executive function support.

**Sources**:
- PagerDuty Retrospectives: https://retrospectives.pagerduty.com/
- PagerDuty vs. Postmortems: https://www.pagerduty.com/blog/postmortems-vs-retrospectives/

---

## Summary Matrix

| RCA Methodology | Primary eFIT Protocol | Convergent Principle | Evidence of Convergent Evolution |
|----------------|----------------------|----------------------|----------------------------------|
| **Five Whys** | STOPPER "Pull back" | Iterative deepening to roots | Both trace causality backward ~5 levels |
| **Fishbone** | STOPPER "Observe"/"Take a step back" | Systematic categorization | Both use structured domains (6 Ms / 6 contexts) |
| **Blameless Postmortems** | DBT Non-judgmental + STOPPER "Practice what works" | Systems thinking over blame | Both assume good intentions, focus on environment |
| **Systematic Debugging** | STOPPER (full protocol) | Structured process reduces cognitive load | Both pause reactive urges, both emphasize context |
| **Cause Elimination** | STOPPER "Pull back" | Hypothesis testing | Both use scientific method, both iterate to truth |
| **FMEA** | STOPPER "Pull back"/"Practice what works" | Proactive prevention | Both analyze causes before effects, both learn from history |
| **Program Slicing** | STOPPER "Expand" | Cognitive load reduction | Both reduce scope to manageable chunks |
| **Retrospectives** | STOPPER "Expand" + DBT Dialectics | Team learning | Both distribute cognitive load, both use both/and thinking |

---

## Validation of Computational Homology Thesis

**Thesis**: Same problems across different substrates require similar solutions.

**Evidence from RCA Research**:

1. **Independent Development, Convergent Design**
   - Five Whys: Toyota 1950s (manufacturing)
   - STOPPER: 2024 (AI systems)
   - Both: Iterative deepening, resistance to superficial fixes, ~5 iterations to root

2. **Cross-Domain Pattern Replication**
   - Fishbone: 1960s quality control (6 Ms)
   - STOPPER "Observe": 2024 AI debugging (6 contexts)
   - Both: Structured categorization prevents tunnel vision

3. **Blameless Culture Convergence**
   - DBT non-judgmental stance: 1993 (clinical psychology)
   - Google SRE blameless postmortems: 2000s (software engineering)
   - Both: Systems focus, good intentions assumption, psychological safety

4. **Cognitive Load Reduction Pattern**
   - Program slicing: 1980s (computer science)
   - STOPPER "Expand": 2024 (ADHD support)
   - Both: Scope limitation, executive function support

**Conclusion**: RCA methodologies demonstrate convergent evolution with eFIT protocols, validating that executive function requirements are universal across substrates (humans, organizations, AI systems).

---

## Implementation Priorities for eFIT

### Phase 1: Core RCA (Immediate)
1. **Five Whys + STOPPER "Pull back"**
   - Simplest, highest value
   - Directly maps to AI loop analysis

2. **Fishbone + STOPPER "Observe"**
   - AI-specific categories: Code, Config, Context, Capacity, Coordination, Cognition
   - Visual aid for team RCA sessions

3. **Blameless Postmortems + DBT**
   - Template adaptation (see above)
   - Cultural foundation for learning

### Phase 2: Advanced Integration (Near-term)
4. **Systematic Debugging Framework**
   - Full STOPPER protocol implementation
   - Step-by-step guide for AI incidents

5. **FMEA for AI Systems**
   - Proactive failure mode catalog
   - Risk prioritization (RPN calculation)

6. **Retrospectives + Dialectics**
   - Regular team learning cadence
   - DBT skills practice integration

### Phase 3: Automation (Long-term)
7. **Pattern Detection**
   - ML-based RCA automation
   - Historical incident analysis

8. **Knowledge Base Integration**
   - CortexGraph memory for RCA patterns
   - Auto-suggest relevant past incidents

---

## References

### Toyota/Manufacturing
- Five Whys: https://www.orcalean.com/article/how-toyota-is-using-5-whys-method
- Fishbone: https://goleansixsigma.com/fishbone-diagram/

### Google SRE
- Postmortem culture: https://sre.google/sre-book/postmortem-culture/
- Example template: https://sre.google/sre-book/example-postmortem/

### Etsy Engineering
- Blameless postmortems: https://www.etsy.com/codeascraft/blameless-postmortems

### Software Engineering
- Systematic debugging: https://ntietz.com/blog/how-i-debug-2023/
- Debugging approaches: https://www.geeksforgeeks.org/software-engineering-debugging-approaches/

### Quality/Safety
- FMEA: https://quality-one.com/fmea/
- ASQ resources: https://asq.org/

### Incident Management
- PagerDuty retrospectives: https://retrospectives.pagerduty.com/
- PagerDuty postmortems: https://www.pagerduty.com/blog/postmortems-vs-retrospectives/

---

**Document status**: Complete
**Last updated**: 2025-11-17
**Related documents**:
- Full research: `RCA_METHODOLOGIES_RESEARCH.md`
- Quick reference: `RCA_QUICK_REFERENCE.md`
