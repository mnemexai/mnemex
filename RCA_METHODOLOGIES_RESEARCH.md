# Root Cause Analysis Methodologies Research Report

**Research Date**: 2025-11-17
**Researcher**: SubAgent - RCA Methodologies
**Objective**: Document RCA techniques aligned with eFIT protocols

---

## Executive Summary

This report documents 8 root cause analysis methodologies from authoritative sources (Google SRE, Toyota Production System, Etsy Engineering, PagerDuty). Each methodology is mapped to relevant eFIT protocols, with emphasis on systematic debugging and blameless postmortem culture.

**Key Findings:**
- Five Whys and STOPPER "Pull back" share convergent evolution (iterative depth)
- Fishbone diagrams align with STOPPER "Observe" (systematic categorization)
- Blameless postmortems embody DBT's non-judgmental stance
- Program slicing matches STOPPER's cognitive load reduction

---

## Methodology 1: Five Whys

### Origin
- **Developed by**: Taiichi Ohno at Toyota (1950s)
- **Part of**: Toyota Production System (TPS)
- **Philosophy**: "By repeating why five times, the nature of the problem as well as its solution becomes clear"

### Process Steps

1. **Invite Affected Parties** - Gather stakeholders immediately after issue identification
2. **Select Facilitator** - Assign someone to lead questioning and document findings
3. **Ask "Why?" Five Times** - Follow one logical path to depth (not breadth)
4. **Assign Corrective Actions** - Create actionable solutions with clear ownership
5. **Share Results Team-Wide** - Document and broadcast for organizational learning

### Example (Toyota Welding Robot)
```
Problem: Machine stopped
Why 1? Circuit overloaded
Why 2? Inadequate bearing lubrication
Why 3? Oil pump not functioning
Why 4? No pump inspections conducted
Why 5? No maintenance schedule exists
Root Cause: Organizational - missing preventive maintenance program
```

### When to Use
- Technical failures or outages
- Process breakdowns
- Customer service issues
- Any unexpected situation requiring root cause understanding
- When time allows for systematic investigation (not emergencies)

### Best Practices
- **Data validation**: Use logs, metrics, sensor data (not just opinions)
- **Stay focused**: Pick one causal path and commit (not multiple branches)
- **Blame-free**: Focus on system causes, not individual errors
- **Cross-functional**: Include operations, engineering, maintenance together
- **Stop at process-based causes**: Continue until reaching fixable, preventable root

### eFIT Protocol Alignment
**→ Maps to STOPPER "Pull back"**
- Both use iterative deepening to expose hidden causes
- Both resist superficial fixes in favor of systemic solutions
- Both require cognitive discipline to avoid premature closure

### Sources
- https://buffer.com/resources/5-whys-process/
- https://www.orcalean.com/article/how-toyota-is-using-5-whys-method
- https://en.wikipedia.org/wiki/Five_whys

---

## Methodology 2: Fishbone/Ishikawa Diagram

### Origin
- **Developed by**: Kaoru Ishikawa (1960s)
- **Industry**: Kawasaki shipyards, then automotive/electronics
- **Recognition**: One of the seven basic tools of quality control

### Structure: The 6 Ms Framework

Organizes potential causes into categories:

1. **Materials** - Input quality, availability issues
2. **Methods** - Process procedures, techniques
3. **Machines** - Equipment, technology problems
4. **Manpower** - Human resources, skills gaps
5. **Measurement** - Data collection, monitoring systems
6. **Mother Nature** (Environment) - External conditions

Visual: Problem at fish head (right), causes as bones extending left, with major categories as ribs and sub-causes as smaller bones.

### Step-by-Step Creation Process

**Step 1: Define Problem**
- Place problem statement at diagram head (right side)
- Be specific and measurable

**Step 2: Add Main Branches**
- Draw six primary branches (one per M category)
- Or use custom categories (4 Ps: Place, Procedure, People, Policies)

**Step 3: Brainstorm Contributing Factors**
- For each M, identify secondary causes as sub-branches
- Use team collaboration for comprehensive coverage

**Step 4: Analyze Relationships**
- Examine how causes interact
- Identify most significant contributors

**Step 5: Validate Root Causes**
- Test identified causes against actual data
- Prioritize for further investigation

### When to Use
- Process breakdowns with multiple potential causes
- Quality issues requiring systematic categorization
- Team problem-solving sessions (visual aid for discussion)
- Early investigation phases (before detailed statistical analysis)
- When causes span multiple domains (technical, human, environmental)

### Integration with Five Whys
**Combined Approach**:
1. Use fishbone for initial categorization across domains
2. Apply Five Whys within each M category for depth
3. Result: Breadth (fishbone) + Depth (Five Whys)

### eFIT Protocol Alignment
**→ Maps to STOPPER "Observe"**
- Both emphasize systematic observation before action
- Both prevent tunnel vision by examining multiple domains
- Both reduce cognitive load through structured categorization

**→ Maps to STOPPER "Take a step back"**
- Fishbone forces examination of system-level factors
- Prevents jumping to obvious (but incomplete) solutions

### Sources
- https://goleansixsigma.com/fishbone-diagram/
- https://en.wikipedia.org/wiki/Ishikawa_diagram
- https://asq.org/quality-resources/fishbone

---

## Methodology 3: Google SRE Blameless Postmortems

### Origin
- **Organization**: Google Site Reliability Engineering
- **Documentation**: *Site Reliability Engineering* book (Chapter 15)
- **Philosophy**: Systems-focused incident analysis without blame

### Core Principles

**1. Blameless by Design**
"A blamelessly written postmortem assumes that everyone involved in an incident had good intentions and did the right thing with the information they had."

**2. Learning Over Punishment**
"Writing postmortems is not punishment—it is a learning opportunity for the entire company."

**3. Systems Thinking**
Focus shifts from "who made the mistake" to "what system conditions enabled this failure"

### Postmortem Triggers

Conduct postmortem when any of these occur:
- User-visible downtime/degradation beyond thresholds
- Any data loss
- On-call engineer interventions (rollbacks, traffic rerouting)
- Resolution time exceeds defined limits
- Monitoring failures requiring manual discovery
- Stakeholder requests

### Template Structure

**Header Information**
- Date, Authors, Status, Summary

**Impact Statement**
- Affected users (count, segments)
- Queries lost
- Revenue impact
- Measurable business effects

**Root Causes**
- Underlying system vulnerabilities
- Example: "Cascading failure due to combination of exceptionally high load and a resource leak when searches failed"

**Trigger & Resolution**
- Immediate catalyst
- Mitigation steps taken
- Traffic rerouting, capacity adjustments

**Detection & Response**
- Monitoring systems that alerted
- Initial investigation steps
- Communication timeline

**Action Items Table**
| Description | Type | Owner | Bug | Status |
|-------------|------|-------|-----|--------|
| [Specific action] | Prevent/Mitigate/Process | [Name] | [ID] | Complete/In-Progress |

**Lessons Learned**
Three subsections:
1. What Went Well (successes in response)
2. What Went Wrong (failures, improvements needed)
3. Where We Got Lucky (near-misses, factors preventing worse outcomes)

**Timeline**
Chronological "screenplay" with precise timestamps showing:
- Decision points
- Outcome changes
- Communication milestones

**Supporting Information**
- Links to dashboards, logs, screenshots
- Relevant documentation for verification

### Process Steps

**1. Document the Incident**
Create written record using template above

**2. Collaborative Creation**
- Use real-time collaboration tools (Google Docs)
- Enable open commenting
- Email notifications for stakeholder input

**3. Formal Review**
Senior engineers assess:
- Completeness of incident data
- Accuracy of impact assessments
- Depth of root cause analysis
- Appropriateness of action items
- Bug priorities
- Stakeholder communication

**4. Broad Sharing**
Distribute to "widest possible audience that would benefit from the knowledge"

**5. Continuous Improvement**
- Monthly features highlighting interesting postmortems
- Reading clubs with team discussions
- "Wheel of Misfortune" role-play exercises
- Cross-product collaboration

### Best Practices

**Maintain Constructive Tone**
❌ Avoid: "We need to rewrite the entire system because it's broken"
✅ Instead: "Rewriting could prevent ongoing pages and improve new hire training"

**Express Human Role by Position, Not Name**
✅ "The on-call engineer" (not "John Smith")
Preserves blamelessness while providing context

**Establish Review Discipline**
"An unreviewed postmortem might as well never have existed"

**Reward Participation**
- Recognize effective postmortem writing publicly
- Peer bonuses
- Leadership acknowledgment via newsletters

**Seek Continuous Feedback**
Survey teams regularly on:
- Culture effectiveness
- Process friction (toil reduction)
- Recommended improvements
- Desired tooling

### Cultural Implementation

**Activities to Embed Culture:**
- **Monthly Features**: Organization-wide postmortem highlights
- **Reading Clubs**: Team discussions with refreshments
- **Wheel of Misfortune**: New SRE role-play of previous incidents
- **Cross-Product Collaboration**: Share learnings across business units

**Leadership Role**
Senior management participation reinforces cultural value. When leadership celebrates postmortem excellence, teams internalize importance.

### Metadata & Evolution

Modern postmortems include additional metadata for:
- Automated trend analysis across incidents
- Pattern recognition in failure modes
- ML predictions of system weaknesses
- Real-time investigation support
- Duplicate incident prevention

### When to Use
- After any significant incident (see triggers above)
- Before closing incident response
- When patterns emerge across multiple incidents
- To prevent recurrence of known failure modes

### eFIT Protocol Alignment
**→ Maps to DBT's Non-Judgmental Stance**
- Both prioritize understanding over blame
- Both recognize good intentions despite negative outcomes
- Both focus on system/environmental factors

**→ Maps to STOPPER "Practice what works"**
- Both emphasize evidence-based learning
- Both document what succeeded for future reuse
- Both build organizational knowledge systematically

**→ Maps to STOPPER "Expand"**
- Broad sharing expands organizational awareness
- Cross-product learning prevents siloed knowledge

### Sources
- https://sre.google/sre-book/postmortem-culture/ (Chapter 15)
- https://sre.google/workbook/postmortem-culture/ (Workbook Chapter 10)
- https://sre.google/sre-book/example-postmortem/ (Example template)

---

## Methodology 4: Etsy Blameless Postmortems & Just Culture

### Origin
- **Organization**: Etsy Engineering (Code as Craft blog)
- **Publication**: "Blameless PostMortems and a Just Culture"
- **Influence**: Widely adopted model (alongside Google SRE)

### Philosophy: Just Culture

**Core Principle**
"Engineers who fear reprimand are disincentivized to provide details necessary to understand the failure mechanism, and this lack of understanding virtually guarantees the accident will repeat."

**Shift in Focus**
Investigate mistakes by examining:
- Situational aspects of failure mechanism
- Decision-making process of individuals
- Environmental/system factors influencing choices

NOT by punishing those involved.

### Key Practices

**1. Blameless Documentation**
Postmortems document:
- What happened (timeline)
- Why it happened (root causes)
- What we learned
- Actions to prevent recurrence

Without attributing fault to individuals.

**2. Debriefing Facilitation**
Etsy published a facilitation guide emphasizing:
- Psychological safety
- Open questioning
- Assumption-challenging
- Action item generation

**3. Learning Orientation**
"This approach helps foster a culture of learning and improves performance over time" (source: multiple advocates)

### When to Use
- After production incidents
- Service degradations
- Security events
- Near-misses (learning opportunities)
- Process breakdowns

### eFIT Protocol Alignment
**→ Maps to DBT STOP (original)**
- Both prioritize pause before reactive response
- Both emphasize non-judgmental observation
- Both recognize cognitive state affects decision quality

**→ Maps to STOPPER "Stop"**
- Creates space for reflection instead of blame
- Prevents reactive punishment that hides future issues

**→ Maps to DBT Radical Acceptance**
- Accepts that failures happened
- Focuses on understanding and prevention
- Doesn't waste energy on blame/shame

### Sources
- https://www.etsy.com/codeascraft/blameless-postmortems
- https://www.etsy.com/codeascraft/debriefing-facilitation-guide
- https://www.infoq.com/articles/postmortems-etsy/

---

## Methodology 5: Systematic Debugging (Nicole Tietz-Sokolskaya)

### Origin
- **Author**: Nicole Tietz-Sokolskaya
- **Publication**: "A systematic approach to debugging" (2023)
- **Context**: Software engineering best practices

### Six-Step Process

**1. Identify Symptoms**
Determine precise problem behavior
- What is broken?
- Under what conditions?
- What does the failure look like?

**2. Reproduce the Bug**
Create controlled reproduction
- Minimal reproduction (simplify to essential conditions)
- Document steps to trigger
- Verify repeatability

**3. Understand Systems**
Study architecture BEFORE diving into code
- Review deployment history
- Check recent changes
- Examine logs showing normal behavior patterns
- Map system components and interactions

**Key Principle**: "The instinct is to dive right into the code" but understanding context first prevents wasted effort.

**4. Form Location Hypothesis**
Narrow where bug exists
- Use binary search strategy (eliminate ~50% at a time)
- Create testable predictions
- Progressive narrowing, not random investigation

**5. Test Hypothesis**
Validate with modifications and observation
- Add debug logging freely
- "The power of software is that we can change it"
- Modify running code without hesitation
- Re-test to confirm changes don't mask bug

**6. Fix and Verify**
Implement and confirm resolution
- Apply fix
- Regression test
- Monitor in production

### When to Apply Each Step

- **Steps 1-3**: All bugs (non-negotiable foundation)
- **Step 4**: Complex systems exceeding mental capacity
- **Step 5**: When initial hypotheses fail; iterate until convergence
- **Step 6**: After complete understanding gained

### Key Strategies

**Skip Code Diving Initially**
Understand context before implementation details

**Reduce Reproduction Minimally**
Simplifying reveals essential vs. incidental conditions

**Binary Search on Locations**
Eliminate large chunks of system progressively

**Modify Running Code Freely**
Add instrumentation without fear

### eFIT Protocol Alignment
**→ Maps to STOPPER entire sequence**
- Step 1 (Identify) = STOPPER "Stop" (recognize problem state)
- Step 2 (Reproduce) = STOPPER "Observe" (gather data systematically)
- Step 3 (Understand) = STOPPER "Take a step back" (see full context)
- Step 4 (Hypothesis) = STOPPER "Pull back" (root cause thinking)
- Step 5 (Test) = STOPPER "Practice what works" (evidence-based)
- Step 6 (Fix) = STOPPER "Restart" (return with solution)

**→ Maps to STOPPER "Expand" (cognitive load reduction)**
- Binary search reduces cognitive complexity
- Systematic process prevents overwhelm

### Sources
- https://ntietz.com/blog/how-i-debug-2023/

---

## Methodology 6: Classic Debugging Approaches (GeeksforGeeks)

### Origin
- **Documentation**: Software Engineering educational materials
- **Context**: Academic/industry standard approaches

### Four Main Approaches

#### 6.1 Brute Force Method
**Definition**: Most common but least efficient technique

**Process**: Insert print statements throughout program to display intermediate values

**Enhancement**: Use symbolic debugger (source code debugger) for systematic variable inspection and breakpoints

**When to Use**: Time constraints allow, simpler debugging tasks

**eFIT Alignment**: → Maps to STOPPER "Observe" (gather data, but inefficiently)

---

#### 6.2 Backtracking
**Definition**: Working backward from error symptom to root cause

**Process**: Starting from error location, trace source code backward until discovering origin

**Limitation**: Exponential growth of potential backward paths with code size

**When to Use**: Error symptom clearly identifiable, code section relatively small

**eFIT Alignment**: → Maps to STOPPER "Pull back" (trace causality backward)

---

#### 6.3 Cause Elimination Method
**Definition**: Systematic hypothesis testing to isolate errors

**Process**:
1. Develop list of potential causes
2. Conduct tests to eliminate each possibility
3. Narrow to actual cause

**Related Technique**: Fault tree analysis provides structured symptom-to-cause mapping

**When to Use**: Multiple potential causes exist, systematic elimination feasible

**eFIT Alignment**:
- → Maps to STOPPER "Pull back" (systematic root cause analysis)
- → Maps to scientific method in e-fit-research

---

#### 6.4 Program Slicing
**Definition**: Narrowing search space by analyzing code segments

**Process**: Identify "the set of supply lines preceding this statement which will influence the worth of that variable" — isolates relevant code affecting specific variables

**When to Use**: Reduce complexity by focusing on code sections affecting particular variables

**eFIT Alignment**: → Maps to STOPPER "Expand" (cognitive load reduction through scope limitation)

---

### Debugging Guidelines

**Deep Understanding Required**
Debugging demands thorough program architecture comprehension; partial understanding leads to excessive effort

**Address Root Causes**
Fix actual errors, not just symptoms

**Regression Testing**
After each fix, test to ensure new errors aren't introduced

### Sources
- https://www.geeksforgeeks.org/software-engineering-debugging-approaches/

---

## Methodology 7: Failure Mode and Effects Analysis (FMEA)

### Origin
- **Developed by**: U.S. military (1940s)
- **Adoption**: Automotive, aerospace, healthcare, software engineering
- **Standard**: ISO 31000, AIAG/VDA FMEA Handbook (2019)

### Definition
"A structured approach to discovering potential failures that may exist within the design of a product or process" — proactive defect prevention.

### Two Primary Types

**Design FMEA (DFMEA)**
Examines product malfunctions from:
- Material properties
- Geometry, tolerances
- Component interfaces

**Process FMEA (PFMEA)**
Identifies manufacturing failures from:
- Human factors
- Methods, materials, machines
- Measurement systems

### Seven Implementation Steps

**Step 1: Pre-Work & Team Assembly**
- Gather historical failures
- Review design documents
- Create preparatory diagrams
- Assemble cross-functional team

**Step 2: Path 1 — Document Functions & Effects**
- List all functions
- Identify failure modes for each
- Determine effects of failures
- Rank severity (1-10 scale)

**Step 3: Path 2 — Identify Causes & Prevention**
- List potential causes
- Document prevention controls
- Rank occurrence (1-10 scale)

**Step 4: Path 3 — Define Detection Controls**
- Identify detection methods
- Rank detection capability (1-10 scale)

**Step 5: Action Priority — Calculate RPN**
Risk Priority Number = Severity × Occurrence × Detection
- Higher RPN = higher priority
- Assign owners to action items

**Step 6: Actions Taken — Execute Countermeasures**
- Implement corrective actions
- Confirm effectiveness

**Step 7: Re-ranking — Verify Improvement**
- Recalculate severity, occurrence, detection
- New RPN should be lower
- Close action items

### Risk Priority Number (RPN) Guidance

**Calculation**: RPN = S × O × D (range: 1-1000)

**Prioritization Approach** (Quality-One recommendation):
Don't rely solely on RPN thresholds. Instead prioritize:
- Safety/regulatory concerns (severity 9-10)
- High severity AND high occurrence
- Control deficiencies (high detection values)

### Severity/Occurrence/Detection Scales

**Severity (1-10)**
- 1 = No effect
- 5-6 = Moderate effect
- 9-10 = Hazardous, safety-critical

**Occurrence (1-10)**
- 1 = Extremely unlikely (< 1 in 1,000,000)
- 5-6 = Occasional (1 in 2,000 to 1 in 400)
- 9-10 = Very high (> 1 in 20)

**Detection (1-10)**
- 1 = Almost certain to detect
- 5-6 = Moderate chance
- 9-10 = Almost certain NOT to detect (hidden failure)

### When to Conduct FMEA

**Timing**:
- Designing new products/processes/services
- Modifying existing processes
- Addressing quality improvement goals
- Periodic reviews throughout product lifecycle

**Ideal Phase**: Early design (more mitigation options, better verification, lower costs)

### Benefits

**Early Discovery Yields**:
- Multiple mitigation options
- Better verification capabilities
- Improved manufacturability
- Significant cost savings
- Leverages team knowledge

### Software FMEA Specifics

**Application**:
- Analyze software elements
- Focus on software-related deficiencies
- Emphasize design improvement
- Consider hardware failure impacts
- Plan for user misuse scenarios

**Considerations**:
- No universal software FMEA standard
- Requires software subject matter experts
- Must default to safe conditions
- Robustness to hardware failures

### When to Use

- High-reliability systems (medical, automotive, aerospace)
- Safety-critical software
- Early design phases (prevention over detection)
- Regulatory compliance requirements (FDA, ISO)
- Cost-sensitive projects (failure prevention ROI)

### eFIT Protocol Alignment

**→ Maps to STOPPER "Pull back"**
- Both analyze causes before effects manifest
- Both trace from symptoms to root system flaws
- Both prevent problems rather than react

**→ Maps to STOPPER "Practice what works"**
- Both build on historical failure data
- Both systematically apply proven prevention
- Both create organizational knowledge base

**→ Maps to STOPPER "Expand" (team-based analysis)**
- Cross-functional teams prevent tunnel vision
- Multiple perspectives reveal hidden failure modes
- Reduces individual cognitive load

### Sources
- https://quality-one.com/fmea/
- https://asq.org/quality-resources/fmea
- https://en.wikipedia.org/wiki/Failure_mode_and_effects_analysis

---

## Methodology 8: PagerDuty Retrospectives Framework

### Origin
- **Organization**: PagerDuty
- **Documentation**: retrospectives.pagerduty.com
- **License**: Apache 2.0 (open source)

### Definition
"Structured team learning sessions enabling teams to improve both products and collaboration processes through regular reflection."

### Core Distinction: Retrospectives vs. Postmortems

**Retrospectives**:
- Regular cadence (biweekly, after major projects)
- Focus on ongoing processes and team dynamics
- Duration: 60-120 minutes
- Scope: Team iteration, delivery pace, collaboration

**Postmortems**:
- Triggered by specific incidents
- Focus on incident response analysis
- Conducted shortly after resolution (fresh context)
- Scope: Technical failure, mitigation, prevention

**Key Difference**: Postmortems address "what went wrong in this incident" while retrospectives ask "how can we improve our way of working?"

### Four Main Phases

#### Phase 1: Planning Stage
**Determine**:
- Retrospective audience and size
- Style/format selection
- Logistics (remote vs. in-person)
- Facilitation approach

#### Phase 2: Execution Phase (During Retrospective)

**2.1 Setting the Stage**
- Establish psychological safety
- Review purpose and agenda
- Set ground rules

**2.2 Gathering Data**
- Collect observations from participants
- Review metrics, timelines, outcomes
- Identify significant events

**2.3 Generating Insights**
- Analyze patterns in data
- Identify root causes
- Recognize trends

**2.4 Deciding on Action**
- Generate improvement ideas
- Prioritize actionable items
- Assign owners and timelines

**2.5 Closing the Retrospective**
- Summarize decisions
- Thank participants
- Schedule follow-up

**2.6 Timeboxing Considerations**
- Allocate time per phase
- Keep discussions focused
- Use "parking lot" for off-topic items

#### Phase 3: Facilitation

**Prerequisites**:
- Formal training process
- Graduation criteria
- Pocket reference guide available

**Responsibilities**:
- Maintain neutrality
- Guide without directing
- Ensure balanced participation
- Manage time and energy

#### Phase 4: Follow-Up

**Activities**:
- Collect participant feedback
- Track action item completion
- Report progress to stakeholders
- Schedule next retrospective

### Target Audience
- Team members across industries
- Organizational leaders building continuous improvement cultures
- Facilitators seeking structured frameworks

### When to Use

**Regular Cadence**:
- Every 2 weeks (sprint retrospectives)
- After completing large-scale projects
- Quarterly for strategic reviews

**Triggered Events**:
- Team conflicts or dysfunction
- Process breakdowns
- Quality issues
- Missed deadlines

### eFIT Protocol Alignment

**→ Maps to STOPPER "Practice what works"**
- Both emphasize learning from experience
- Both build on evidence of past performance
- Both codify successful approaches

**→ Maps to STOPPER "Expand" (team learning)**
- Collective reflection reduces individual burden
- Shared mental models improve coordination
- Team wisdom exceeds individual insight

**→ Maps to DBT's Dialectical thinking**
- Balances "what's working" with "what needs change"
- Synthesis of opposing viewpoints
- Both/and thinking (not either/or)

### Sources
- https://retrospectives.pagerduty.com/
- https://www.pagerduty.com/blog/postmortems-vs-retrospectives/

---

## Cross-Methodology Synthesis

### Convergent Evolution with eFIT Protocols

| RCA Methodology | Primary eFIT Alignment | Convergent Principle |
|----------------|------------------------|----------------------|
| Five Whys | STOPPER "Pull back" | Iterative deepening to root causes |
| Fishbone Diagram | STOPPER "Observe" + "Take a step back" | Systematic categorization prevents tunnel vision |
| Google SRE Postmortems | DBT Non-judgmental stance + STOPPER "Practice what works" | Systems thinking over blame |
| Etsy Blameless Culture | DBT STOP + Radical Acceptance | Psychological safety enables learning |
| Systematic Debugging | STOPPER entire sequence | Structured process reduces cognitive load |
| Cause Elimination | STOPPER "Pull back" | Scientific method applied to debugging |
| FMEA | STOPPER "Pull back" + "Practice what works" | Proactive failure prevention |
| PagerDuty Retrospectives | STOPPER "Expand" + DBT Dialectics | Team learning over individual heroics |

### Shared Design Principles

**1. System-Level Thinking**
All methodologies shift focus from individual errors to environmental/system factors enabling failures.

**2. Non-Blame Orientation**
Psychological safety enables honest disclosure, which enables accurate understanding.

**3. Evidence-Based Improvement**
Data collection precedes analysis; hypotheses tested against reality.

**4. Iterative Refinement**
Problems rarely solved in single pass; progressive deepening reveals truth.

**5. Documentation as Learning**
Written artifacts preserve institutional knowledge beyond individuals.

**6. Cross-Functional Collaboration**
Multiple perspectives reveal blind spots invisible to specialists.

### Integration Recommendations

**For AI Systems (eFIT context)**:

**Combine Five Whys + Fishbone**:
- Use Fishbone for breadth (identify domain categories)
- Apply Five Whys within each category for depth
- Result: Comprehensive root cause mapping

**Sequence STOPPER → Postmortem**:
- STOPPER prevents reactive debugging during incident
- Postmortem provides structured analysis afterward
- Combination: Effective response + systematic learning

**Embed Retrospectives + FMEA**:
- FMEA proactively identifies failure modes
- Retrospectives reactively improve based on experience
- Together: Prevent known issues, learn from novel ones

### Implementation Priority for eFIT Research

**Phase 1 (Immediate)**:
- Five Whys (simplest, highest value)
- Systematic Debugging framework
- Blameless postmortem templates

**Phase 2 (Near-term)**:
- Fishbone diagram integration
- FMEA for known AI failure modes
- Retrospective cadence establishment

**Phase 3 (Long-term)**:
- Automated RCA tooling
- Pattern detection across incidents
- ML-driven failure prediction

---

## Limitations and Criticisms

### Five Whys Limitations

**Investigator Bias**
Results depend heavily on investigator knowledge and perspective. Different people may follow different "why" paths.

**Multiple Root Causes**
Real-world problems often have multiple interacting causes; Five Whys forces single-path analysis.

**Confirmation Bias**
Tendency to stop at familiar causes rather than unfamiliar deeper roots.

### Fishbone Limitations

**Overwhelm Risk**
Can generate too many potential causes without prioritization mechanism.

**Category Limitations**
6 Ms framework may not fit all problem types (especially software/AI).

**False Precision**
Visual structure implies causation that may not exist.

### Postmortem Limitations

**Time Investment**
High-quality postmortems require significant engineering time.

**Fatigue Risk**
Too many postmortems lead to "postmortem fatigue" and declining quality.

**Action Item Debt**
Organizations accumulate action items faster than completion, creating technical debt.

### FMEA Limitations

**Upfront Cost**
Requires substantial time investment in early design phases.

**RPN Oversimplification**
Multiplicative scoring can hide nuances (e.g., high severity with low occurrence).

**Expert Dependency**
Quality depends on team expertise; novice teams miss failure modes.

### Mitigation Strategies

**For Five Whys**:
- Use Fishbone to explore multiple paths
- Include cross-functional team to reduce bias
- Document alternative hypotheses even if not pursued

**For Fishbone**:
- Combine with data analysis to prioritize causes
- Use custom categories when 6 Ms don't fit
- Time-box brainstorming to prevent overwhelm

**For Postmortems**:
- Establish clear triggers (don't postmortem everything)
- Use lightweight formats for minor incidents
- Track action item completion rates

**For FMEA**:
- Start with high-risk components (not exhaustive)
- Use historical failure data to guide analysis
- Focus on severity 9-10 items if time-constrained

---

## Additional Resources

### Books
- *Site Reliability Engineering* (Google) — https://sre.google/sre-book/
- *The Field Guide to Understanding Human Error* (Sidney Dekker)
- *Toyota Production System* (Taiichi Ohno)

### Online Guides
- Google SRE Workbook: https://sre.google/workbook/
- PagerDuty Retrospectives: https://retrospectives.pagerduty.com/
- PagerDuty Postmortems: https://postmortems.pagerduty.com/
- Etsy Code as Craft: https://www.etsy.com/codeascraft/

### Training Resources
- "Wheel of Misfortune" exercises (Google SRE)
- Etsy Debriefing Facilitation Guide
- PagerDuty Incident Response training

### Templates
- Google SRE postmortem template: https://sre.google/sre-book/example-postmortem/
- PagerDuty incident response template: https://response.pagerduty.com/

---

## Conclusion

This research documents 8 established RCA methodologies from authoritative sources (Google, Toyota, Etsy, PagerDuty) that demonstrate convergent evolution with eFIT protocols. Key findings:

**Convergent Design Patterns**:
- Iterative deepening (Five Whys ↔ STOPPER "Pull back")
- Systematic observation (Fishbone ↔ STOPPER "Observe")
- Blameless culture (Google/Etsy ↔ DBT non-judgmental stance)
- Cognitive load reduction (Program slicing ↔ STOPPER "Expand")

**Shared Principles**:
- System-level thinking over individual blame
- Evidence-based improvement
- Documentation as learning
- Cross-functional collaboration

**eFIT Integration Value**:
These methodologies provide battle-tested frameworks for implementing eFIT protocols in AI systems. Their convergent evolution with DBT/CBT techniques validates the computational homology thesis—same problems across substrates require similar solutions.

**Next Steps**:
- Map methodologies to specific eFIT protocol implementations
- Create combined RCA framework (Five Whys + Fishbone + STOPPER)
- Develop AI-specific postmortem templates
- Build automated RCA tooling

**Research completed**: 2025-11-17
**Total methodologies documented**: 8
**Sources consulted**: 25+ authoritative references
**eFIT protocol mappings**: All major protocols aligned

---

## Appendix: Quick Reference Matrix

| When You Need... | Use This Methodology | Time Required | Complexity |
|-----------------|---------------------|---------------|------------|
| Quick root cause on single issue | Five Whys | 30-60 min | Low |
| Multiple potential causes | Fishbone Diagram | 60-90 min | Medium |
| Post-incident learning | Blameless Postmortem | 2-4 hours | High |
| Regular team improvement | Retrospective | 60-120 min | Medium |
| Systematic debugging | 6-Step Process | Varies | Medium |
| Proactive failure prevention | FMEA | 4-8 hours | High |
| Hypothesis testing | Cause Elimination | 1-3 hours | Medium |
| Complex code investigation | Program Slicing | Varies | High |

**Combination Recommendations**:
- Five Whys + Fishbone = Depth + Breadth
- STOPPER + Postmortem = Response + Learning
- FMEA + Retrospectives = Prevention + Adaptation
