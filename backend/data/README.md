# Assignment 1: Month-End Close Sample Data

## Dataset Overview
This dataset contains realistic financial data for 8 portfolio companies spanning 3 months (Nov 2025 - Jan 2026).

## Generated: 2026-03-16 22:54:34

## Directory Structure
```
./data/
├── trial_balances/       # Monthly trial balances for each company
├── budgets/             # 2026 annual budgets
├── prior_year/          # Prior year comparatives (2024-2025)
├── intercompany/        # Intercompany transactions requiring elimination
├── bank_statements/     # Mock bank statements
├── accrual_schedules/   # Standard accrual templates
└── company_metadata.json # Company profiles
```

## Portfolio Companies
- TechForge SaaS: $45,000,000 revenue, SaaS
- PrecisionMfg Inc: $120,000,000 revenue, Manufacturing
- RetailCo: $200,000,000 revenue, Retail
- HealthServices Plus: $35,000,000 revenue, Healthcare Services
- LogisticsPro: $80,000,000 revenue, Transportation
- IndustrialSupply Co: $150,000,000 revenue, Distribution
- DataAnalytics Corp: $25,000,000 revenue, Professional Services
- EcoPackaging Ltd: $60,000,000 revenue, Manufacturing

## Data Validation
Total trial balances generated: 24
Total budget records: 1548
Total intercompany transactions: 3000
Total accrual schedules: 1008

## Known Issues (Intentional for Testing)
1. Some expenses may be miscategorized (e.g., marketing in COGS)
2. Missing accruals in December (bonus accrual not booked)
3. Some intercompany transactions missing elimination entries
4. Timing differences in prepaid expenses

## Loading Instructions
```python
import pandas as pd

# Load trial balance
tb = pd.read_csv('trial_balances/techforge_saas_2026_01.csv')

# Validate it balances
assert abs(tb['debit'].sum() - tb['credit'].sum()) < 0.01

# Load all budgets
budgets = pd.read_csv('budgets/budgets_2026.csv')
```

## Questions?
See main assignment document or contact hello@talentdeel.com
