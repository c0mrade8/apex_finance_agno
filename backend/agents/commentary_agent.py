from agno.agent import Agent
from agno.models.groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize model
model=Groq(id="llama-3.3-70b-versatile") # your model ID here
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

# Create agent
commentary_agent = Agent(
    name="CommentaryAgent",
    model=model,
    instructions="""
    You are a financial analyst.

    Given a variance in financial data,
    explain the reason in a professional tone.
    Keep it concise (2-3 lines).
    """
)


def generate_commentary(company, account, variance_pct):

    prompt = f"""
    Company: {company}
    Account: {account}
    Variance: {variance_pct:.2f}%

    Explain the reason for this variance.
    """

    response = commentary_agent.run(prompt)

    return response.content