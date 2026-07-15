from autogen import ConversableAgent

ANALYST_SYSTEM_MESSAGE = """You are a data analyst.
You are given the path to a CSV file and a business question.

Follow this turn-by-turn process strictly:

1. Load the CSV with pandas using the exact path given in the task.
2. Write ONE Python code block that computes what is needed to answer the
   question. If a chart would help, save it as chart.png in the current
   working directory using matplotlib (do not call plt.show()). Send ONLY
   this code block in this message. Do not add a summary and do not write
   TERMINATE in this message.
3. Wait for the executor to run the code and return its output.
4. Look at the executor's output. If it shows an error, fix the code and
   send a corrected code block (again, code only, no TERMINATE).
5. Once the output looks correct, send a final message with NO code block:
   just a short, plain-English summary (2-4 sentences) of the finding,
   ending with the single word TERMINATE on its own line.

Important: never put a code block and the word TERMINATE in the same
message. TERMINATE only belongs in the final, code-free summary message,
sent after you have seen correct execution output.

Only use pandas, matplotlib, and the Python standard library. Do not invent
columns that are not in the data. Keep code short and readable.
"""

REVIEWER_SYSTEM_MESSAGE = """You are a careful reviewer for data analysis results.
You will be given the original question and the analyst's final summary.

Check that the summary:
- Directly answers the question asked.
- Is consistent with what a correct analysis of the data would show.
- Does not overstate confidence or invent numbers.

Reply with the single word APPROVED if the summary is acceptable.
Otherwise, reply with a short, specific explanation of what is wrong or missing
so the analyst can fix it. Do not rewrite the analysis yourself.
"""


def build_data_analyst_agent(llm_config: dict) -> ConversableAgent:
    """Agent that writes pandas/matplotlib code to answer a question about a CSV."""
    return ConversableAgent(
        name="data_analyst",
        system_message=ANALYST_SYSTEM_MESSAGE,
        llm_config=llm_config,
        human_input_mode="NEVER",
    )


def build_executor_agent(executor) -> ConversableAgent:
    """Agent that runs the analyst's code in a sandboxed executor and returns output."""
    return ConversableAgent(
        name="code_executor",
        llm_config=False,
        code_execution_config={"executor": executor},
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: "TERMINATE" in (msg.get("content") or "").upper(),
    )


def build_reviewer_agent(llm_config: dict) -> ConversableAgent:
    """Agent that does a one-shot sanity check on the analyst's final summary."""
    return ConversableAgent(
        name="reviewer",
        system_message=REVIEWER_SYSTEM_MESSAGE,
        llm_config=llm_config,
        human_input_mode="NEVER",
    )