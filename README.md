# AutoGen Data Analyst

A multi-agent data analysis assistant built with AutoGen. Upload a CSV, ask a
question in plain English, and a team of agents writes and runs the pandas
code needed to answer it — including generating a chart when useful.

---

## Architecture

```
User Question + CSV
        |
   FastAPI /analyze
        |
   data_analyst  <--code + result-->  code_executor (sandboxed subprocess)
        | (loops until analyst is satisfied, or MAX_TURNS reached)
        v
   final summary
        |
     reviewer  --> APPROVED or feedback
        |
   JSON response --> Streamlit frontend (summary + chart + approval)
```

- **data_analyst** — writes one Python code block per turn (pandas + matplotlib)
  to answer the question, and produces a plain-English summary once done.
- **code_executor** — runs that code in an isolated working directory per
  request using AutoGen's `LocalCommandLineCodeExecutor`, and returns
  stdout/stderr back to the analyst so it can self-correct on errors.
- **reviewer** — a one-shot check on the analyst's final summary, to catch
  answers that don't actually address the question.

---

## Tech Stack

| Component        | Tool                              |
|-------------------|------------------------------------|
| Agent framework   | AutoGen (pyautogen)                |
| Code execution     | AutoGen `LocalCommandLineCodeExecutor` |
| LLM                | Groq Llama 3.3 70B                 |
| Analysis           | pandas, matplotlib                 |
| Backend API        | FastAPI                            |
| Frontend           | Streamlit                          |

---

## Folder Structure

```
autogen_data_analyst/
├── backend/
│   ├── config.py     -> env vars, LLM config, constants
│   ├── agents.py      -> factory functions for the 3 agents
│   ├── executor.py    -> sandboxed code executor factory
│   ├── pipeline.py    -> orchestrates the analyst/executor/reviewer flow
│   └── main.py         -> FastAPI app (/analyze, /chart/{run_id})
├── frontend/
│   └── app.py           -> Streamlit UI
├── requirements.txt
└── .env.example
```


## Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Create `.env`** (copy `.env.example`)
```
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile
WORK_DIR_ROOT=runs
MAX_TURNS=6
```

**3. Run the backend**
```bash
cd backend
uvicorn main:app --reload
```
Swagger UI: http://localhost:8000/docs

**4. Run the frontend** (in a separate terminal)
```bash
cd frontend
streamlit run app.py
```

Backend: http://localhost:8000 · Frontend: http://localhost:8501
