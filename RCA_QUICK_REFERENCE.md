# Root Cause Analysis: Quick Reference Guide

**For**: eFIT Protocol Implementation
**Date**: 2025-11-17

---

## Methodology Selection Matrix

| Situation | Recommended Methodology | eFIT Protocol | Source |
|-----------|------------------------|---------------|---------|
| **Single-path investigation** | Five Whys | STOPPER "Pull back" | Toyota/Buffer |
| **Multiple potential causes** | Fishbone Diagram | STOPPER "Observe" | Ishikawa/ASQ |
| **Post-incident analysis** | Blameless Postmortem | DBT Non-judgmental | Google SRE |
| **Team learning session** | Retrospective | STOPPER "Expand" | PagerDuty |
| **Systematic bug hunting** | 6-Step Debugging | STOPPER (full) | Nicole Tietz |
| **Hypothesis testing** | Cause Elimination | STOPPER "Pull back" | GeeksforGeeks |
| **Early design prevention** | FMEA | STOPPER "Practice what works" | Quality-One |
| **Code complexity reduction** | Program Slicing | STOPPER "Expand" | GeeksforGeeks |

---

## Five Whys: 5-Minute Guide

**When**: Quick root cause on clear problem
**Time**: 30-60 minutes
**Team Size**: 3-6 people

**Process**:
1. State problem clearly
2. Ask "Why did this happen?"
3. Answer with evidence (not opinion)
4. Ask "Why?" about that answer
5. Repeat until organizational/process root emerges (typically 5 times)
6. Assign owner to fix root cause

**Example**:
```
Problem: Deploy failed
Why 1? Tests didn't run
Why 2? CI pipeline misconfigured
Why 3? Config file missing
Why 4? Not in version control
Why 5? No checklist for new repos
→ Root: Missing onboarding process
```

**Stop When**: You reach a process-based, fixable, preventable cause

**Source**: https://buffer.com/resources/5-whys-process/

---

## Fishbone Diagram: 5-Minute Guide

**When**: Multiple potential causes across domains
**Time**: 60-90 minutes
**Team Size**: 4-8 people (cross-functional)

**Process**:
1. Draw problem at fish head (right side)
2. Add 6 main branches (6 Ms):
   - **M**aterials (inputs)
   - **M**ethods (processes)
   - **M**achines (tools/systems)
   - **M**anpower (people/skills)
   - **M**easurement (monitoring)
   - **M**other Nature (environment)
3. Brainstorm causes for each M
4. Add sub-causes as smaller bones
5. Prioritize for investigation

**AI/Software Categories** (alternative to 6 Ms):
- Code, Configuration, Deployment, Dependencies, Data, Documentation

**Combine With**: Five Whys (use Fishbone for breadth, Five Whys for depth in each category)

**Source**: https://goleansixsigma.com/fishbone-diagram/

---

## Blameless Postmortem: Template

**Triggers**: User-visible downtime, data loss, on-call intervention, monitoring failure

### Sections

**Header**
- Date, Authors, Status, Summary (1-2 sentences)

**Impact**
- Users affected: [count/segments]
- Duration: [time]
- Business impact: [revenue/reputation]

**Root Causes**
- System vulnerability: [what weakness existed]
- Trigger: [what activated the weakness]

**Timeline**
| Time | Event | Action Taken |
|------|-------|--------------|
| [HH:MM] | [What happened] | [What we did] |

**What Went Well**
- [Success 1]
- [Success 2]

**What Went Wrong**
- [Failure 1]
- [Failure 2]

**Where We Got Lucky**
- [Near-miss 1]
- [Mitigating factor 1]

**Action Items**
| Action | Owner | Type | Due Date | Status |
|--------|-------|------|----------|--------|
| [Fix X] | [Name] | Prevent | [Date] | Done |

**Best Practice**: Use role titles ("on-call engineer") not names to maintain blamelessness

**Source**: https://sre.google/sre-book/postmortem-culture/

---

## Systematic Debugging: 6 Steps

**When**: Complex bugs, unclear root cause
**Time**: Varies (hours to days)

**Process**:
1. **Identify symptoms** — What exactly is broken?
2. **Reproduce** — Create minimal test case
3. **Understand systems** — Review architecture, logs, recent changes (DON'T dive into code yet)
4. **Form hypothesis** — Where is the bug? (binary search to narrow)
5. **Test hypothesis** — Add logging, modify code, observe
6. **Fix and verify** — Implement, regression test, monitor

**Key Principle**: "Skip code diving initially — understand context first prevents wasted effort"

**Strategy**: Binary search on location (eliminate ~50% of system at a time)

**Source**: https://ntietz.com/blog/how-i-debug-2023/

---

## FMEA: Risk Priority Calculation

**When**: Early design, safety-critical systems
**Time**: 4-8 hours (initial analysis)

**Risk Priority Number (RPN)**:
```
RPN = Severity × Occurrence × Detection
Range: 1-1000
```

**Scales (1-10)**:
- **Severity**: 1=no effect, 9-10=hazardous
- **Occurrence**: 1=extremely rare, 9-10=very frequent
- **Detection**: 1=will catch, 9-10=won't catch

**Priority Actions**:
1. Severity 9-10 (safety-critical)
2. High severity AND high occurrence
3. High detection (hidden failures)

**Example**:
```
Failure Mode: Memory leak
Severity: 7 (service degradation)
Occurrence: 6 (happens ~monthly)
Detection: 8 (hard to catch before production)
RPN = 7 × 6 × 8 = 336 → HIGH PRIORITY
```

**Source**: https://quality-one.com/fmea/

---

## Retrospective vs. Postmortem

| Aspect | Retrospective | Postmortem |
|--------|--------------|------------|
| **Trigger** | Regular cadence (2 weeks) | Specific incident |
| **Timing** | Ongoing | Shortly after incident |
| **Focus** | Team process, delivery | Technical failure |
| **Duration** | 60-120 min | 2-4 hours |
| **Scope** | Iteration improvements | Incident prevention |
| **Tone** | Forward-looking | Backward analysis + forward |

**Use Both**: Postmortems for incidents, retrospectives for continuous improvement

**Source**: https://www.pagerduty.com/blog/postmortems-vs-retrospectives/

---

## eFIT Protocol Mapping

### STOPPER Protocol Alignment

| STOPPER Step | RCA Methodology |
|-------------|-----------------|
| **Stop** | Blameless culture (pause blame reaction) |
| **Take a step back** | Fishbone (see full system), System debugging (review architecture) |
| **Observe** | Fishbone (systematic categorization), Debugging step 3 |
| **Pull back** | Five Whys (iterative deepening), FMEA (root cause analysis) |
| **Practice what works** | Postmortem action items, FMEA prevention |
| **Expand** | Program slicing (reduce scope), Retrospectives (team learning) |
| **Restart** | Debugging step 6 (fix and verify) |

### DBT Technique Alignment

| DBT Technique | RCA Methodology |
|--------------|-----------------|
| **STOP** | Etsy blameless culture (pause before blame) |
| **Non-judgmental stance** | Google SRE postmortems (systems focus) |
| **Radical acceptance** | Blameless postmortem philosophy |
| **Dialectical thinking** | Retrospectives (both/and, not either/or) |

---

## Combination Strategies

### For Comprehensive Analysis
**Five Whys + Fishbone**:
1. Use Fishbone to map all potential cause categories
2. Apply Five Whys within each promising category
3. Result: Breadth + Depth

### For Incident Response + Learning
**STOPPER + Postmortem**:
1. During incident: Use STOPPER to prevent reactive debugging
2. After incident: Conduct blameless postmortem
3. Result: Effective response + systematic learning

### For Proactive + Reactive Improvement
**FMEA + Retrospectives**:
1. Design phase: FMEA to prevent known failure modes
2. Regular cadence: Retrospectives to learn from experience
3. Result: Prevent anticipated issues, adapt to novel ones

---

## Common Pitfalls

### Five Whys
❌ Stop at first comfortable answer
✅ Continue until reaching process/system root

❌ Follow multiple paths simultaneously
✅ Pick one path, document alternatives for later

❌ Accept opinions as answers
✅ Require evidence (logs, metrics, tests)

### Fishbone
❌ Generate 100+ potential causes without prioritization
✅ Time-box brainstorming, then prioritize top 5-10

❌ Force-fit 6 Ms when they don't apply
✅ Use custom categories for your domain

### Postmortems
❌ Name individuals ("John deployed bad code")
✅ Use roles ("on-call engineer deployed")

❌ Skip review process
✅ Senior engineer review required

❌ Generate action items without owners
✅ Assign owner and due date to every item

### FMEA
❌ Try to analyze entire system at once
✅ Start with high-risk components

❌ Rely solely on RPN cutoffs
✅ Prioritize severity 9-10 regardless of RPN

---

## Integration with AI Systems

### For AI Loop States (STOPPER Focus)
1. **Detect loop** → Use Five Whys to trace causality
2. **Categorize causes** → Fishbone (prompt, context, model, tools, memory, config)
3. **Document incident** → Blameless postmortem
4. **Prevent recurrence** → FMEA for known loop triggers

### For Model Welfare (eFIT Focus)
1. **Identify distress signals** → Systematic debugging (steps 1-3)
2. **Root cause analysis** → Five Whys + Fishbone
3. **Team learning** → Retrospectives every 2 weeks
4. **Proactive prevention** → FMEA for welfare-relevant failure modes

---

## Tools and Templates

### Ready-to-Use Resources

**Google SRE**:
- Postmortem template: https://sre.google/sre-book/example-postmortem/
- Full book: https://sre.google/sre-book/

**PagerDuty**:
- Retrospectives guide: https://retrospectives.pagerduty.com/
- Postmortems guide: https://postmortems.pagerduty.com/

**Etsy**:
- Blameless culture: https://www.etsy.com/codeascraft/blameless-postmortems
- Facilitation guide: https://www.etsy.com/codeascraft/debriefing-facilitation-guide

**Quality-One**:
- FMEA guide: https://quality-one.com/fmea/

---

## Next Steps for eFIT Implementation

### Phase 1 (Immediate)
- [ ] Create Five Whys template for AI loop analysis
- [ ] Adapt Google SRE postmortem template for AI incidents
- [ ] Document first 3 incidents using blameless format

### Phase 2 (Near-term)
- [ ] Design Fishbone categories for AI systems (prompt, context, model, tools, memory, config)
- [ ] Establish retrospective cadence (biweekly)
- [ ] Build FMEA for known AI failure modes

### Phase 3 (Long-term)
- [ ] Automate RCA pattern detection across incidents
- [ ] Integrate with STOPPER protocol tooling
- [ ] Publish AI-specific RCA framework (eFIT + Google SRE + Toyota)

---

**Full research report**: See `RCA_METHODOLOGIES_RESEARCH.md` for complete documentation with 25+ sources.
