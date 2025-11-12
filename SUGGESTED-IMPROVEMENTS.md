# Suggested Improvements for CortexGraph Organization

Based on an analysis of the graph structure, here are some suggested organizational techniques to enhance discoverability, context, and maintenance.

### 1. Create "Maps of Content" (MOCs)

Currently, many memories relate to large, recurring topics like "STOPPER" or "Prefrontal Systems." A Map of Content (MOC) is a single, high-level memory that acts as a curated index or dashboard for a major topic, turning scattered notes into a cohesive, navigable resource.

- **Action:** Create new memories dedicated to being MOCs (e.g., `MOC: STOPPER Protocol`).
- **Content:** This memory would contain a brief summary of the topic and then a curated list of links to the most important related memories (e.g., the core definition, the full paper draft, key case studies, related retrospectives).
- **Benefit:** This provides a single, stable entry point to explore the entire history and current state of a major project or concept.

### 2. Use Hierarchical (Nested) Tags

The current tagging system is effective but flat. Adopting a hierarchical or nested tag structure can create a browsable taxonomy, which is incredibly powerful for filtering and searching a growing knowledge base.

- **Action:** Evolve flat tags into a nested structure using forward slashes (`/`).
- **Examples:**
  - `stopper` could become `project/stopper`
  - `paper_revision` could become `project/stopper/paper-revision`
  - `branding` could become `project/prefrontal-systems/branding`
  - `dbt-for-ai` could become `concept/psychology/dbt/ai-application`
- **Benefit:** This allows for queries of varying specificity. You could search for `tags:"project/stopper"` to see everything about the project, or `tags:"project/stopper/paper-revision"` to see only the paper revision notes.

### 3. Formalize Memory "Types"

Many memories represent a specific *type* of information (e.g., a to-do list, a key insight, a meeting summary, a project definition). Formalizing this with a dedicated `type` tag makes the graph much easier to manage and query.

- **Action:** Add a `type/...` tag to memories to classify their role.
- **Examples:**
  - A to-do list memory could get `type/plan` or `type/todo-list`.
  - A memory about a key discovery could get `type/insight`.
  - A session retrospective could get `type/retrospective`.
  - A memory marking a major project completion could get `type/milestone`.
- **Benefit:** This enables powerful, cross-topic queries, such as finding all major insights from the last month or listing all active plans, regardless of the project they belong to.

### 4. Use More Specific Relation Types

The graph currently uses the `related` link type extensively. CortexGraph supports more specific relationship types that can add a deeper layer of semantic meaning to the connections between memories.

- **Action:** When creating links, consider using more descriptive types to capture the nature of the connection.
- **Examples:**
  - A detailed memory could `support` a summary memory.
  - A memory about a key decision could be linked from the context with `has_decision`.
  - If one idea directly leads to another, the first can be said to `cause` the second.
  - A memory refuting an old idea could be linked with `contradicts`.
- **Benefit:** This makes the graph traversable in more meaningful ways, allowing you to trace the flow of causality, evidence, and decision-making through your knowledge base.

---

## Code-Level Implementation Suggestions

Here are the specific locations in the `cortexgraph` codebase where the above organizational improvements could be implemented.

### 1. Maps of Content (MOCs)

This is a new feature that would best be implemented as a new tool.

- **Suggestion:** Create a new tool file `src/cortexgraph/tools/create_moc.py`.
- **Implementation:** This new `create_moc` tool would:
    1. Accept a `topic: str` and `title: str` as arguments.
    2. Import and call the `search_memory` function from `src/cortexgraph/tools/search.py` to find all memories matching the topic.
    3. Format the results into a markdown list of links to the found memories.
    4. Import and call the `save_memory` function from `src/cortexgraph/tools/save.py` to create a new memory with the generated content, automatically adding a `type/moc` tag.

### 2. Hierarchical (Nested) Tags

The codebase already supports this feature correctly. This is a workflow suggestion rather than a code change.

- **Location:** `src/cortexgraph/security/validators.py`
- **Analysis:** The `TAG_PATTERN` regex on line 41 (`re.compile(r"^[a-zA-Z0-9\-_/]+$")`) already permits forward slashes (`/`), which is the standard for nested tags. The accompanying comment correctly references the Obsidian documentation.
- **Action:** No code change is required. The improvement is to adopt the `category/subcategory` convention in user workflows.

### 3. Formalize Memory "Types"

This can be implemented either by convention or by a code change for more explicit support.

- **Option A (Convention Only):** Simply adopt the workflow of adding a `type/...` tag to the existing `tags` list when calling `save_memory`. The current code supports this without changes.
- **Option B (Code Enhancement):** For more robust, explicit support:
  - **File to Modify:** `src/cortexgraph/tools/save.py`
  - **Suggestion:** Add a dedicated `type: str | None = None` parameter to the `save_memory` function signature.
  - **Implementation:** Inside the function, if the `type` parameter is provided, it could be programmatically added to the memory's metadata or tags list (e.g., as `type:{type}`). This would also involve a small change to the `Memory` or `MemoryMetadata` models in `src/cortexgraph/storage/models.py`.

### 4. Use More Specific Relation Types

This is a straightforward enhancement to the existing validation system.

- **File to Modify:** `src/cortexgraph/security/validators.py`
- **Location:** Line 32, the `ALLOWED_RELATION_TYPES` set.
- **Suggestion:** Expand the set with additional semantic relationship types.
- **Implementation:** Add new strings to the set, for example:

    ```python
    ALLOWED_RELATION_TYPES = {
        "related",
        "causes",
        "supports",
        "contradicts",
        "has_decision",
        "consolidated_from",
        "refines",          # A new memory refines an older one
        "summarizes",       # A memory is a summary of another
        "is_part_of",       # A memory is a component of a larger concept
        "has_example",      # A memory provides an example for another
    }
    ```

---

## Consolidation and Clustering Routine Improvements

The `cluster_memories` and `consolidate_memories` tools provide a powerful foundation for graph maintenance. Here are suggestions to make them even more effective.

### Clustering (`cluster_memories`)

- **Location:** `src/cortexgraph/tools/cluster.py`
- **Analysis:** The tool is primarily driven by semantic similarity. While effective, it could be enhanced with more diverse strategies and more actionable outputs.

**Suggestions:**

1. **Add New Clustering Strategies:** The `strategy` parameter could be expanded to support methods beyond vector similarity.
    - **Implementation:** In `cluster_memories`, add logic to handle new strategy types. This would likely involve new functions in `src/cortexgraph/core/clustering.py`.
    - **New Strategies:**
        - `"tag_overlap"`: Cluster memories that share a high percentage of common tags. This is excellent for grouping user-defined topics.
        - `"temporal"`: Cluster memories created in close temporal proximity (e.g., within the same hour or day), which is useful for grouping notes from a single work session.
        - `"hybrid"`: A weighted combination of similarity, tag overlap, and temporal proximity to produce highly relevant, context-aware clusters.

2. **Generate Actionable Cluster Summaries:** The current output is a list of IDs and previews. The tool could provide more intelligence in its output.
    - **Implementation:** After clusters are generated, a new function could be called to process each cluster and enrich the output.
    - **New Features:**
        - **Auto-Generated Titles:** Use an LLM to generate a concise title for each cluster (e.g., "Memories about STOPPER paper revisions from late October").
        - **Keyword/Entity Extraction:** Identify and return the most frequent and significant keywords or entities within the cluster to provide an at-a-glance summary.

### Consolidation (`consolidate_memories`)

- **Location:** `src/cortexgraph/tools/consolidate.py`
- **Analysis:** The tool has a robust `preview`/`apply` workflow and correctly preserves history by creating `consolidated_from` relations. The biggest opportunity for improvement lies in the intelligence of the content merging itself.

**Suggestions:**

1. **Implement Intelligent Content Merging:** The current merge logic (likely in `core/consolidation.py`) could be augmented with LLM-powered strategies.
    - **Implementation:** Add a `merge_strategy: str` parameter to `consolidate_memories`. The `execute_consolidation` and `generate_consolidation_preview` functions in `src/cortexgraph/core/consolidation.py` would need to be updated to handle these new strategies.
    - **New Strategies:**
        - `"summarize"`: Instead of combining all text, this strategy would feed the content of all memories in the cluster to an LLM and prompt it to generate a single, coherent, summarized memory that captures the essence of the originals.
        - `"qa_extract"`: This strategy would prompt an LLM to read the clustered memories and extract the most important questions and answers into a structured Q&A format.
        - `"deduplicate_and_merge"`: A more advanced version of the current approach that intelligently identifies and removes redundant sentences or paragraphs before combining the unique information.

2. **Enhance the Preview:** The preview mode is a critical safety feature and can be made even more informative.
    - **Implementation:** The `generate_consolidation_preview` function in `src/cortexgraph/core/consolidation.py` can be expanded.
    - **New Features:**
        - **Show a `diff`:** For non-summarization strategies, generate and display a `diff` of the content to be merged, highlighting what text is unique versus what is overlapping and will be removed.
        - **Preview Summaries:** When `merge_strategy="summarize"` is used in preview mode, the preview should include the LLM-generated summary so the user can approve it before applying the consolidation.
