import uuid
from core.state_manager import set_agent_status
from models.intercompany import IntercompanyTransaction
from models.alert import Alert
from pydantic import BaseModel, Field
from typing import List, Literal
from models.agent_log import AgentLog
import datetime

class IntercompanyMatchInsight(BaseModel):
    seller_entity: str = Field(description="The selling entity identifier")
    buyer_entity: str = Field(description="The buying entity identifier")
    variance_explanation: str = Field(description="Forensic hypothesis explaining the intercompany mismatch asymmetry")
    elimination_entry_debit: str = Field(description="The required target account code and value to debit for ledger elimination")
    elimination_entry_credit: str = Field(description="The required target account code and value to credit for ledger elimination")
    severity: Literal["MEDIUM", "HIGH", "CRITICAL"] = Field(description="Determined transactional error severity rating")

class IntercompanyReconciliationPackage(BaseModel):
    executive_summary: str = Field(description="Fund controller level macro summary of group intercompany matching positions")
    reconciliation_records: List[IntercompanyMatchInsight] = Field(default=[], description="Array of structural matching corrections per entity pair")

class IntercompanyAgent:

    def __init__(self, db, agent_instance):
        """
        db = Thread-isolated global database session instance passed by Orchestrator
        agent_instance = Agno Agent model instance bound to Groq
        """
        self.db = db
        self.agent = agent_instance

    def run(self, period) -> bool:

        try:
            set_agent_status("IntercompanyAgent", "GLOBAL", "STARTED")

            # filter by period
            txns = self.db.query(IntercompanyTransaction).filter_by(period=period).all()

            if not txns:
                self.save_log("GLOBAL", "IntercompanyAgent", f"No intercompany transaction records found for period {period}")
                set_agent_status("IntercompanyAgent", "GLOBAL", "COMPLETED")
                return True
            
            #Map reciprocal positions precisely: (Seller, Buyer) -> Cumulative Total
            reciprocal_map = {}
            for t in txns:
                key = (t.selling_entity_id, t.buying_entity_id)
                reciprocal_map[key] = reciprocal_map.get(key, 0.0) + float(t.amount)

            # Extract distinct unique entity links to build distinct pairs
            all_entities = list(set([t.selling_entity_id for t in txns] + [t.buying_entity_id for t in txns]))
            processed_pairs = set()
            flagged_discrepancies_batch = []

            for entity_a in all_entities:
                for entity_b in all_entities:
                    if entity_a == entity_b or (entity_b, entity_a) in processed_pairs:
                        continue

                    pair_token=tuple(sorted([entity_a, entity_b]))
                    if pair_token in processed_pairs:
                        continue
                    processed_pairs.add(pair_token)

                    # Extract true counterparty tracking directional metrics
                    a_to_b_sales = reciprocal_map.get((entity_a, entity_b), 0.0)
                    b_to_a_sales = reciprocal_map.get((entity_b, entity_a), 0.0)

                    # In balanced records, A's sales to B must perfectly offset B's purchases from A
                    net_imbalance = abs(a_to_b_sales - b_to_a_sales)

                    # Account limit variance checkpoint
                    if net_imbalance > 1.0:
                        flagged_discrepancies_batch.append({
                            "entity_a": entity_a,
                            "entity_b": entity_b,
                            "directional_flow_a_to_b": float(a_to_b_sales),
                            "directional_flow_b_to_a": float(b_to_a_sales),
                            "asymmetric_variance": float(net_imbalance)
                        })

            if not flagged_discrepancies_batch:
                self.save_log("GLOBAL", "IntercompanyAgent", f"All multi-entity reciprocal intercompany positions matched perfectly for period {period}.")
                set_agent_status("IntercompanyAgent", "GLOBAL", "COMPLETED")
                return True
            
            prompt = f"""
            You are a lead Private Equity Fund Controller auditing group intercompany matching parameters for a multi-entity corporate portfolio during closing period '{period}'.
            
            Reciprocal balance verification has identified asymmetric matching variances between entity ledger endpoints. 
            
            Analyze the attached batch payload array. For each broken counterparty link:
            1. Formulate a forensic explanation accounting for the ledger variance asymmetry.
            2. Suggest the matching double-entry elimination journal correction needed to true-up and drop out the cross-company positions completely before consolidation.

            Flagged Intercompany Variance Payload Array:
            {flagged_discrepancies_batch}
            """

            response = self.agent.run(prompt, response_model=IntercompanyReconciliationPackage)
            if isinstance(response.content, str):
                self.save_log("GLOBAL", "IntercompanyAgent", f"Intercompany validation fallback string caught: {response.content}")
                set_agent_status("IntercompanyAgent", "GLOBAL", "FAILED")
                return False
            structured_output: IntercompanyReconciliationPackage = response.content
            self.save_log("GLOBAL", "IntercompanyAgent", structured_output.executive_summary)

            for record in structured_output.reconciliation_records:
                alert_payload = (
                    f"Intercompany Asymmetric Variance [{record.seller_entity} <-> {record.buyer_entity}]:\n"
                    f"• Forensic Match Analysis: {record.variance_explanation}\n"
                    f"• Proposed Elimination Debit: {record.elimination_entry_debit}\n"
                    f"• Proposed Elimination Credit: {record.elimination_entry_credit}"
                )
                self.create_alert("GLOBAL", alert_payload, record.severity)

            set_agent_status("IntercompanyAgent", "GLOBAL", "COMPLETED")

            return True

        except Exception as e:
            self.db.rollback()
            set_agent_status("IntercompanyAgent", "GLOBAL", "FAILED")
            print(f"XXX Error in IntercompanyAgent: {e}")
            return False

    def create_alert(self, company_id, message, severity):

        self.db.add(Alert(
            id=str(uuid.uuid4()),
            company_id=company_id,
            message=message,
            severity=severity
        ))

    def save_log(self, company_id, agent, message):


        self.db.add(AgentLog(
            id=str(uuid.uuid4()),
            agent_name=agent,
            company_id=company_id,
            message=message,
            timestamp=str(datetime.datetime.now())
        ))