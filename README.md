# AI4Ed Turing Project

## Multi-Agent Systems for Multi-Party Human-AI Interaction

A research project investigating how multi-agent systems can enhance essay writing through collaborative AI interactions.

### Team Members
- Alan O'Connell
- Don Rasula Dhakshaka Atapattu
- Raymon JS Narwal

**Supervisor:** Zheng Yuan

### Project Overview

This project develops a prototype system with three interconnected modules to support student essay writing:

1. **Planning Module** - Pre-writing discussions with multiple AI agents (facilitator, challenger, supporter) to help students brainstorm ideas and explore diverse perspectives
2. **Assessment Module** - Automated band-like scoring aligned with writing rubrics (IELTS, TOEFL)
3. **Feedback Module** - Surface-level corrections and deeper guidance on coherence, organization, and argument quality

### Key Features

- Multi-agent collaboration with different AI personas representing various cultural and linguistic backgrounds
- Critic agents for evaluation and feedback
- Integration with existing assessment and feedback systems
- Flexible, expandable design for future enhancements

### Technical Approach

- Prioritizing local LLM models (privacy concerns, especially for minors)
- Flexible implementation allowing easy model switching
- Limited OpenAI credits ($2000) available for testing

### Project Timeline

**Semester 1 (Weeks 1-12)**
- Week 1-3: Team forming and project setup
- Week 4-10: Research and development
- Week 11: Interim presentation
- Week 12: Interim report

**Semester 2 (Weeks 1-12)**
- Week 1-10: Continued development
- Week 11: Final presentation
- Week 12: Final report

### Getting Started

#### Prerequisites

- Python 3.12 or higher
- [UV package manager](https://docs.astral.sh/uv/)
- OpenAI API key

#### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd AI4ED-turing-project
```

2. Install dependencies using UV:
```bash
uv sync
```

3. Activate the Environment:
```bash
source .venv/bin/activate
```

4. Set up environment variables:
Create a `.env` file in the project root (get from folder in google drive):
```bash
OPENAI_API_KEY=your_api_key_here
```


#### Running the Application

You can choose between two user interfaces:

**Option 1: Rich Console UI (Recommended)**

Modern, interactive terminal interface with colored panels, spinners, and conversation history:

```bash
# Interactive mode (will prompt for subject)
uv run python -m bin.RichUI.app

# With subject specified
uv run python -m bin.RichUI.app --subject "Social media and mental health"
```

Features:
- Live conversation display with color-coded Rich panels
- Typing indicators/spinners during LLM processing
- Conversation history scrollback (last 5 turns)
- Multi-line input support (use `>>>` to finish)
- Commands: `/help`, `/clear`, `/quit`

See `bin/RichUI/README.md` for detailed usage guide.

**Option 2: Basic CLI**

Simple command-line interface (original):

```bash
uv run python -m bin.MultiAgentSystem.app
```

This runs a demo conversation where a facilitator agent helps a student brainstorm an essay about social media's impact on mental health.

**Option 4 : (MOST RECENT) SERVER AND FRONTEND**

first from project root folder run:

```bash
uvicorn bin.MultiAgentSystem.app:app --reload --host 127.0.0.1 --port 8000
```

now inorder to run the front end naviagate to the bin/MultiAgentSystem Folder
```bash
cd bin/MultiAgentSystem
```

After run the front end using :
```bash
streamlit run front_end.py
```


Now you should be able to see the chat interface loaded up if you follow the URL into your browser.

**Option 5: Docker (recommended for deployment)**

Requires [Docker](https://docs.docker.com/get-docker/) and Docker Compose.

1. Copy the example env file and fill in your API keys:
```bash
cp .env.example .env
```

2. Build and start both services:
```bash
docker compose up --build
```

The backend will be available at `http://localhost:8000` and the frontend at `http://localhost:8501`.

To stop:
```bash
docker compose down
```

**Option 6: WrAFT — Writing Assessment & Feedback Tool**

Requires Docker and Docker Compose. Run from the `wraft/` directory.

1. Create the secrets file from the example:
```bash
cp wraft/.envs/.local/.secrets.example wraft/.envs/.local/.secrets
```

2. Fill in your API keys in `wraft/.envs/.local/.secrets`:
```
OPENAI_API_KEY=<finetuned 4o key — get from .env>
ANTHROPIC_API_KEY=<your Anthropic key>
```
> **Note:** Both keys are required. `surface_correction` and `score` use the finetuned GPT-4o model; `macro_correction` and `micro_correction` use Claude 3.7 Sonnet.

3. Build and start all services:
```bash
cd wraft
make build-local
make start-local
```

4. Initialise LLM configs and API keys in the database (first run only):
```bash
make init-data-local
```

5. Access the services:
   - Frontend: http://localhost:5173
   - Backend admin: http://localhost:8000/admin (user: `admin`, password: `MyPass123`)
   - Email testing: http://localhost:8025

To stop:
```bash
make stop-local
```

#### Project Structure

```
.
├── bin/
│   ├── MultiAgentSystem/          # Core multi-agent system (backend)
│   │   ├── agents.py              # Agent persona definitions
│   │   ├── llm_connector.py       # OpenAI/LangChain integration
│   │   ├── ochestrator.py         # LangGraph multi-agent orchestration
│   │   ├── prompts.py             # Prompt building utilities
│   │   └── app.py                 # Basic CLI application
│   └── RichUI/                    # Rich Console UI (frontend)
│       ├── console_ui.py          # Main UI orchestrator
│       ├── conversation_manager.py # Message history tracking
│       ├── input_handler.py       # Multi-line input handling
│       ├── display_renderer.py    # Rich panels and formatting
│       ├── app.py                 # Rich UI entry point
│       └── README.md              # Rich UI documentation
├── main.py                        # Project entry point
├── pyproject.toml                 # Project dependencies and metadata
└── readme.md                      # This file
```

### Resources

- **Module:** COM4520 Turing Research Project
- **Academic Year:** 2025/2026
- **University:** University of Sheffield, Computer Science Department

### Ethics

This project will follow the University of Sheffield's Ethics Review Procedure with appropriate consent forms and data protection measures.

---

*This is an early-stage research project. Documentation and features will be updated as development progresses.*
