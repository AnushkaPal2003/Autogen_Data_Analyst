import os
import re
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
    Runs the complete AG2 pipeline.

    Flow

    User
      ↓
    Analyst
      ↓
    Executor
      ↓
    Analyst
      ↓
    Reviewer
      ↓
    API Response
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

    code_executor = build_executor_agent(executor)

    reviewer = build_reviewer_agent(LLM_CONFIG)

    task = f"""
You are given a CSV dataset.

CSV Path

{csv_path}

User Question

{question}

================================================

IMPORTANT

Read the user's request carefully.

Your answer MUST satisfy EVERY requirement.

Examples

If user asks

Generate heatmap

Generate heatmap.

If user asks

Give 5 insights

Return EXACTLY FIVE insights.

If user asks

Find top 10

Return EXACTLY TEN.

Never ignore any request.

================================================

Execution Rules

1. Load CSV with pandas.

2. Inspect available columns.

3. Perform calculations.

4. Never guess.

5. Never use prior knowledge.

6. Base conclusions ONLY on computed values.

7. Save every chart as

chart.png

8. Execute Python before writing conclusions.

================================================

Final Response

Executive Summary

Key Insights

Recommendations (if requested)

End with

TERMINATE
"""

    chat_result = code_executor.initiate_chat(
        analyst,
        message=task,
        max_turns=MAX_TURNS,
        summary_method="last_msg",
    )

    transcript = chat_result.chat_history

    conversation = []

    generated_code = ""

    execution_output = ""

    final_summary = ""

    for msg in transcript:

        name = msg.get("name", "")

        content = msg.get("content", "")

        conversation.append(
            f"{name}\n{content}"
        )

        if "```python" in content:
            generated_code = content

        if name == "code_executor":
            execution_output += "\n" + content

    conversation = "\n\n".join(conversation)

    final_summary = _extract_final_summary(transcript)

    chart_path = os.path.join(
        work_dir,
        "chart.png",
    )
        review_prompt = f"""
You are reviewing a completed data analysis.

User Question

{question}

==============================

Analyst Final Answer

{final_summary}

==============================

Execution Output

{execution_output}

==============================

Review Checklist

1. Did the analyst answer every part of the user's question?

2. If the user requested N insights,
were exactly N provided?

3. Are conclusions supported by execution output?

4. Are statistics actually computed?

5. Are correlations actually computed?

6. If a chart was requested,
did the analyst discuss it?

7. Reject if Python code appears.

8. Reject if traceback appears.

9. Reject if installation logs appear.

10. Reject hallucinations.

Reply ONLY in this format

APPROVED

or

REJECTED

Then explain why.
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

    approved = review_reply.upper().startswith("APPROVED")

    return {
        "run_id": run_id,
        "summary": final_summary,
        "generated_code": generated_code,
        "execution_output": execution_output,
        "chart_path": chart_path if os.path.exists(chart_path) else None,
        "approved": approved,
        "review_feedback": review_reply,
        "transcript": transcript,
    }


def _extract_final_summary(transcript):
    """
    Returns the analyst's final business summary only.

    Removes:
    - python code
    - TERMINATE
    - traceback
    - pip install logs
    """

    for msg in reversed(transcript):

        if msg.get("name") != "data_analyst":
            continue

        content = msg.get("content", "")

        if not content:
            continue

        # remove python blocks
        content = re.sub(
            r"```python.*?```",
            "",
            content,
            flags=re.DOTALL,
        )

        # remove any fenced code
        content = re.sub(
            r"```.*?```",
            "",
            content,
            flags=re.DOTALL,
        )

        # remove TERMINATE
        content = re.sub(
            r"TERMINATE",
            "",
            content,
            flags=re.IGNORECASE,
        )

        # remove traceback
        content = re.sub(
            r"Traceback[\s\S]*",
            "",
            content,
            flags=re.MULTILINE,
        )

        # remove pip install lines
        cleaned = []

        for line in content.splitlines():

            lower = line.lower()

            if "pip install" in lower:
                continue

            if "subprocess.check_call" in lower:
                continue

            if "sys.executable" in lower:
                continue

            if line.strip().startswith("import "):
                continue

            if line.strip().startswith("from "):
                continue

            cleaned.append(line)

        content = "\n".join(cleaned).strip()

        if content:
            return content

    return ""
