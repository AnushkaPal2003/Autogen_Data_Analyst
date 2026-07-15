import os
import uuid

from config import LLM_CONFIG, MAX_TURNS, CODE_TIMEOUT_SECONDS, WORK_DIR_ROOT
from agents import build_data_analyst_agent, build_executor_agent, build_reviewer_agent
from executor import build_executor


def run_analysis(csv_path: str, question: str) -> dict:
    """
    Runs the full pipeline for one CSV + one question:
      1. data_analyst and code_executor go back and forth: analyst writes code,
         executor runs it, until the analyst is satisfied or MAX_TURNS is hit.
      2. reviewer does a one-shot sanity check on the analyst's final summary.

    Returns a dict with: summary, chart_path, approved, review_feedback, transcript.
    """
    run_id = str(uuid.uuid4())[:8]
    work_dir = os.path.join(WORK_DIR_ROOT, run_id)
    os.makedirs(work_dir, exist_ok=True)

    csv_path = os.path.abspath(csv_path)

    executor = build_executor(work_dir=work_dir, timeout=CODE_TIMEOUT_SECONDS)

    analyst = build_data_analyst_agent(LLM_CONFIG)
    code_runner = build_executor_agent(executor)
    reviewer = build_reviewer_agent(LLM_CONFIG)

    task = (
        f"CSV file path: {csv_path}\n"
        f"Question: {question}\n\n"
        "Load the CSV with pandas, answer the question, save any useful chart "
        "as chart.png in the current directory, and finish with a short summary."
    )

    chat_result = code_runner.initiate_chat(
        analyst,
        message=task,
        max_turns=MAX_TURNS,
        summary_method="last_msg",
    )

    transcript = chat_result.chat_history
    final_summary = chat_result.summary or _last_message_from(transcript, "data_analyst")

    review_reply = reviewer.generate_reply(
        messages=[
            {
                "role": "user",
                "content": f"Question: {question}\n\nAnalyst's final summary:\n{final_summary}",
            }
        ]
    )
    # generate_reply can return either a plain string or a dict like
    # {"content": ..., "role": ...} depending on the installed AutoGen version.
    if isinstance(review_reply, dict):
        review_reply = review_reply.get("content", "")
    review_reply = review_reply or ""
    approved = "APPROVED" in review_reply.upper()

    chart_path = os.path.join(work_dir, "chart.png")

    return {
        "run_id": run_id,
        "summary": final_summary,
        "chart_path": chart_path if os.path.exists(chart_path) else None,
        "approved": approved,
        "review_feedback": review_reply,
        "transcript": transcript,
    }


def _last_message_from(transcript: list, sender_name: str) -> str:
    """Fallback: pull the last message sent by a given agent from the chat history."""
    for msg in reversed(transcript):
        if msg.get("name") == sender_name and msg.get("content"):
            return msg["content"]
    return ""