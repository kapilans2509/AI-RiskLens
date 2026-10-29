import json
import pandas as pd
import streamlit as st

from risklens import (
    REQUIRED_COLUMNS,
    make_sample_data,
    validate_candidate_data,
    score_candidates,
    calculate_fairness_metrics,
    build_risk_register,
    build_report,
)

st.set_page_config(
    page_title="AI RiskLens | Hiring AI Audit",
    page_icon="🛡️",
    layout="wide",
)

st.title("AI RiskLens")
st.caption(
    "AI hiring risk assessment | fairness, transparency, privacy, "
    "human oversight, accountability"
)
st.warning(
    "Research prototype only. It does not certify legal compliance or prove "
    "fairness. Use synthetic or properly authorized data."
)

with st.sidebar:
    st.header("Assessment settings")
    threshold = st.slider("Shortlisting threshold", 0, 100, 70, 5)
    reference_group = st.selectbox(
        "Reference group", ["Group A", "Group B"]
    )
    st.markdown(
        "**Workflow**\n"
        "1. Load demo data or upload CSV.\n"
        "2. Review scoring assumptions.\n"
        "3. Inspect fairness indicators and risks.\n"
        "4. Compare thresholds in the Experiment Lab.\n"
        "5. Export reports."
    )

if "candidate_data" not in st.session_state:
    st.session_state.candidate_data = make_sample_data()

t1, t2, t3, t4, t5 = st.tabs(
    [
        "Overview",
        "Candidate data",
        "Risk register",
        "Export report",
        "Fairness Experiment Lab",
    ]
)

with t2:
    if st.button("Load / reset synthetic demo data", type="primary"):
        st.session_state.candidate_data = make_sample_data()

    uploaded = st.file_uploader("Upload candidate CSV", type=["csv"])

    if uploaded is not None:
        try:
            new = pd.read_csv(uploaded)
            errs = validate_candidate_data(new)

            if errs:
                st.error("CSV not loaded: " + " ".join(errs))
            else:
                st.session_state.candidate_data = new
                st.success(f"Loaded {len(new)} rows.")
        except Exception as e:
            st.error(f"Could not read CSV: {e}")

    st.markdown("**Required columns**")
    st.code(", ".join(REQUIRED_COLUMNS))
    st.caption(
        "Group labels are illustrative. Avoid uploading identifiable "
        "or sensitive personal data."
    )
    st.dataframe(
        st.session_state.candidate_data,
        width="stretch",
        hide_index=True,
    )
    st.download_button(
        "Download current dataset CSV",
        st.session_state.candidate_data.to_csv(index=False).encode(),
        "risklens_candidate_data.csv",
        "text/csv",
    )

df = st.session_state.candidate_data.copy()
errors = validate_candidate_data(df)

if errors:
    with t1:
        st.error("Current dataset is invalid: " + " ".join(errors))
else:
    scored = score_candidates(df, threshold)
    metrics = calculate_fairness_metrics(scored, reference_group)
    risks = build_risk_register(scored, metrics)
    report = build_report(
        scored, metrics, risks, threshold, reference_group
    )

    with t1:
        st.subheader("Assessment overview")
        a, b, c, d = st.columns(4)
        a.metric("Candidates assessed", len(scored))
        b.metric("Shortlisted", int(scored.selected.sum()))
        c.metric(
            "Selection rate",
            f"{scored.selected.mean() * 100:.1f}%",
        )
        d.metric("Risk items", len(risks))

        st.markdown("### Transparent baseline scoring")
        st.write(
            "Gender group is not used in the score formula; it is used "
            "only to compare outcomes. This is an illustrative baseline, "
            "not a validated hiring model."
        )
        st.code(
            "score = 0.30 × qualification + 0.35 × skills "
            "+ 0.15 × min(experience, 10) × 10 "
            "+ 0.20 × interview"
        )

        gs = metrics["group_summary"].copy()
        gs["selection_rate_pct"] = (
            gs.selection_rate * 100
        ).round(1)
        gs["mean_score"] = gs.mean_score.round(1)

        st.dataframe(
            gs[
                [
                    "gender_group",
                    "candidates",
                    "selected",
                    "selection_rate_pct",
                    "mean_score",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

        x, y, z = st.columns(3)
        x.metric(
            "Selection-rate difference",
            f"{metrics['selection_rate_difference_pp']:.1f} pp",
        )
        ratio = metrics["selection_rate_ratio"]
        y.metric(
            "Selection-rate ratio",
            "N/A" if ratio is None else f"{ratio:.2f}",
        )
        z.metric(
            "Mean score gap",
            f"{metrics['mean_score_gap']:.1f} points",
        )

        st.caption(
            "Descriptive screening indicators only. A ratio below 0.80 "
            "is not a legal determination. Sample size and context matter."
        )
        st.subheader("Candidate-level results")
        st.dataframe(scored, width="stretch", hide_index=True)

    with t3:
        st.subheader("Risk register")
        st.caption(
            "Risk ratings are heuristic priorities; review evidence "
            "and assumptions before acting."
        )
        st.dataframe(
            pd.DataFrame(risks),
            width="stretch",
            hide_index=True,
        )

        for r in risks:
            with st.expander(f"{r['priority']} · {r['risk']}"):
                st.write(r["evidence"])
                st.write("**Recommended action:** " + r["recommendation"])

    with t4:
        st.subheader("Export assessment")
        st.download_button(
            "Download assessment report JSON",
            json.dumps(report, indent=2, default=str).encode(),
            "risklens_assessment_report.json",
            "application/json",
        )
        st.download_button(
            "Download scored candidates CSV",
            scored.to_csv(index=False).encode(),
            "risklens_scored_candidates.csv",
            "text/csv",
        )
        st.download_button(
            "Download risk register CSV",
            pd.DataFrame(risks).to_csv(index=False).encode(),
            "risklens_risk_register.csv",
            "text/csv",
        )
        st.markdown("### Report summary")
        st.json(report["summary"])

    with t5:
        st.subheader("Fairness Experiment Lab")
        st.write(
            "Compare selection outcomes across thresholds and investigate "
            "potential differences between groups."
        )

        thresholds = [50, 60, 70, 80, 90]
        experiment_rows = []
        comparison_rows = []

        for test_threshold in thresholds:
            test_scored = score_candidates(df, test_threshold)
            test_metrics = calculate_fairness_metrics(
                test_scored, reference_group
            )

            group_summary = test_metrics["group_summary"]

            for _, group in group_summary.iterrows():
                experiment_rows.append({
                    "threshold": test_threshold,
                    "group": group["gender_group"],
                    "candidates": int(group["candidates"]),
                    "shortlisted": int(group["selected"]),
                    "selection_rate_pct": round(
                        float(group["selection_rate"] * 100), 1
                    ),
                    "mean_score": round(
                        float(group["mean_score"]), 2
                    ),
                })

            comparison_rows.append({
                "threshold": test_threshold,
                "selection_rate_difference_pp":
                    test_metrics["selection_rate_difference_pp"],
                "selection_rate_ratio":
                    test_metrics["selection_rate_ratio"],
                "mean_score_gap": test_metrics["mean_score_gap"],
            })

        experiment_df = pd.DataFrame(experiment_rows)
        comparison_df = pd.DataFrame(comparison_rows)
                # Overall selection trade-offs at each threshold
        threshold_totals = (
            experiment_df.groupby("threshold")
            .agg(
                total_candidates=("candidates", "sum"),
                total_shortlisted=("shortlisted", "sum"),
            )
            .reset_index()
        )

        threshold_totals["overall_selection_rate_pct"] = (
            threshold_totals["total_shortlisted"]
            / threshold_totals["total_candidates"]
            * 100
        ).round(1)

        st.markdown("### Overall selection trade-offs")

        st.write(
            "Compare how restrictive each threshold is. Higher thresholds "
            "generally shortlist fewer candidates under this scoring formula."
        )

        st.dataframe(
            threshold_totals,
            width="stretch",
            hide_index=True,
        )

        st.markdown("#### Total candidates shortlisted")

        st.line_chart(
            threshold_totals.set_index("threshold")[
                ["total_shortlisted"]
            ]
        )

        st.markdown("#### Research interpretation")

        min_gap = comparison_df[
            "selection_rate_difference_pp"
        ].min()
        max_gap = comparison_df[
            "selection_rate_difference_pp"
        ].max()

        min_gap_thresholds = comparison_df.loc[
            comparison_df["selection_rate_difference_pp"] == min_gap,
            "threshold",
        ].tolist()

        max_gap_thresholds = comparison_df.loc[
            comparison_df["selection_rate_difference_pp"] == max_gap,
            "threshold",
        ].tolist()

        st.write(
            f"The smallest observed selection-rate gap was "
            f"{min_gap:.1f} percentage points at threshold(s) "
            f"{min_gap_thresholds}."
        )

        st.write(
            f"The largest observed selection-rate gap was "
            f"{max_gap:.1f} percentage points at threshold(s) "
            f"{max_gap_thresholds}."
        )

        st.write(
            "Review these results alongside the total number selected, "
            "group sample sizes, and whether the scoring criteria are "
            "job-related. Equal selection rates alone do not establish "
            "fairness, and a smaller gap does not automatically mean "
            "a better outcome."
        )
                # 6. Compare alternative scoring strategies
        st.markdown("---")
        st.subheader("Scoring Strategy Experiment")

        st.write(
            "Compare how alternative scoring weights affect candidate "
            "selection and group outcome indicators. All strategies use "
            "the same candidate data and the current threshold."
        )

        strategies = {
            "Baseline": {
                "qualification": 0.30,
                "skills": 0.35,
                "experience": 0.15,
                "interview": 0.20,
            },
            "Skills-focused": {
                "qualification": 0.20,
                "skills": 0.50,
                "experience": 0.10,
                "interview": 0.20,
            },
            "Qualification-focused": {
                "qualification": 0.50,
                "skills": 0.25,
                "experience": 0.10,
                "interview": 0.15,
            },
        }

        strategy_summary = []
        strategy_groups = []

        for strategy_name, weights in strategies.items():
            strategy_df = df.copy()

            exp_score = (
                pd.to_numeric(strategy_df["experience_years"])
                .clip(lower=0, upper=10) * 10
            )

            strategy_df["baseline_score"] = (
                weights["qualification"]
                * pd.to_numeric(strategy_df["qualification_score"])
                + weights["skills"]
                * pd.to_numeric(strategy_df["skills_score"])
                + weights["experience"] * exp_score
                + weights["interview"]
                * pd.to_numeric(strategy_df["interview_score"])
            ).round(2)

            strategy_df["selected"] = (
                strategy_df["baseline_score"] >= threshold
            )
            strategy_df["decision"] = strategy_df["selected"].map({
                True: "SHORTLIST",
                False: "NOT_SHORTLISTED",
            })

            strategy_metrics = calculate_fairness_metrics(
                strategy_df, reference_group
            )

            strategy_summary.append({
                "strategy": strategy_name,
                "threshold": threshold,
                "candidates": len(strategy_df),
                "shortlisted": int(strategy_df["selected"].sum()),
                "overall_selection_rate_pct": round(
                    strategy_df["selected"].mean() * 100, 1
                ),
                "selection_rate_difference_pp":
                    strategy_metrics["selection_rate_difference_pp"],
                "selection_rate_ratio":
                    strategy_metrics["selection_rate_ratio"],
                "mean_score_gap": strategy_metrics["mean_score_gap"],
            })

            group_summary = strategy_metrics["group_summary"].copy()
            group_summary["strategy"] = strategy_name
            group_summary["selection_rate_pct"] = (
                group_summary["selection_rate"] * 100
            ).round(1)

            strategy_groups.append(
                group_summary[
                    [
                        "strategy",
                        "gender_group",
                        "candidates",
                        "selected",
                        "selection_rate_pct",
                        "mean_score",
                    ]
                ]
            )

        strategy_results = pd.DataFrame(strategy_summary)
        strategy_group_results = pd.concat(
            strategy_groups, ignore_index=True
        )

        st.markdown("### Strategy comparison")
        st.dataframe(
            strategy_results.round(2),
            width="stretch",
            hide_index=True,
        )

        st.markdown("### Overall selection rate by strategy")
        st.bar_chart(
            strategy_results.set_index("strategy")[
                ["overall_selection_rate_pct"]
            ]
        )

        st.markdown("### Selection-rate disparity by strategy")
        st.bar_chart(
            strategy_results.set_index("strategy")[
                ["selection_rate_difference_pp"]
            ]
        )

        st.markdown("### Group-level outcomes")
        st.dataframe(
            strategy_group_results.round(2),
            width="stretch",
            hide_index=True,
        )

        st.download_button(
            "Download strategy comparison CSV",
            strategy_results.to_csv(index=False).encode("utf-8"),
            "risklens_strategy_comparison.csv",
            "text/csv",
        )

        st.download_button(
            "Download strategy group results CSV",
            strategy_group_results.to_csv(index=False).encode("utf-8"),
            "risklens_strategy_group_results.csv",
            "text/csv",
        )

        st.info(
            "Research limitation: these weights are illustrative hypotheses, "
            "not validated hiring criteria. A change in measured disparity "
            "does not prove that a strategy is fairer. Evaluate job relevance, "
            "selection outcomes, sample size, and potential harms before "
            "drawing conclusions."
        )

        # 1. Selection rate chart
        st.markdown("### 1. Selection rates by threshold")

        rate_chart = experiment_df.pivot(
            index="threshold",
            columns="group",
            values="selection_rate_pct",
        )

        st.line_chart(rate_chart)

        # 2. Disparity chart
        st.markdown("### 2. Selection-rate disparity")

        st.caption(
            "Absolute percentage-point difference between the reference "
            "group and the lowest-selection-rate non-reference group. "
            "A gap of zero means equal observed selection rates in this sample."
        )

        disparity_chart = comparison_df.set_index("threshold")[
            ["selection_rate_difference_pp"]
        ]

        st.bar_chart(disparity_chart)

        # 3. Automatic experiment summary
        st.markdown("### 3. Automatic experiment summary")

        smallest_gap = comparison_df[
            "selection_rate_difference_pp"
        ].min()

        largest_gap = comparison_df[
            "selection_rate_difference_pp"
        ].max()

        smallest_rows = comparison_df[
            comparison_df["selection_rate_difference_pp"] == smallest_gap
        ]

        largest_rows = comparison_df[
            comparison_df["selection_rate_difference_pp"] == largest_gap
        ]

        smallest_thresholds = ", ".join(
            smallest_rows["threshold"].astype(str).tolist()
        )

        largest_thresholds = ", ".join(
            largest_rows["threshold"].astype(str).tolist()
        )

        m1, m2 = st.columns(2)

        m1.metric(
            "Smallest observed gap",
            f"{smallest_gap:.1f} percentage points",
        )

        m2.metric(
            "Largest observed gap",
            f"{largest_gap:.1f} percentage points",
        )

        st.write(
            f"**Smallest gap:** threshold(s) {smallest_thresholds}. "
            "This indicates the smallest measured selection-rate difference "
            "among the tested thresholds."
        )

        st.write(
            f"**Largest gap:** threshold(s) {largest_thresholds}. "
            "These threshold(s) show the largest measured difference "
            "and may warrant further investigation."
        )

        st.warning(
            "Thresholds also change how many candidates are selected. "
            "A smaller disparity does not automatically mean a better or "
            "fairer hiring process. Review job relevance, sample size, "
            "data quality, and potential harms before drawing conclusions."
        )

        # 4. Full results
        st.markdown("### 4. Group results")

        st.dataframe(
            experiment_df,
            width="stretch",
            hide_index=True,
        )

        st.markdown("### 5. Threshold comparison table")

        st.dataframe(
            comparison_df.round(2),
            width="stretch",
            hide_index=True,
        )

        # 5. Export experiment data
        st.download_button(
            "Download group results CSV",
            experiment_df.to_csv(index=False).encode("utf-8"),
            "risklens_fairness_experiments.csv",
            "text/csv",
        )

        st.download_button(
            "Download disparity summary CSV",
            comparison_df.to_csv(index=False).encode("utf-8"),
            "risklens_disparity_summary.csv",
            "text/csv",
        )

        st.info(
            "Interpretation: thresholds change who is shortlisted and "
            "may change group disparities. A smaller measured gap does "
            "not by itself prove fairness. These are descriptive results "
            "on the supplied dataset, not causal findings or legal conclusions."
        )

st.markdown("---")
st.caption(
    "AI RiskLens • Portfolio research prototype • "
    "Not legal advice or a hiring decision system"
)
