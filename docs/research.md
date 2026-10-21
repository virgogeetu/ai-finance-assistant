# Initial research

## Existing financial education platforms and robo-advisors

| Platform | Type | What it does well | What we borrow |
|---|---|---|---|
| Investopedia | Reference articles + dictionary | Huge glossary, every concept has a definition page | Glossary-first answers: define terms before explaining |
| Khan Academy (personal finance) | Structured courses | Concepts ordered from simple to advanced | KB organised by category with a "basics" track |
| Zogo / gamified apps | Micro-lessons | Short, bite-sized content | Short answers (<250 words), small chunks in the KB |
| NerdWallet / Bankrate | Calculators + explainers | Pairs explanations with interactive tools | Goal planner tab next to the chat |
| Betterment / Wealthfront | Robo-advisors | Risk questionnaire → model portfolio, automatic rebalancing, goal buckets | Risk profile drives reference allocation and projection assumptions |
| Vanguard Digital Advisor / Schwab Intelligent Portfolios | Robo-advisors from large brokers | Low-cost index ETFs, clear drift/rebalancing views | Portfolio "drift vs. reference mix" view |
| Cleo / Copilot-style chat apps | Conversational money apps | Natural-language entry point, friendly tone | Chat as the main interface, plain language |

**Gaps we target:** robo-advisors manage money but explain little; reference sites explain but don't look at *your* situation. AI Finance Assistant combines explanation (RAG over a curated KB) with light, educational analysis of the user's own numbers, and is explicit that it does not give personalised advice.

**Compliance-driven design rules** (from how these platforms position themselves): never recommend buying/selling specific securities, label projections as illustrative, show data freshness, and attach an educational disclaimer.

## Multi-agent frameworks

| | LangChain | LangGraph | CrewAI |
|---|---|---|---|
| Model | Components (models, retrievers, tools, chains) | Explicit state graph: nodes, conditional edges, reducers | Role-based "crew" of agents with tasks |
| Control flow | Linear chains / agent loops | Fully explicit, deterministic routing, cycles allowed | Sequential or hierarchical process, more implicit |
| State & memory | Manual | Typed state + checkpointers (per-thread memory) built in | Crew memory features, less granular |
| Error handling | Manual | Per-node, easy to add fallback edges | Retries per task |
| Best for | Building blocks | Production workflows needing routing, memory, observability | Fast prototyping of collaborative agents |

**Decision:** LangGraph for orchestration and state, LangChain components for model and embedding wrappers. Routing in a finance app must be predictable and auditable (which agent answered, with what data), and LangGraph's typed state, conditional edges and checkpointer give that directly. CrewAI's role-play style is attractive but harder to constrain for compliance-sensitive output.

**Other choices**
- **LLM:** provider-agnostic wrapper (Gemini / OpenAI / Claude) selected by `LLM_PROVIDER`; offline `mock` mode returns tool-computed drafts so everything is testable without keys.
- **Vector DB:** FAISS (local, free, fast for ~10k chunks). Chroma/Pinecone can replace `FaissStore` behind the same interface.
- **Market data:** Alpha Vantage primary (quotes, daily series, news sentiment), yFinance fallback, deterministic sample data offline.
- **UI:** Streamlit for speed of iteration; React is an option later via the same `FinanceWorkflow.chat()` API.
