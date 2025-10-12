# PRP: ARIA Prototype Architecture

### What we are making

A prototype of an agentic system named **ARIA**.

### Main Technologies

- `deepagents` library
- `langgraph`
- `deep-agents-ui`

**Note:** `deepagents` is a wrapper built on top of `langgraph`. `deep-agents-ui` is an open-source codebase that works in tandem with the `deepagents` code. Thus, when we use the `langgraph dev` command in the CLI, our agent connects to the frontend, and we can use the frontend to chat with the agent.

---

### Agent Architecture

The following is the envisioned workflow for the prototype.

**ARIA** will be the customer-facing LLM. Only **ARIA** will communicate directly with the user.

#### Workflow

1.  **ARIA** receives a request/query.
2.  If the query is trivial (e.g., "Hi, what can you do for me?"), **ARIA** handles it directly.
3.  If the query is complex, **ARIA** will start creating a `TODO` list about what to do and which agent to use. (e.g., User asks a complex query, **ARIA** responds: "I will save your query and make a todo.")
4.  **ARIA** has knowledge of the available subagents. For this prototype, we will have two subagents: `sec-edgar` and `obsidian`.
5.  Each subagent is an expert for its specific task:
    - `obsidian`: Deals with queries requiring access to the Obsidian vault.
    - `sec-edgar`: Deals with user queries about SEC-EDGAR.
6.  The subagents perform these tasks with the help of the MCP servers they have access to.
7.  **ARIA** understands the capabilities of the subagents and assigns them tasks. Its planning is simply to extract the user's request and delegate each task to the suitable subagent.
8.  Once subagents receive a task, they complete it in a single step (one-shot completions, no back-and-forth communication).
9.  The output from the subagents is passed to a `synthesizer` agent, which creates a concise report of the findings from all subagents.
10. The `synthesizer`'s output is displayed to the user. **ARIA** is notified that the `synthesizer` has finished and informs the user about what was done.
11. To do this, **ARIA** must know what each agent did. Agents should send a special, small summary back to **ARIA** for this purpose.

---

### Perks of `deepagents`

1.  **Virtual File System (VFS):** We get a runtime, session-scoped VFS where agents can store files.
2.  **File System Tools:** Agents have access to tools like `read`, `write`, `edit`, and `ls` for these files. This is beneficial for session memory and for sharing memory between agents (e.g., **ARIA** reading files written by the `obsidian` agent).
3.  **Verifiability:** This VFS is helpful because we can save the actual output from agents, allowing **ARIA** to cross-check the information if the user asks it to.
4.  **Planning Tool:** Agents also have access to a `TODO` tool by default, which is helpful for planning. Every agent except the `synthesizer` should have this tool.
5.  **Follow-up Handling:** If a follow-up question is asked, **ARIA** can either reread the information stored in the VFS to answer or, if subagents are required (i.e., the follow-up is a new question, not about something already found), **ARIA** can once again contact one or more subagents. **ARIA** should inform the subagents if they have already performed a previous related task so they can refer to the VFS for their prior work.

---

### Design Notes

- **ARIA's Role:** **ARIA** acts as the main orchestrator of the conversation flow, while the subagents are specialists for token-intensive tasks. This delegation prevents **ARIA** from being overloaded.

- **Parallel Subagent Calls:** **ARIA** must be able to make parallel calls to subagents. For example, if one query requires both the `sec-edgar` and `obsidian` subagents, it should invoke both simultaneously and only respond to the user after both subagents and the `synthesizer` have completed their tasks.

- **Synthesizer & Memory Management:** The role of the `synthesizer` is critical for memory management. Both subagents might produce extensive reports. We do not want to store these entire reports in our chat memory. The synthesized version will be outputted to the user, but **ARIA** will only retain the "summarized" or "conclusion" versions from all subagents and the synthesizer in its own memory. We can consider skipping the synthesizer's summary in **ARIA**'s memory if necessary.
