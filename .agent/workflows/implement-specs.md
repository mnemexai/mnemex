---
description: Implement a feature based on a provided spec directory.
---

---
description: Implement a feature based on a provided spec directory.
---

1. **Identify Spec Directory**:
   - Look at the user's message to see if they provided a path to a spec directory (e.g., `specs/001-foo`).
   - **IF** a path is provided: Set that as the `TargetDirectory`.
   - **IF** no path is provided: STOP and ask the user, "Which spec directory would you like me to work on?"

2. **Read Context**:
   - Use `list_dir` to inspect the `TargetDirectory`.
   - Read all relevant files (Markdown, text, etc.) within that directory to understand the requirements.

3. **Initialize Task**:
   - Create or update `task.md` by extracting requirements from the files you just read.
   - Break down the work into a checklist.

4. **Plan Implementation**:
   - Create `implementation_plan.md` detailing the changes required.
   - Group changes by component/file.

5. **Review**:
   - Ask the user to review the plan before starting execution.
