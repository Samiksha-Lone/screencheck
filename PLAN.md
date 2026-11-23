# ScreenCheck — Research Plan

**Project:** ScreenCheck  
**Document:** Research plan  
**Status:** Initial plan — written before running experiments  
**Scope:** Version 1, six core experiments

## 1. Purpose

ScreenCheck is a controlled lab for testing resume screeners that we build ourselves.

The project will create synthetic resumes with known skills and experience, build three simple screening approaches, and run controlled experiments. In each experiment, we change one factor while keeping the rest of the resume the same. We then measure how the screener's score changes.

The goal is to understand the behaviour of our own test screeners. The results must not be presented as evidence about any specific company's hiring product.

## 2. Research questions

We will investigate four questions:

1. **Name, college and gap-year effects:** Do names, college names, or a gap year change a resume's score when its skills and other relevant content are identical?
2. **Layout and file-type effects:** Does resume layout or file type change the score when the resume's words are identical?
3. **Tricks versus honest improvements:** Do tactics such as keyword stuffing or hidden text improve scores compared with genuine improvements, such as adding a real, relevant project?
4. **Screener stability:** Does the same resume receive a consistent score across repeated runs, section reordering, and small synonym-based rewording?

## 3. Test screeners

We will implement and evaluate three screening approaches:

- **S1 — Keyword matcher:** Scores a resume using job-description skill matches and a small, explicit synonym list.
- **S2 — Embedding matcher:** Compares the meaning of the resume and job description using text embeddings and cosine similarity.
- **S3 — LLM judge:** Uses a defined scoring rubric to assess the resume against the job description and returns a score with a short reason.

These are our own simplified test systems. They are not replicas of commercial screening products.

All screeners will use a 0–100 score scale so their score changes can be compared.

## 4. Core experiments

The first version will focus on the six core experiments specified in the project guide. We will not expand the scope until these are completed.

| ID | Experiment | Controlled change | Expected behaviour of a fair test screener |
|---|---|---|---|
| E1 | Gender-coded names | Change only the name, comparing two published name-coded groups (20 names per group). | No score change when the resume's qualifications are identical. |
| E3 | College name versus real work | Compare a lesser-known college with a well-known college; separately compare the lesser-known-college version with and without one real project. | Compare the college-name effect with the real-project effect. A college effect larger than the real-project effect is a warning sign. |
| E5 | Resume layout | Render the same resume words in one-column, two-column, and table-based layouts. | No score change when the words are identical. |
| E7 | Keyword stuffing | Add a visible skills list that repeats job-description keywords without adding evidence of those skills. | Small or no gain. |
| E9 | Honest improvements | Add one genuine relevant project and rewrite experience/project bullets with specific numbers. | A clear gain when the improvements add relevant evidence. |
| E10 | Screener stability | Score the same input five times; also test section reordering and synonym-based rewording. | Almost no change for repeated identical input; small changes for harmless reordering or rewording. |

### Experiment controls

- Each twin pair must differ in exactly the factor being tested.
- All other resume content must remain unchanged.
- The base resume and its twin must be traceable by IDs.
- An automatic diff check must verify that no unintended fields changed.
- If a pair contains an unintended change, it must be fixed or excluded and documented; it must not be silently treated as a valid pair.
- Use synthetic data only. Do not use real resumes or real people's personal information.

## 5. Measurement plan

### 5.1 Score change

For each valid pair and screener, calculate:

`difference = twin_score - base_score`

A positive value means the changed version received a higher score; a negative value means it received a lower score.

Report the mean paired difference for each experiment and screener.

### 5.2 Uncertainty

For paired differences, calculate a 95% bootstrap interval:

1. Resample the observed paired differences with replacement.
2. Keep the resample size equal to the original number of pairs.
3. Calculate the mean for each resample.
4. Repeat 10,000 times.
5. Use the 2.5th and 97.5th percentiles as the interval bounds.

Use a fixed random seed so the analysis can be reproduced.

### 5.3 Additional results to report

For every experiment and screener, report:

- Mean score change, in points.
- 95% bootstrap interval.
- Effect in spread units: mean change divided by the spread (standard deviation) of base scores.
- Percentage of pairs where the twin scored higher.
- Percentage of pairs with an absolute score change greater than 5 points.
- A plain-language summary sentence.

For E1 and E3, also calculate the shortlist impact ratio. Pool the base resumes and the relevant twins for the same job, rank them by score, define the top 20% as the shortlist, calculate each group's shortlist rate, and divide each group's rate by the highest group's rate.

The impact ratio is a screening heuristic for further investigation, not a legal conclusion and not proof of fairness when it is above the threshold.

### 5.4 Multiple comparisons

Because several experiments and screeners will produce multiple intervals, apply the Holm correction to the relevant statistical tests. Report both uncorrected and corrected results. Treat borderline findings cautiously.

## 6. What counts as a meaningful result?

Before looking at experiment results, use these practical thresholds:

- A score change of **3 points or more** on the 0–100 scale; or
- A shortlist impact ratio of **0.80 or lower**.

These are investigation thresholds, not automatic proof that a system is unfair or legally non-compliant. Report the actual measurements and uncertainty, including results that do not cross either threshold.

## 7. Data and responsible testing rules

1. Use synthetic, fictional resumes only. Do not collect, scrape, or publish real resumes or real people's personal information.
2. Build and test our own screeners. Do not claim that results describe a named company's product.
3. Describe findings as **score differences** or **screening outcomes**, not as proof of discrimination or unlawful conduct.
4. Treat name groups as **name-coded test groups**. A name does not establish a person's gender, religion, or region.
5. Publish the exact name lists used for the experiment. Leave caste-coded surnames out of version 1.
6. Test hidden-text behaviour only against our own screeners.
7. Keep API keys and other secrets in `.env`; never commit them.
8. Keep private/generated data that should not be public out of Git.
9. Record failures, unexpected behaviour, model details, settings, and costs. Do not hide inconvenient or null results.

## 8. Reporting commitment

We will report every core experiment, including null, small, unexpected, or inconvenient results.

We will not select only the most exciting results for the final report. Each reported number must be reproducible from the experiment outputs and analysis scripts.

## 9. Phase 0 completion checklist

- [ ] This research plan has been reviewed and committed before any experiments are run.
- [ ] The repository contains the planned project folders: `data/`, `src/factory/`, `src/screeners/`, `src/experiments/`, `src/stats/`, `app/`, and `reports/`.
- [ ] `.gitignore` excludes `.env` and `data/private/`.
- [ ] A fresh clone can be set up and run using the documented instructions.

---

**Planning note:** This document defines the questions, core experiments, and measurement rules before results are collected. Any later change to the plan must be documented with a reason and date; earlier results must not be silently reinterpreted under new rules.
