# AskImmigrate 2.0: Multi-Agent U.S. Immigration Assistant 🇺🇸🤖

**Project Goal:**  
AskImmigrate 2.0 helps users navigate U.S. immigration—from F/J/B visas to green cards and citizenship—using a team of agentic AI specialists.

**Features:**
- Multi-agent system: Intake, Research, Tool, Checklist, and Output agents each handle distinct roles.
- RAG & Tools: Uses Retrieval-Augmented Generation (ChromaDB), web search, PDF parsing, and cost calculation.
- Step-by-step checklists and official forms for all major visa/status questions.
- Built for CLI and web UI; easily extensible for new features.

## Agents & Responsibilities

| Agent          | Main Responsibility         |
|----------------|----------------------------|
| Intake Agent   | Parse/understand user’s scenario, visa, country |
| Research Agent | Retrieve rules, requirements, and forms |
| Tool Agent     | PDF parsing, fee calculation, eligibility check |
| Checklist Agent| Build custom checklist of steps/docs |
| Output Agent   | Synthesize and present answers |

## State Structure

See `agentic_state.py` for full details.

## Getting Started

1. **Clone the repo**
2. **Install dependencies**
3. **Set up `.env` with API keys**
4. **Run backend and (optionally) frontend**

## Contributing

- Each team member owns at least one node/agent.
- All work should be done via issues, branches, and PRs.
- See the [Project Board](LINK_TO_PROJECT_BOARD) for progress.

## License

MIT

## Maintainers

- @arindakhill – Intake Agent
- @okumujustine – Research Agent, RAG
- @deo-Mugabe – Tool/Checklist Agent, PDF, Calculator
- @dunky-star – Output Agent, Docs, Integration
