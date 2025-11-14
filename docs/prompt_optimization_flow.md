# Prompt Optimization Flow

## Overview

This document describes a sophisticated prompt optimization architecture that intercepts, analyzes, enhances, and validates user prompts before they reach Claude. The system uses a multi-stage pipeline involving local LLMs, MCP tool chains, knowledge graph integration, and cloud-based optimization to maximize prompt quality while minimizing API costs.

## Key Benefits

- **Zero Initial API Cost**: All optimization happens before hitting paid Claude API endpoints
- **Intelligent Complexity Routing**: Simple prompts bypass optimization for speed; complex prompts get full treatment
- **Knowledge Graph Integration**: Automatically enriches prompts with relevant context from CortexGraph
- **Multi-Model Validation**: Cross-validates optimizations using multiple LLMs to ensure quality
- **Flexible Architecture**: Local LLMs can be swapped with cloud providers as needed
- **Metadata Enrichment**: Adds confidence scores, similarity metrics, and processing metadata to prompts

## Architecture Components

### 1. **Proxy Server**
   - Central orchestration layer
   - Handles routing decisions based on complexity
   - Manages communication between all components
   - Tracks confidence/similarity thresholds

### 2. **Local LLMs**
   - Primary: Prompt optimization and tagging
   - Validation: Multiple instances for cross-validation
   - Can be replaced with cloud providers (OpenAI, Anthropic, etc.)

### 3. **MCP Tool Chain**
   - **CortexGraph**: Knowledge graph for context retrieval
   - **STOPPER**: Process control and validation
   - **Custom Tools**: User-defined extensions
   - **Gemini Optimizer**: Large context window for final assembly

### 4. **Validation Layer**
   - Semantic similarity checks
   - Confidence scoring
   - Iterative refinement below thresholds

## Detailed Flow Description

### Phase 1: Initial Intake
1. **User Input**: User enters prompt in Claude Code interface
2. **Proxy Intercept**: Proxy captures the prompt before it reaches Claude
3. **Complexity Analysis**: NLP-based complexity rating determines routing strategy

### Phase 2: Intelligent Routing
4. **Simple Path** (Low Complexity):
   - Proxy applies basic formatting rules
   - Routes directly to Claude with minimal processing
   - Optimizes for speed and reduces overhead

5. **Complex Path** (High Complexity):
   - Triggers full optimization pipeline
   - Proceeds to Phase 3

### Phase 3: Prompt Optimization
6. **Local LLM Processing**:
   - Adds semantic tags to categorize intent
   - Restructures prompt for optimal Claude comprehension
   - Formats according to Claude best practices
   - Extracts key entities and concepts

### Phase 4: Validation & Refinement
7. **Multi-Model Validation**:
   - Routes optimized prompt to 2-n additional local LLMs
   - Each validator scores the optimization independently
   - Can use semantic similarity algorithms instead of LLMs
   - Calculates confidence and similarity metrics

8. **Threshold Check**:
   - If scores meet threshold: Proceed to Phase 5
   - If scores below threshold: Return to Phase 3 for reprocessing
   - Prevents low-quality optimizations from proceeding

9. **Tool Recommendation**:
   - Proxy receives validated prompt with metadata
   - System suggests relevant MCP tools for the query

### Phase 5: MCP Tool Chain Execution
10. **CortexGraph Search**:
    - Searches knowledge graph for related concepts
    - Retrieves relevant memories and context
    - Returns similarity-scored results

11. **STOPPER Validation**:
    - Process control checks
    - Safety and constraint validation
    - Prevents out-of-scope operations

12. **Additional Tools**:
    - Routes to n other tools based on user preferences
    - Each tool contributes specialized context
    - Tools run in parallel for efficiency

### Phase 6: Final Assembly
13. **Gemini Optimization**:
    - Combines original prompt + optimizations + tool outputs
    - Leverages Gemini's large context window (2M tokens)
    - Uses generous free tier for cost optimization
    - Assembles coherent final prompt

14. **Quality Assurance**:
    - Compares input to assembled output
    - Generates similarity score (drift detection)
    - Calculates final confidence rating
    - Appends metadata to prompt

### Phase 7: Claude Execution
15. **Final Prompt Delivery**:
    - Proxy sends optimized prompt to Claude
    - **First API cost incurred at this step**
    - Prompt includes:
      - Original user intent (preserved)
      - Optimization tags and structure
      - Knowledge graph context
      - Tool outputs and recommendations
      - Confidence/similarity metadata
      - Processing history

16. **Normal Operation**:
    - Claude processes the enriched prompt
    - Claude Code continues standard workflow
    - User receives high-quality response

## Sequence Diagram

\`\`\`mermaid
sequenceDiagram
    actor User
    participant Claude Code Interface
    participant Proxy
    participant NLP Complexity Analyzer
    participant Local LLM (Optimizer)
    participant Local LLM 2 (Validator)
    participant Local LLM N (Validator)
    participant Semantic Similarity Engine
    participant MCP Chain
    participant CortexGraph
    participant STOPPER
    participant Custom Tools
    participant Gemini
    participant Claude API

    %% Phase 1: Initial Intake
    User->>Claude Code Interface: Enter prompt
    Claude Code Interface->>Proxy: Forward prompt
    Proxy->>NLP Complexity Analyzer: Analyze complexity
    NLP Complexity Analyzer-->>Proxy: Complexity rating

    %% Phase 2: Routing Decision
    alt Low Complexity (Simple Prompt)
        Proxy->>Proxy: Apply basic rules
        Proxy->>Claude API: Route directly to Claude
        Note over Proxy,Claude API: Fast path for simple queries
    else High Complexity (Complex Prompt)
        Note over Proxy: Trigger full optimization pipeline

        %% Phase 3: Optimization
        Proxy->>Local LLM (Optimizer): Optimize prompt
        Note over Local LLM (Optimizer): - Add semantic tags<br/>- Format for Claude<br/>- Extract entities<br/>- Restructure query
        Local LLM (Optimizer)-->>Proxy: Optimized prompt v1

        %% Phase 4: Validation Loop
        rect rgb(240, 240, 240)
            Note over Proxy,Semantic Similarity Engine: Validation & Refinement Loop

            par Parallel Validation
                Proxy->>Local LLM 2 (Validator): Validate optimization
                Proxy->>Local LLM N (Validator): Validate optimization
                Proxy->>Semantic Similarity Engine: Check semantic similarity
            end

            Local LLM 2 (Validator)-->>Proxy: Confidence score 2
            Local LLM N (Validator)-->>Proxy: Confidence score N
            Semantic Similarity Engine-->>Proxy: Similarity score

            Proxy->>Proxy: Aggregate scores

            alt Below Confidence/Similarity Threshold
                Note over Proxy,Local LLM (Optimizer): Quality check failed
                Proxy->>Local LLM (Optimizer): Reprocess with feedback
                Local LLM (Optimizer)-->>Proxy: Optimized prompt v2
                Note over Proxy: Loop until threshold met
            else Above Threshold
                Note over Proxy: Quality validated, proceed
            end
        end

        Proxy->>Proxy: Append recommendation metadata

        %% Phase 5: MCP Tool Chain
        Proxy->>MCP Chain: Route validated prompt + metadata

        rect rgb(230, 245, 255)
            Note over MCP Chain,Custom Tools: MCP Tool Execution (Parallel)

            par Tool Execution
                MCP Chain->>CortexGraph: Search knowledge graph
                MCP Chain->>STOPPER: Validate constraints
                MCP Chain->>Custom Tools: Execute user-defined tools
            end

            CortexGraph-->>MCP Chain: Context + memories (similarity scored)
            STOPPER-->>MCP Chain: Validation results
            Custom Tools-->>MCP Chain: Tool outputs
        end

        %% Phase 6: Final Assembly
        MCP Chain->>Gemini: Assemble final prompt
        Note over Gemini: - Combine all inputs<br/>- Optimize structure<br/>- 2M token context<br/>- Free tier usage

        Gemini->>Gemini: Compare input vs output
        Gemini->>Gemini: Calculate similarity & confidence
        Gemini-->>MCP Chain: Final prompt + metadata

        MCP Chain-->>Proxy: Return final prompt

        %% Phase 7: Claude Execution
        Note over Proxy,Claude API: 💰 First API cost incurred here
        Proxy->>Claude API: Send final optimized prompt
        Note over Claude API: Prompt includes:<br/>- Original intent<br/>- Optimizations<br/>- Knowledge graph context<br/>- Tool outputs<br/>- Metadata
    end

    %% Normal Operation
    Claude API-->>Claude Code Interface: Process request
    Claude Code Interface-->>User: Return response
    Note over User,Claude Code Interface: Claude Code continues as normal
\`\`\`

## Configuration Options

### Complexity Thresholds
\`\`\`python
# Proxy configuration
# Prompts with complexity > COMPLEX_PROMPT_THRESHOLD follow the complex path, otherwise the simple path is used.
COMPLEX_PROMPT_THRESHOLD = 0.4
\`\`\`

### Validation Settings
\`\`\`python
# Validation thresholds
CONFIDENCE_THRESHOLD = 0.75       # Minimum confidence to proceed
SIMILARITY_THRESHOLD = 0.80       # Minimum semantic similarity
MAX_REFINEMENT_ITERATIONS = 3     # Prevent infinite loops
\`\`\`

### Model Selection
\`\`\`python
# Local LLMs (can be replaced with cloud providers)
OPTIMIZER_MODEL = "llama-3.1-70b"           # Primary optimizer
VALIDATOR_MODELS = [                        # Validation ensemble
    "mixtral-8x7b",
    "qwen-2.5-72b",
    "deepseek-v2"
]

# Example using cloud providers (alternative to local)
# OPTIMIZER_MODEL = "openai:gpt-4"
# VALIDATOR_MODELS = ["anthropic:claude-3-opus", "openai:gpt-4"]
\`\`\`

### MCP Tools
\`\`\`python
# Tool chain configuration
MCP_TOOLS = {
    "cortex_graph": {
        "enabled": True,
        "similarity_threshold": 0.7,
        "max_results": 10
    },
    "stopper": {
        "enabled": True,
        "strict_mode": False
    },
    "custom": {
        "user_preferences": True,
        "context_retrieval": True
    }
}
\`\`\`

### Gemini Settings
\`\`\`python
# Final assembly configuration
GEMINI_MODEL = "gemini-2.0-flash-exp"  # Free tier, large context
GEMINI_MAX_TOKENS = 2000000            # 2M token context window
GEMINI_TEMPERATURE = 0.3               # Consistent assembly
\`\`\`

## Performance Characteristics

### Latency Profile

| Stage | Estimated Time | Notes |
|-------|---------------|-------|
| Complexity Analysis | 10-50ms | Fast NLP classification |
| Simple Path (total) | 50-100ms | Minimal processing overhead |
| Optimization | 200-500ms | Local LLM inference |
| Validation | 150-300ms | Parallel execution |
| MCP Tool Chain | 100-400ms | Depends on tool complexity |
| Gemini Assembly | 300-800ms | Large context processing |
| **Complex Path (total)** | **1-3 seconds** | Full pipeline |

### Cost Analysis

**Traditional Approach** (direct to Claude):
- Every prompt hits Claude API immediately
- No optimization or context enrichment
- Cost: $X per request from first token

**Optimized Approach** (this architecture):
- Local LLMs: Free (self-hosted) or cheap (cloud)
- Gemini: Leverages the generous free tier for final assembly
- Claude API: Only hit after full optimization
- Cost: $0 until Claude execution, then same $X but better results

**Net Effect**:
- Same Claude API cost per request
- Significantly better prompt quality
- Higher success rate (fewer retries needed)
- Lower total cost due to reduced iterations

## Implementation Considerations

### 1. **Local LLM Requirements**
   - GPU: RTX 4090 or better for 70B models
   - RAM: 64GB+ recommended
   - Alternative: Use cloud inference APIs (Groq, Together.ai, OpenRouter)

### 2. **Proxy Server**
   - Needs to be MCP-compatible
   - Should support WebSocket for streaming
   - Must handle concurrent validation requests

### 3. **Knowledge Graph Integration**
   - CortexGraph needs to be populated with relevant data
   - Index must be kept up-to-date
   - Consider using CortexGraph for temporal memory

### 4. **Error Handling**
   - Fallback to simple path if optimization fails
   - Timeout protection (max 5s total processing)
   - Graceful degradation if tools unavailable

### 5. **Monitoring & Observability**
   - Track optimization success rates
   - Monitor confidence/similarity distributions
   - Log processing times for each stage
   - A/B test optimized vs non-optimized prompts

## Future Enhancements

1. **Adaptive Thresholds**: Learn optimal confidence/similarity thresholds per user
2. **Caching Layer**: Cache optimizations for similar prompts
3. **User Feedback Loop**: Incorporate user ratings to improve optimization
4. **Model Selection**: Automatically choose best LLM based on prompt type
5. **Streaming Optimization**: Stream partial results during processing
6. **Cost Tracking**: Detailed cost accounting per stage
7. **A/B Testing Framework**: Compare different optimization strategies

## Security Considerations

- **Prompt Injection**: Validate all optimized prompts for injection attempts
- **Data Privacy**: Local LLMs keep sensitive data on-premise
- **Rate Limiting**: Prevent abuse of free tier services
- **Access Control**: Authenticate proxy requests
- **Audit Trail**: Log all prompt transformations

## Related Documentation

- [CortexGraph Architecture](architecture.md) - Integration with temporal memory
- [CortexGraph Documentation](graph_features.md) - Knowledge graph features
- [MCP Specification](https://github.com/modelcontextprotocol/specification) - Tool protocol details
- [Prompt Injection Prevention](prompt_injection.md) - Security best practices

## Example Workflow

### Input Prompt
\`\`\`
"Help me write a Python function to process user data"
\`\`\`

### After Optimization
\`\`\`markdown
## Task: Python Function Development

**User Intent**: Create data processing function

**Context** (from CortexGraph):
- User prefers type hints (from memory: 2025-10-15)
- Uses pytest for testing (from memory: 2025-10-20)
- Prefers dataclasses over dicts (from memory: 2025-10-12)

**Requirements**:
1. Function should process user data
2. Follow user's Python style preferences
3. Include type hints and docstrings
4. Consider testing approach

**Metadata**:
- Confidence: 0.87
- Similarity: 0.92
- Optimization iterations: 1
- Tools used: CortexGraph, STOPPER
- Processing time: 1.2s
\`\`\`

### Result
Claude receives a rich, contextualized prompt that produces higher-quality output on the first try, reducing the need for follow-up iterations.

---

**Built with** [Claude Code](https://claude.com/claude-code) 🤖
