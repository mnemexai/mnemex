---
description: Resume the implementation of the CortexGraph Web App Graph Visualization feature.
---

This workflow resumes the work from Phase 6 (Full Metadata Display) of the Graph Visualization implementation plan.

1. **Verify Environment**: Ensure all dependencies are installed.
   ```bash
   pip install -e ".[dev]"
   ```

2. **Review Context**:
   - Read `task.md` to see the current progress (Phase 5 complete, Phase 6 pending).
   - Read `implementation_plan.md` for the detailed design.
   - Read `walkthrough_phase5.md` to see what was just completed.

3. **Check Current State**:
   - Run the contract tests for graph visualization to ensure no regressions.
   ```bash
   pytest tests/contract/test_graph_api.py
   pytest tests/integration/test_graph_visualization.py
   ```

4. **Resume Phase 6 Implementation (User Story 3)**:
   - **Objective**: Display full metadata (tags, dates, usage stats) in the memory detail view.
   - **Tasks**:
     - T050: Contract test for metadata fields.
     - T053: Update `MemoryResponse` model if needed (likely already supports it).
     - T054: Update frontend to display all metadata fields nicely.
     - T055: Format dates and times.
     - T056: Add copy-to-clipboard for JSON representation.

5. **Continue with Phase 7 (Production Hardening)**:
   - Once Phase 6 is complete, proceed to Phase 7 (Error Handling & Security).
