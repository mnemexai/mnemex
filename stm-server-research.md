stm-server-research

On my computer, I have an mcp server called basic-memory that allows AI tools to 'remember' things into my Obsidian vault. This is good for long term memory. I need something for ephemeral memories or short term memory and a process by which memories can be moved into long term storage if they are reinforced through regular reference in normal work. It also needs a temporal component so that short term memories can 'fade' over time if not referenced. 

Research the web and github and maybe arxiv (though most of the info there is hypothetical) for something that can either achieve this goal directly or that can be pieced together with other tools to achieve this effect. Ultimately, I would like long term memories to either reside in my Obsidian vault or in a database that can be referenced by my vault.
ChatGPT said:

Thanks for the detailed context. To focus the research, could you please clarify a few points:

Tooling Stack: Are there specific tools or frameworks you already use (e.g., LangChain, LlamaIndex, MemGPT, OpenAI tools, custom scripts)?

Obsidian Access: Should the solution interact with Obsidian via its plugin API, file sync, or do you prefer memory to be handled externally with references into the vault?

Integration Style: Do you want this short-term memory system to run as a local background service (like your MCP server), a plugin to another system, or are cloud-based tools acceptable?

Language/Framework Preferences: Any programming languages, databases, or frameworks you'd prefer (e.g., Python, SQLite, JSON-based storage)?

Scope of Use: Is this meant to assist just you on one machine, or is syncing across devices (or collaboration) in scope too?

Let me know and I’ll begin the research right after you confirm these details.

You said:
1. nothing specific, I would like the solution to be accessible via model context protocol.
2. The plugin API is fine, but direct filesystem access is available. that is how basic-memory works. My guess is that filesystem access would be faster than going through the API.
3. local background mcp. native. no containers unless absolutely needed
4. python + sqlite or json would be preferable, but I can work with most anything.
5. Just one machine
ChatGPT said:

Great. I’ll look into tools and techniques that support short-term memory for local AI systems with the following criteria:

Supports ephemeral memory that fades unless reinforced

Compatible with the Model Context Protocol (MCP)

Operates locally as a background service (no containers unless necessary)

Can promote short-term memories to long-term ones in your Obsidian vault based on reinforcement or usage

Works well with Python and either SQLite or JSON

I’ll review projects across GitHub, research papers, and relevant web discussions. I’ll update you once I’ve gathered actionable insights and options.

Research completed in 5m · 14 sources · 114 searches

Short-Term Memory System for MCP-Compatible AI with Obsidian Integration

Ephemeral AI Memory with Temporal Decay and Long-Term Consolidation
The Challenge of Ephemeral vs Persistent Memory in AI

AI assistants typically have short-term (ephemeral) memory limited by the context window, meaning they forget conversation details once those fall out of the window or the session ends
arsturn.com
. This is analogous to working memory: it's transient and easily lost without reinforcement. In contrast, long-term memory systems (like your Basic Memory MCP integration with Obsidian) store information persistently across sessions. Ephemeral memory is valuable for maintaining context in the moment, but if not managed, it vanishes – losing potentially useful info. A balanced approach is needed where short-term memories can fade over time if unused (preventing clutter), yet important or frequently referenced information is retained by moving it into long-term storage.

Requirements for a Short-Term Memory System

To achieve human-like memory dynamics, the solution should meet several requirements:

Ephemeral Storage: Maintain a store of recent interactions or facts that is fast to access (e.g. in-memory, JSON, or SQLite) and does not require heavy infrastructure. This short-term store should be local (no cloud) and accessible either via the Model Context Protocol or direct filesystem for speed.

Temporal Decay: Implement a time-based fading mechanism so that each memory’s relevance decays as time passes without being recalled
tribe.ai
. Older entries gradually drop in priority or are purged unless they’re refreshed by use. This mimics how we forget things that aren’t revisited.

Reinforcement by Usage: Each time a memory is referenced or used by the AI, it should be “strengthened” or its timer reset. Frequent recall acts as reinforcement, preventing the item from expiring
arxiv.org
. In other words, regularly referenced memories persist longer, reflecting their importance.

Promotion to Long-Term: Define a criterion by which an ephemeral memory graduates to long-term storage (Obsidian vault or a persistent DB). For example, if a memory has been referenced N times or has existed for a certain duration with repeated use, it should be saved permanently. This memory consolidation step ensures important information isn’t lost
arxiv.org
.

Seamless Integration: The system should ideally expose an interface through MCP so that AI tools can store, retrieve, and update these short-term memories on the fly. It also needs to interact with your existing Obsidian-based memory (for long-term), either by writing Markdown notes or through an API, when consolidating a memory.

Local-First and Lightweight: Operate as a local background service or script (Python is fine) without heavy containers. Direct filesystem or local database access is preferred to minimize latency (as you noted, direct FS access is faster than using a remote API). Python with SQLite or JSON for storage fits well here, given the single-machine setup.

Existing Tools and Research for Memory Decay and Reinforcement

Encouragingly, there are tools and research ideas that align with these needs:

Memoripy (Python Library) – An open-source memory management library that already implements short-term vs long-term storage and optional memory decay & reinforcement. According to its documentation, “older memories decay over time, while frequently accessed memories are reinforced.”
github.com
. It automatically classifies memories as short-term or long-term based on usage and relevance
github.com
. This could serve as a direct solution or inspiration – you could potentially integrate Memoripy into an MCP server. It uses JSON or in-memory storage for short-term data and supports embedding-based retrieval and concept tagging, which might be overkill but is useful.

Basic Memory & Cognio – Your current Basic Memory MCP server already handles persistent knowledge storage in Obsidian. Other similar MCP servers (e.g. Cognio) emphasize long-term memory via local databases + semantic search (Cognio uses SQLite and vector search to store context permanently, “unlike ephemeral memory that disappears after each session”
github.com
). However, these are geared toward persistent memory. To add ephemerality, one might run a second memory mechanism in parallel that intentionally forgets.

Multi-Tier Memory Systems – Some advanced AI memory frameworks introduce a tiered approach. For example, the Titan Memory MCP server provides “three-tier context awareness” with a Short-term Memory for recent context, Long-term Memory for consolidated knowledge, and even a meta-memory for usage stats
github.com
. Titan’s design includes automatic memory consolidation: “important patterns from short-term are moved to long-term storage” and it prunes low-relevance memories based on recency and frequency
github.com
. This is essentially the process you're looking for, though Titan is a fairly complex Node.js project (with transformer-based learning and 16 tools) – likely more than you need, but it proves the concept is feasible.

Memory Consolidation Research – Research literature mirrors these ideas. For instance, MemoryBank (Zhong et al. 2023) increments a memory’s strength each time it’s recalled, effectively resetting its decay timer
arxiv.org
. Another framework uses a saliency score combining recency and importance, where “time decay gradually reduces the priority of older memories unless they remain relevant”
tribe.ai
. In other words, an unused memory’s influence fades, but a timely reminder can boost it back. This is analogous to human memory where repeated exposure over time solidifies recall.

Specialized Memory Graphs – Tools like LangMem SDK and Klu.ai’s Memory Graph are designed for long-term agent memory but incorporate consolidation logic. They perform automatic relevance scoring, lifecycle management, and even graph-based linking of facts
tribe.ai
. These systems confirm that automatic memory lifecycle management (deciding what to keep, forget, or consolidate) is an active area of development. While they may not be plug-and-play for your setup, they offer patterns to emulate (e.g. linking related memories, using importance tags, etc.).

The above tools show that the key pieces – short-term storage, decay over time, and promotion to long-term – can be achieved. Memoripy stands out as a straightforward solution in Python that you could adopt directly, given it already handles decay/reinforcement logic in a local environment
github.com
. Otherwise, you can draw on these concepts to implement a custom solution.

Designing the Ephemeral Memory System

Using the insights from those tools, you can design a custom ephemeral memory module tailored to your environment:

Storage Mechanism: A simple approach is to use a local SQLite database or even a lightweight JSON file to store short-term memories. Each memory entry would have fields like content (the information to remember), a timestamp (last_used or last_referenced time), a creation_time, and perhaps a use_count or strength score. SQLite offers the advantage of fast queries and persistence (so the short-term memory survives a reboot or AI restart), while JSON or in-memory Python dict would be simpler but would reset if the process restarts. Given you prefer direct filesystem access, either is fine (SQLite via Python is file-based and quite fast).

Memory Insertion: Whenever the AI encounters a new piece of information that is worth remembering (but not yet ready for long-term vault), it should add an entry to this short-term store. This could be done via an MCP tool call like short_memory.save (if implementing an MCP server) or by the AI writing to a local file through the filesystem. The entry might include metadata like tags or an embedding for semantic search, though at minimum text and timestamps suffice.

Retrieval with Decay: When the AI needs context, it can query this short-term memory. The retrieval process should factor in decay: for example, calculate a score for each memory such as score = relevance - decay_factor * (current_time - last_used). Memories not referenced recently would have their scores lowered. In practice, you might simply filter out entries older than a certain cutoff (e.g. “forget anything not recalled in the last 7 days”) or use a gradual decay function as shown in the Tribe example code
tribe.ai
tribe.ai
. If using an embedding-based search, you could also multiply the semantic similarity by a time-based weight to favor recent items.

Reinforcement on Access: Each time a memory is accessed or used by the AI, update its record. For example, set last_used = now and increment use_count. This effectively refreshes the memory’s life. As noted in research, repeated recall reduces the chance of forgetting
arxiv.org
 – implementing this could be as simple as resetting the decay by updating the timestamp, or you could increment a strength value that makes the memory more resistant to deletion. If you model a decay function, you might increase the memory’s weight so it decays more slowly thereafter.

Automatic Fading: Implement a background process or periodic check to purge truly unused memories. For instance, a daily or weekly job could scan the short-term DB and remove entries that have a last_used older than X days and a low use_count. Alternatively, you can let them remain but simply never retrieve low-scoring ones; however, cleaning them out keeps the store efficient. This is analogous to forgetting: if something hasn’t been recalled in a long time and was never important, it’s safe to drop.

Threshold for Long-Term: Decide when an item should graduate to your Obsidian vault. Possible policies:

Frequency-based: If use_count exceeds a threshold (meaning the AI referred to this info many times), it’s clearly important and should be saved permanently.

Time + references: If a memory has been around for a certain minimum time (to avoid saving fleeting info) and it’s been referenced consistently (e.g. at least N times over that period), then promote it. This prevents noise from going straight to long-term, ensuring only well-utilized knowledge is kept.

Explicit tagging: In some setups, the AI or user might explicitly mark something as “important”. If your AI can identify that (“this is important, I should remember it”), you could immediately flag it for long-term storage as well.

Memory Consolidation Process: When a memory qualifies for long-term, the system can move or copy it to the Obsidian vault. Since Basic Memory already writes Markdown notes to Obsidian, you have two choices:

Via Basic Memory API – If Basic Memory MCP has a tool/endpoint to add knowledge notes, call that with the content. For example, Basic Memory likely has a function to save a note (with relations and metadata) which would then appear in Obsidian
docs.basicmemory.com
docs.basicmemory.com
. Using the API ensures formatting and graph links are consistent.

Direct File Write – Create a new Markdown file in the vault (or append to an existing note) representing this memory. You would format it according to Basic Memory’s knowledge format (with YAML frontmatter, etc., if needed). Basic Memory’s docs show it stores notes with sections like “## Relations” and “## Observations” in Markdown
docs.basicmemory.com
docs.basicmemory.com
. For a simple fact, you might just create a note with the content as an observation or a short summary. Because Obsidian will detect the new file, it becomes part of your knowledge base.
After promotion, you might still keep it in short-term for a while (it won’t hurt to have it in both), but you could also delete it from the ephemeral store to free space, since it’s safely archived long-term.

MCP Interface: To integrate with AI tools smoothly, exposing this via MCP is ideal. You could implement a minimal MCP server (in Python, using something like FastAPI or even a simple Flask) with a few endpoints: e.g. remember_short(term) to save a memory, recall_short(query) to search, and maybe list_recent() or cleanup() for maintenance. This server would manage the SQLite/JSON under the hood. Because it’s MCP, any compliant AI client (Claude, Cursor, etc.) can invoke it with standardized commands. (If you prefer not to write a server from scratch, see if Memoripy can be run in a way that an AI agent can use – it might not directly support MCP out-of-the-box, but you can adapt its calls in a tool wrapper.)
Alternatively, since you mentioned the AI has direct filesystem access, an even simpler approach is to let the AI read/write the short-term memory file directly. For example, the AI could append a JSON line for a new memory and load the JSON for context. This is a bit ad-hoc but could be faster to implement and bypasses HTTP overhead. The trade-off is you lose the standardized structure MCP provides.

Promoting Short-Term Memories to Obsidian Vault (Long-Term)

Ultimately, long-term memories should reside in Obsidian or a queryable database so that they integrate with your second brain. With the above system, the promotion mechanism will ensure anything important finds its way there. Some additional considerations for this consolidation:

Metadata and Linking: When creating a permanent note in Obsidian, consider adding links or tags that connect it to related notes. Basic Memory’s format uses wiki-style links for relations and tags for topics
docs.basicmemory.com
docs.basicmemory.com
. For example, if the memory is about a project or concept that has an existing note, link them (so the graph view stays useful). This way, as your AI’s knowledge grows, it’s not just a flat list of notes but a network, which Basic Memory and Obsidian can visualize.

Avoid Duplication: Make sure you don’t duplicate knowledge in long-term storage. If the AI already wrote something similar before, maybe update that note instead of creating a new one. Your ephemeral memory system could do a quick similarity check against existing vault notes (Basic Memory might support semantic search across the vault). This is a nice-to-have; even if you skip it, you can always manually merge notes later.

Periodic Review: It might be wise to occasionally review what got promoted. The AI might save things that are technically repetitive or low-value. By reviewing the Obsidian notes (or having the AI summarize new additions), you can prune or consolidate them further. This is analogous to how humans periodically review memories (or how we sleep to consolidate memory: not all details are stored, just the important stuff). If something made it to long-term undesirably, you can remove it from the vault (and perhaps relegate it back to short-term or nowhere).

By implementing this pipeline, your AI will have a kind of medium-term memory: information that persists longer than a single session but not permanently unless it proves its worth. Unused bits naturally expire, preventing infinite accumulation of trivia, while genuinely useful knowledge accumulates in your Obsidian vault over time.

Conclusion

In summary, achieving an ephemeral memory with fading and reinforcement is practical with current tools. The core idea is to maintain a short-term memory store for recent context and apply “use it or lose it” principles: memories decay if not used
tribe.ai
, but each use reinforces them
github.com
, and sufficiently reinforced memories get consolidated into long-term storage
arxiv.org
. You can leverage libraries like Memoripy for an out-of-the-box solution supporting these features, or build a custom Python-based service using SQLite/JSON for storage. Research and existing MCP servers confirm the viability of this approach – even advanced setups automatically promote important short-term memories to long-term and prune the rest
github.com
. By integrating such a system with your Obsidian vault (either via the Basic Memory MCP or direct file writes), you ensure that your AI’s knowledge base grows organically over time with information that truly matters, while less important context gracefully fades away. This gives you the best of both worlds: a nimble short-term memory that doesn’t bloat, and a curated long-term memory that keeps enriching your second brain.

 

Sources:

Arsturn Blog – Solving AI's Forgetfulness (Local Memory MCP)
arsturn.com

Tribe AI – Context-Aware Memory Systems (on time decay and importance)
tribe.ai
tribe.ai

Memoripy GitHub – AI memory layer (decay and reinforcement features)
github.com
github.com

Kim et al. – MemoryBank research (human-like memory recall reinforcement)
arxiv.org

HenryHawke Titan MCP – Three-tier memory with consolidation and pruning
github.com
github.com

Basic Memory Docs – Obsidian integration and knowledge format
docs.basicmemory.com
docs.basicmemory.com
 (for context on vault storage)

Tribe AI – Memory frameworks (LangMem, Klu.ai) with consolidation
tribe.ai

Sources
You said:
I've used the modelcontextprotocol reference memory server before, it saves to json and work well-ish. it does not have a temporal component though. conceptually, a lightweight server like that plus some sort of temporal component and reference count could serve as the short-term memory or medium-term memory. yes? I only ask because it's something I'm a little familiar with, is already MCP enabled and seems to have worked well in the past as a memory server for AI systems.
ChatGPT said:

Yes — your intuition is solid. Starting from a memory server that already supports MCP and JSON storage (like the ModelContextProtocol reference memory server) and adding a temporal decay + reference-count component is a pragmatic and efficient path. You won’t have to reinvent all the plumbing — just augment the existing server with the temporal logic. That keeps things light and familiar.

Here’s how I’d approach enhancing that server to support ephemeral / decaying memory with promotion to long-term:

Proposal: Augmented MCP Memory Server with Decay & Reinforcement
Architecture Overview

Base MCP Memory Server

You already have a memory server that handles saving, retrieving, updating, and listing memory entries via MCP, storing in JSON.

It supports operations like save_memory, get_memory, list_memories, etc.

Add Metadata Fields
Augment each memory entry with a few extra metadata fields to support decay and reinforcement:

{
  "id": "...",
  "content": "...",
  "tags": [...],
  "created_at": 1697078400,
  "last_used": 1697082000,   // timestamp when it was last referenced
  "use_count": 3,
  "strength": 1.0
}


created_at: when the memory was first saved

last_used: updated every time the memory is referenced

use_count: how many times it’s been recalled / used

strength: optional floating score that decays (or increases) over time

Scoring / Decay Function
Define a decay or scoring formula to compute a current relevance score for each memory. Some possibilities:

Exponential decay:

score
=
strength
×
𝑒
−
𝜆
(
𝑡
−
last_used
)
score=strength×e
−λ(t−last_used)

where 
𝜆
λ is a decay constant (tunable).

Linear or piecewise:

score
=
strength
−
𝛼
(
𝑡
−
last_used
)
score=strength−α(t−last_used)

(bounded below by zero)

Hybrid with use_count: combine use_count and last_used:

\text{score} = (\text{use_count})^\beta \times e^{-\lambda (t - \text{last\_used})}

giving more weight to items used many times.

You can choose a decay model that fits your preferences (e.g. faster forgetting, slower forgetting, etc.).

Retrieval Filter / Ranking
When the AI asks the memory server to recall or list relevant memories, the server should:

Compute the score for each candidate memory (using the decay formula).

Filter out memories whose score is below a threshold (i.e. “forgotten”).

Rank the remaining ones by score (or by combined relevance to the query and score).

Return a subset (e.g. top N) as context.

Reinforcement on Access
Whenever a memory is accessed (either explicitly or implicitly during context assembly):

Update last_used = now

Increment use_count += 1

Optionally increase strength (e.g. strength += δ) or recalibrate it so that the decay starts fresh.

This effectively “refreshes” the memory and makes it less likely to be forgotten.

Garbage Collection / Purging
Periodically (e.g. every hour or day), run a cleanup task:

Remove entries whose scores are near zero (i.e. extremely aged and unused).

Optionally, archive them somewhere (in case you want to review what was forgotten) or just drop them.

Promotion to Long-Term
Define a policy to decide when a memory is “worth” moving to long-term (Obsidian). For example:

If use_count >= N (e.g. used 5 times)

If it’s been alive for >= T days and used at least M times

If its strength remains above a threshold despite decay

When memory qualifies, have the server (or an orchestrator) call the Basic Memory MCP API (or write the Markdown file) to store it long-term, then optionally remove it from short-term memory.

Benefits & Trade-Offs

Advantages:

You leverage a system you already understand and trust (the MCP memory server).

The added logic is lightweight (a few metadata fields + a scoring/decay function + periodic cleanup).

You maintain the MCP interface unchanged (so AI clients don’t have to be retooled much).

It gives you medium-term memory: stuff lives beyond a single session, but doesn’t accumulate infinitely unless it’s useful enough to be consolidated.

Challenges / Tuning Risks:

Choosing good decay constants (λ) or thresholds is somewhat empirical; you’ll likely need to tweak them to your preference (fast forgetting, slow forgetting, etc.).

There’s a risk of promoting too much low-value content to long-term if your promotion criteria are too lenient.

If the short-term store gets large, scoring and scanning many entries might slow retrieval; you may need indexing or more efficient storage (e.g. SQLite) if JSON gets large.

You’ll need to decide how to merge or deduplicate similar memories during or before promotion to long-term to avoid clutter.

Practical Steps to Build It

Fork or wrap the existing MCP memory server, adding metadata fields (use_count, last_used, strength) to each memory entry.

Extend get_memory / list_memories endpoints so returned entries are filtered & ranked by the score decay formula.

Wrap memory access (read/query) so that anytime a memory is used, the server updates its metadata (last_used, use_count, strength).

Add a background task (cron or thread) to clean out low-score memories periodically.

Implement promotion logic, linking into your Basic Memory system: when a memory qualifies, call the Basic Memory’s API or write a Markdown file.

Tune thresholds and parameters (decay rate, minimum score, promotion thresholds) based on how your AI works in practice.

You could even add an endpoint like promote_memory(id) so you can manually promote a memory if you realize it’s important.

So yes — starting from the MCP JSON memory server and layering a temporal + reinforcement component is a very sensible, lightweight, and effective architecture. If you like, I can sketch you a prototype in Python (with MCP stub methods) or show example code for decay/retrieval logic. Do you want me to build you a prototype you can drop in?

You said:
for this: You’ll need to decide how to merge or deduplicate similar memories during or before promotion to long-term to avoid clutter.

I am working on a set of processes for one of the cli AI assistants to use to traverse the json graph and the obsidian vault to trim cruft and consolidate, etc. I think that's the only way that it will work. trying to rely on a script to do this might miss nuances that an llm would catch.
ChatGPT said:
Thought for 17s

Agreed. Let the LLM do the nuance, and make the scripts act as scaffolding + guardrails. Here’s a concrete, local-first design you can drop onto your MCP stack.

LLM-in-the-loop consolidation pipeline
0) Storage & metadata (short-term)

SQLite (fast, single file) with JSON column for flexibility.

-- memories.db
CREATE TABLE mem (
  id TEXT PRIMARY KEY,
  content TEXT NOT NULL,
  meta   JSON,                -- {tags:[], source:"...", ...}
  created_at INTEGER NOT NULL,
  last_used  INTEGER NOT NULL,
  use_count  INTEGER NOT NULL DEFAULT 0,
  strength   REAL NOT NULL DEFAULT 1.0,
  embed      BLOB            -- optional: 1536-d float32, for ANN
);

CREATE INDEX mem_last_used_idx ON mem(last_used);
CREATE INDEX mem_use_count_idx ON mem(use_count);


Decay on read (or via cron):

score = (use_count^β) * exp(-λ * (now - last_used)) * strength


Purge when score < τ_forget and never promoted.

Promotion candidate when (use_count ≥ N) OR (score ≥ τ_promote).

1) Exact & fuzzy prefilters (cheap heuristics)

Before involving the LLM, shrink the candidate set:

Exact dedupe: hash of normalized content; drop identicals.

Near-duplicate shingling: 5-gram MinHash or SimHash; merge if Hamming distance < d.

Semantic screen (fast): cosine(sim(embedding), threshold t_semantic_hi for “likely dup”, t_semantic_lo for “likely distinct”). Only ambiguous clusters go to the LLM.

This cuts token costs while catching obvious duplicates.

2) Clustering for LLM review

Build clusters using embeddings (e.g., HNSW or faiss.indexFlatIP if you want dead simple).

Parameters:

t_link = 0.83 (cosine) to link

max_cluster_size = 12 (cap review batch)

Mark clusters as:

Auto-merge: high cohesion, low variance → summarize automatically.

LLM-review: mixed cohesion or conflicting facts.

3) LLM consolidation pass (CLI tool)

You already have a CLI assistant; give it a deterministic, auditable workflow.

Input bundle (per cluster)

mems.json: each item {id, content, meta, created_at, last_used, use_count}

obsidian_refs.json: harvested candidate notes from the vault (title, path, headings, backlinks, last_modified)

context.json: project/topic hints, tags, exclusion rules

System prompt (template)
You are consolidating short-term AI memories into durable notes.
Goals:
1) Merge near-duplicates into one clear, source-attributed statement.
2) Preserve facts; remove redundancy.
3) Detect conflicts; propose resolution or keep both with qualifiers.
4) Produce an Obsidian-ready Markdown block, including:
   - summary paragraph
   - bullet “facts” with provenance (memory ids)
   - backlinks [[...]] where obvious
   - YAML frontmatter suggestions (tags, aliases)
Rules:
- Keep dates and proper nouns exact.
- Keep uncertainty explicit.
- Prefer concise phrasing; no marketing language.
- If merge is unsafe, label as "NEEDS HUMAN REVIEW" with rationale.

User content (per run)
Short-term candidates (N = {{N}}):
{{mems.json}}

Relevant vault excerpts:
{{obsidian_refs.json}}

Context/policies:
{{context.json}}

Deliverables:
- "consolidated_note": Markdown body (no frontmatter)
- "frontmatter": YAML map with {title, tags, aliases, related}
- "actions": array of {type, ids, rationale}
  where type ∈ ["promote", "link_only", "skip", "needs_human_review"]

Output validator

JSON schema check (fail → re-ask with tool message).

Max-diff safety: limit changes per cluster unless confidence high.

Dry-run mode produces a .preview.md alongside a .plan.json.

4) Write-back strategies (long-term)

Two safe paths:

Basic-Memory MCP: call its “add knowledge”/“save note” tool with frontmatter, content, and relations. Keeps format consistent with your vault graph.

Direct FS: create/update vault/Knowledge/<slug>.md. Include:

--- YAML (title, tags, aliases, source_mem_ids)

“Summary” section, then “Facts (with provenance)”, then “Context/Links”.

Add source_mem_ids: [m123, m456,...] so future audits can trace origin.

If an existing note is a better home:

Append under a new ### Consolidated on 2025-10-07.

Avoid high-churn rewrites; use additive edits unless conflicts resolved.

5) Post-merge housekeeping

Mark merged short-term items with status='promoted' and keep a small stub:

redirect_to: vault path

consolidated_at: timestamp

For items that were “link_only”, retain in short-term but lower strength.

For “skip”, apply faster decay (bump λ temporarily).

6) MCP surface (so any tool can use it)

Expose minimal, composable tools:

stm.save({content, meta}) -> id

stm.search({query?, top_k?, window_days?, min_score?}) -> [ids]

stm.touch({id}) (reinforce)

stm.cluster({strategy, thresholds}) -> [cluster_ids]

stm.consolidate({cluster_id, mode: "dry_run"|"apply"}) -> {plan, previews, results}

stm.promote({ids, target:"obsidian"|"basic-memory"})

stm.gc({policy})

Keep JSON-over-stdio or HTTP; both fit MCP. Everything local.

7) Safety rails

Dry-run default for any mutation touching the vault.

Plan + diff: write *.plan.json and *.preview.md; require a second call to apply.

Budget caps: max tokens per run, max notes touched.

Confidence gating: if the model flags low confidence or conflict, shunt to “NEEDS HUMAN REVIEW”.

8) Practical thresholds (initial)

λ (decay): choose half-life of ~3 days → λ = ln(2) / (3*86400)

β (use_count weight): 0.6

τ_forget (purge): 0.05

τ_promote (promote): 0.65

t_semantic_hi: 0.88 (dup), t_semantic_lo: 0.78 (distinct)

N (use_count promote): 5 within 14 days

Tune with your real traffic; log per-decision metrics.

9) Cheap wins for quality

Normalize content before hashing: lowercase, collapse whitespace, strip URLs tracking params.

Sentence-split + dedupe at sentence level before LLM (reduces verbosity).

Maintain a stoplist: don’t promote volatile facts (ephemeral URLs, session IDs).

Keep a human-review inbox note in Obsidian where uncertain consolidations are parked.

Why this works

Scripts do what they’re good at: fast heuristics, metadata, safe file ops.

The LLM does what it’s good at: resolving soft duplicates, merging, hedging uncertainty, and writing clean Markdown with links.

MCP keeps everything tool-addressable from any client you use.

You avoid vault bloat while letting “high-signal” facts graduate naturally.

If you want, I can generate:

a minimal Python MCP server implementing stm.* (SQLite, decay, clustering stubs), and

a CLI “consolidate” runner with the prompt, schema checks, and dry-run previews.