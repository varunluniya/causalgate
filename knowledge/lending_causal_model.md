# Dealer Point-of-Sale Lending: Causal Model

## Variables
Income stability, debt-to-income, down payment chosen, dealer, region, product price, payment reminders, and default.

## Known confounders
Income stability drives both the down payment an applicant can afford and their chance of default.
So the observed link between low down payment and default is partly confounded by income.
Region drives both which dealer an applicant uses and local default rates.

## Selection effects
Applicants self-select into down payment levels. A policy that forces a higher minimum down payment changes who applies at all:
some lower-income applicants drop out and others borrow elsewhere. The observed 2x difference is not the effect of the policy.

## Correlation questions (Level 1)
"Does this applicant belong to a group with higher observed default?" can be answered from historical data alone.

## Intervention questions (Level 2)
"What happens if we change the policy?" needs either a causal model that adjusts for confounders, or an experiment:
a randomised pilot, an A/B test, or a holdout group. Comparing people who opted into something with people who did not is biased.

## Counterfactual questions (Level 3)
"Would this specific borrower have defaulted under a different choice?" cannot be read off population data.
It needs an individual-level structural model and explicit assumptions, and the answer is a probability, not a certainty.
Customers removed by a policy (for example, a dealer ban) would partly have borrowed elsewhere, so the portfolio counterfactual must model substitution.

## Deployment implication
Correlation-level tasks can be automated when accuracy is high. Intervention and counterfactual tasks need human review,
a compensating design (confidence gating, explicit uncertainty), or an experiment before the model's answer is acted on.
