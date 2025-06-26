# AskImmigrate 2.0: Multi-Agent U.S. Immigration Assistant 🇺🇸🤖

**Navigate U.S. immigration — from F/J/B/many more visas to green cards and citizenship — with AI-powered guidance.**

---

## Overview

AskImmigrate 2.0 is an easy-to-use assistant for U.S. immigration.  
Whether you’re applying for a visa, changing status, or pursuing citizenship, you’ll get clear answers, forms, and step-by-step checklists—**no legal jargon required**.

- **Powered by multiple agentic AI specialists:** Each handles a specific part of your question.
- **Official data, updated logic:** Guidance is grounded in real forms, policies, and government sources.
- **Supports CLI and web UI** for flexible use.

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+ (for React frontend)
- Groq/OpenAI API key (for LLM)
- Access to required PDF/JSON files in `/data/`

### Installation

```bash
git clone https://github.com/okumujustine/AskImmigrate.git
cd AskImmigrate
uv pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Environment Setup

1. Create `.env` file at the project root.
```bash
GROQ_API_KEY=your-groq-api-key
OPENAI_API_KEY=your-open-api-key
```
2. Ensure JSON and PDF source files are accessible on disk.

#### ⚡ LangSmith Observability Setup

AskImmigrate 2.0 supports full agentic tracing with [LangSmith](https://smith.langchain.com).

**Add these variables to your `.env`:**

```env
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=AskImmigrate2.0
```
**(Optional) If using OpenAI:**
```env
OPENAI_API_KEY=your-openai-api-key
```

Ensure your code loads `env` vars (usually already in backend/graph_workflow.py):
```bash
from dotenv import load_dotenv
load_dotenv()
```

Run your CLI, workflow, or web UI as normal.
All LLM calls, agent transitions, and state changes are now logged to your [LangSmith dashboard](https://smith.langchain.com)..

Never commit your `.env` or API keys to git!




## Usage 
### CLI Example
```bash
python backend/cli.py --question "How do I get OPT as an F-1 student?"
```


### Web UI Example
1. Start the backend
```bash
uvicorn backend.main:app --reload --port 9000
```
2. In another terminal
```bash
cd frontend
npm install
npm run dev
```
3. Open your browser at [http://localhost:5173](http://localhost:5173) to chat with AskImmigrate 2.0 in the web UI.

## Running Tests

After installation and setup, run all tests with:

```bash
pytest tests/
```

## Methodology

1. **Ingestion:** Splits PDFs/JSON to text chunks for RAG

2. **Embedding:** Uses HuggingFace MiniLM for vectorization

3. **Indexing:** Stores embeddings in Chroma vector DB

4. **Prompting:** Builds system/user prompts via LangChain

5. **Query:** Semantic search + LLM call to generate answers



# Performance 
- **Ingestion:** ~100 documents/min on typical hardware

- **Query:** <500 ms/response (GPU-enabled backend)

- **Embedding:** 768-dim vectors per chunk



## Agent and Responsibilities
| Agent           | Main Responsibility                             |
| --------------- | ----------------------------------------------- |
| Intake Agent    | Parse/understand user’s scenario, visa, country |
| Research Agent  | Retrieve rules, requirements, and forms         |
| Tool Agent      | PDF parsing, fee calculation, eligibility check |
| Checklist Agent | Build custom checklist of steps/docs            |
| Output Agent    | Synthesize and present answers                  |



## State Structure

See `backend/agentic_state.py` for field definitions.



## Contributing

- Fork the repo, branch for each feature/agent
- Commit clear messages, PR to main
- See the Project Board for assignments and progress



## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.



## Maintainers and Contact

Maintainers:&#x20;

1. Geoffrey Duncan Opiyo ([dunkygeoffrey39@gmail.com](mailto\:dunkygeoffrey39@gmail.com))

2. Justine Okumu ([okumujustine01@gmail.com](mailto\:okumujustine01@gmail.com))

3. Deo Mugabe([deo.mugabe7@gmail.com](mailto\:deo.mugabe7@gmail.com))

4. Hillary Arinda ([arinda.hillary@gmail.com](mailto\:arinda.hillary@gmail.com))

   GitHub Issues: [https://github.com/okumujustine/AskImmigrate/issues](https://github.com/dunky-star/AskImmigrate/issues)



## Changelog
`v2.0.0 (July 2025)`: Multi-agent architecture, new checklists, improved CLI & web UI


## Citation
If you use AskImmigrate2.0 in academic work, please cite:
Geoffrey Duncan Opiyo, Justine Okumu, Deo Mugabe, Hillary Arinda (2025). AskImmigrate: An AI-powered multi-agent chat assistant for U.S. immigration. GitHub. https://github.com/okumujustine/AskImmigrate2.0



