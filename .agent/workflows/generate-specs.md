---
description: Generate requirements, plans, and to-do lists using GitHub's Spec-Kit bash scripts.
---

This workflow executes the actual Spec-Kit bash scripts to manage the feature lifecycle, ensuring consistency with the Spec-Kit methodology.

1. **Initialize/Verify Spec-Kit**:
   Ensure the `.specify` directory exists.
   ```bash
   # Initialize Spec-Kit if needed
   if [ ! -d ".specify" ]; then
       pip install "git+https://github.com/github/spec-kit.git" || true
       specify init . --ai gemini --no-git --force
   fi
   # Ensure scripts are executable
   chmod +x .specify/scripts/bash/*.sh
   ```

2. **Create New Feature**:
   Use the `create-new-feature.sh` script to set up the branch and directory structure.
   - **Input**: Ask user for Feature Description and Short Name.
   - **Command**:
     ```bash
     ./.specify/scripts/bash/create-new-feature.sh "<Feature Description>" --short-name "<Short Name>"
     ```
   - **Note**: This script creates the feature branch (if git is available), creates `specs/<feature-branch>/`, and copies `spec-template.md`.

3. **Generate Constitution**:
   Use the constitution prompt template.
   - **Source**: `.specify/memory/constitution.md` (or `.specify/templates/constitution.md` if moved).
   - **Action**: Generate `specs/constitution.md` using the template as a system prompt.

4. **Generate Specification**:
   Fill in the `spec.md` created by the script.
   - **File**: `specs/<feature-branch>/spec.md`
   - **Template**: `.specify/templates/spec-template.md` (already copied by script).
   - **Prompt**: `.specify/specify.md` (system prompt).
   - **Action**: Update `specs/<feature-branch>/spec.md` with the generated content.

5. **Generate Implementation Plan**:
   Use the `setup-plan.sh` script (if available) or manually create `plan.md` from template.
   - **Command**:
     ```bash
     # Check if setup-plan exists and run it, or copy template
     if [ -f ".specify/scripts/bash/setup-plan.sh" ]; then
         ./.specify/scripts/bash/setup-plan.sh
     else
         cp .specify/templates/plan-template.md specs/<feature-branch>/plan.md
     fi
     ```
   - **Prompt**: `.specify/plan.md` (system prompt).
   - **Action**: Update `specs/<feature-branch>/plan.md`.

6. **Generate Task List**:
   Create `tasks.md` from template.
   - **Command**: `cp .specify/templates/tasks-template.md specs/<feature-branch>/tasks.md`
   - **Prompt**: `.specify/tasks.md` (system prompt).
   - **Action**: Update `specs/<feature-branch>/tasks.md`.

7. **Refine and Validate**:
   Review artifacts with the user.

8. **Execute**:
   Proceed to implementation using the generated tasks.
