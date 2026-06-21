import os
from pydantic import BaseModel, Field
from typing import Literal
from agno.agent import Agent
from agno.models.groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Enforce a machine-readable structured schema contract
class CommentaryPackage(BaseModel):
    variance_classification: Literal["FAVORABLE", "UNFAVORABLE", "NEUTRAL"] = Field(description="The strategic classification of the financial deviation")
    forensic_hypothesis: str = Field(description="A concise, 2-3 line senior analyst level explanation of the variance reason")
    recommended_next_step: str = Field(description="Actionable follow-up verification step for the portfolio management team")


class VarianceCommentaryAgent:

    def __init__(self):
        """
        Initializes the thread-safe standalone Agno agent wrapper bound to Groq.
        """
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise ValueError("❌ Missing CRITICAL environment variable: GROQ_API_KEY")
            
        self.model = Groq(id="llama-3.3-70b-versatile", api_key=groq_key)
        
        self.agent = Agent(
            name="CommentaryAgent",
            model=self.model,
            instructions=[
                "You are an elite Private Equity Senior Financial Analyst and Forensic Auditor.",
                "Given a variance deviation payload across a corporate ledger line item, formulate a professional operational hypothesis.",
                "Ensure your forensic commentary remains exactly 2 to 3 lines long, highly technical, and completely devoid of fluff.",
                "Determine if the change represents a Favorable, Unfavorable, or Neutral operational shift based on standard normal balance rules."
            ]
        )

    def generate_commentary(self, company: str, account: str, account_type: str, current_bal: float, prior_bal: float) -> CommentaryPackage:
        """
        Executes a high-efficiency single-pass structured inference call to generate closing variance commentary.
        """
        delta = current_bal - prior_bal
        variance_pct = (delta / (abs(prior_bal) + 1e-6)) * 100

        prompt = f"""
        Execute forensic variance analysis for the following ledger endpoint entry:
        
        • Portfolio Company: {company}
        • Targeted Ledger Account: {account} (Type Classification: {account_type})
        • Current Closing Balance: ${current_bal:,.2f}
        • Prior Baseline Balance: ${prior_bal:,.2f}
        • Absolute Net Delta: ${delta:,.2f}
        • Calculated Horizontal Variance: {variance_pct:.2f}%
        
        Analyze the metric, evaluate the scale of the drift, and populate the requested response model structure cleanly.
        """

        # Force structural schema formatting alignment natively
        response = self.agent.run(prompt, response_model=CommentaryPackage)

        return response.content