import os
import uuid

from config import (
    LLM_CONFIG,
    MAX_TURNS,
    CODE_TIMEOUT_SECONDS,
    WORK_DIR_ROOT,
)
from agents import (
    build_data_analyst_agent,
    build_executor_agent,
    build_reviewer_agent,
)
from executor import build_executor


def run_analysis(csv_path: str, question: str) -> dict:
    """
    Multi-agent pipeline

    1. Data Analyst writes pandas/matplotlib code.
    2. Executor executes the code.
    3. Analyst iterates until satisfied.
    4. Reviewer validates the entire analysis.

    Returns:
        summary
        chart_path
        generated_code
        transcript
        review_feedback
        approved
    """

    run_id = str(uuid.uuid4())[:8]

    work_dir = os.path.join(WORK_DIR_ROOT, run_id)
    os.makedirs(work_dir, exist_ok=True)

    csv_path = os.path.abspath(csv_path)

    executor = build_executor(
        work_dir=work_dir,
        timeout=CODE_TIMEOUT_SECONDS,
    )

    analyst = build_data_analyst_agent(LLM_CONFIG)
    code_runner = build_executor_agent(executor)
    reviewer = build_reviewer_agent(LLM_CONFIG)

    task = f"""
You are a professional Data Analyst.

CSV file:
{csv_path}

User Question:
{question}

Instructions:

1. Load the CSV using pandas.
2. Perform ALL calculations using Python.
3. Never guess.
4. Never rely on prior knowledge.
5. Base every conclusion ONLY on computed values.
6. If correlation is requested, compute the correlation matrix.
7. If statistics are requested, calculate them.
8. If a chart is useful, generate it using matplotlib and save it as:

chart.png

9. Always execute the code before giving conclusions.

10. Your final response should contain:

- Analysis
- Key findings
- Numerical evidence
- Short summary

Do NOT invent numbers.
"""

    chat_result = code_runner.initiate_chat(
        analyst,
        message=task,
        max_turns=MAX_TURNS,
        summary_method="last_msg",
    )

    transcript = chat_result.chat_history

    final_summary = (
        chat_result.summary
        or _last_message_from(transcript, "data_analyst")
    )

    generated_code = ""

    conversation = []

    for msg in transcript:

        name = msg.get("name", "unknown")
        content = msg.get("content", "")

        conversation.append(
            f"{name}:\n{content}"
        )

        if "```python" in content:
            generated_code = content

    conversation = "\n\n".join(conversation)

    review_prompt = f"""
You are a Senior Data Scientist.

Your task is to review the analyst's work.

Question:

{question}

Conversation:

{conversation}

Analyst Summary:

{final_summary}

Instructions:

- Verify whether the conclusions follow from the executed Python output.
- Reject unsupported claims.
- Reject hallucinations.
- Verify statistics and correlations.
- If evidence is insufficient, reject.

Reply ONLY in this format:

APPROVED

or

REJECTED

Then explain your reasoning.
"""

    review_reply = reviewer.generate_reply(
        messages=[
            {
                "role": "user",
                "content": review_prompt,
            }
        ]
    )

    if isinstance(review_reply, dict):
        review_reply = review_reply.get("content", "")

    review_reply = review_reply or ""

    approved = "APPROVED" in review_reply.upper()

    chart_path = os.path.join(work_dir, "chart.png")

    return {
        "run_id": run_id,
        "summary": final_summary,
        "generated_code": generated_code,
        "chart_path": chart_path if os.path.exists(chart_path) else None,
        "approved": approved,
        "review_feedback": review_reply,
        "transcript": transcript,
    }


def _last_message_from(transcript, sender_name):
    """
    Returns the last message sent by an agent.
    """

    for msg in reversed(transcript):

        if (
            msg.get("name") == sender_name
            and msg.get("content")
        ):
            return msg["content"]

    return ""
