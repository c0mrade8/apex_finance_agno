import uuid
from core.state_manager import set_agent_status
from models.intercompany import IntercompanyTransaction
from models.alert import Alert


class IntercompanyAgent:

    def __init__(self, db, agent):
        self.db = db
        self.agent = agent

    def run(self, period):

        try:
            set_agent_status("IntercompanyAgent", "GLOBAL", "STARTED")

            # filter by period
            txns = self.db.query(IntercompanyTransaction).filter_by(period=period).all()

            if not txns:
                set_agent_status("IntercompanyAgent", "GLOBAL", "COMPLETED")
                return

            #group by entity pair
            pairs = {}

            for t in txns:
                pair_key = tuple(sorted([t.selling_entity_id, t.buying_entity_id]))

                pairs.setdefault(pair_key, []).append({
                    "from_id": t.selling_entity_id,
                    "to_id": t.buying_entity_id,
                    "from_name": t.selling_entity_name,
                    "to_name": t.buying_entity_name,
                    "amount": float(t.amount),
                    "description": t.description
                })

            #processing of each pair
            for pair_key, pair_txns in pairs.items():

                entity_a, entity_b = pair_key

                seller_total = sum(t["amount"] for t in pair_txns if t["from_id"] == entity_a)
                buyer_total = sum(t["amount"] for t in pair_txns if t["to_id"] == entity_a)

                net_imbalance = abs(seller_total - buyer_total)

                if net_imbalance< 1:
                    continue

                # 4. Severity logic
                if net_imbalance > 100000:
                    severity = "CRITICAL"
                elif net_imbalance> 10000:
                    severity = "HIGH"
                else:
                    severity = "MEDIUM"

                # 5. LLM reasoning
                prompt = f"""
                Intercompany Transactions: {pair_txns}

                Net imbalance: {net_imbalance}

                Tasks:
                - Explain mismatch
                - Financial risk
                - Suggest elimination journal entry
                """

                response = self.agent.run(prompt)

                # 6. Alert
                self.create_alert(
                    "GLOBAL",
                    f"Intercompany imbalance {net_imbalance}: {response.content}",
                    severity
                )

                # 7. Log
                self.save_log("IntercompanyAgent", response.content)

            self.db.commit()

            set_agent_status("IntercompanyAgent", "GLOBAL", "COMPLETED")

        except Exception as e:
            self.db.rollback()
            set_agent_status("IntercompanyAgent", "GLOBAL", "FAILED")
            print(f"Intercompany Error: {e}")

    def create_alert(self, company_id, message, severity):

        self.db.add(Alert(
            id=str(uuid.uuid4()),
            company_id=company_id,
            message=message,
            severity=severity
        ))

    def save_log(self, agent, message):

        from models.agent_log import AgentLog
        import datetime

        self.db.add(AgentLog(
            id=str(uuid.uuid4()),
            agent_name=agent,
            message=message,
            timestamp=str(datetime.datetime.now())
        ))