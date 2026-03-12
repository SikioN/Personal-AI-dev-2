"""
Benchmark runner for QA pipeline evaluation.

Usage:
    from src.pipelines.qa.benchmark import BenchmarkRunner
    runner = BenchmarkRunner(engine)
    df = runner.run()
    runner.summarize(df)
"""
from __future__ import annotations

import time
import pandas as pd
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.pipelines.qa.qa_engine import QAEngine

# ---------------------------------------------------------------------------
# Benchmark dataset: 5 question types × 3 questions = 15 total
# Each type has exactly 1 out-of-KG question (in_kg=False → expected: Unknown/NULL)
# ---------------------------------------------------------------------------
BENCHMARK_QUESTIONS = [
    # --- 1. Simple Entity ---
    {
        "q": "Who was the spouse of Vladimir Nabokov?",
        "type": "simple_entity",
        "gt": "Vera Nabokova",
        "in_kg": True,
    },
    {
        "q": "What country is Vladimir Nabokov a citizen of?",
        "type": "simple_entity",
        "gt": "United States of America",
        "in_kg": True,
    },
    {
        "q": "What was the name of Vladimir Nabokov's pet cat?",
        "type": "simple_entity",
        "gt": "Unknown",
        "in_kg": False,
    },

    # --- 2. Simple Time ---
    {
        "q": "In what year did Vladimir Nabokov marry Vera Nabokova?",
        "type": "simple_time",
        "gt": "1925",
        "in_kg": True,
    },
    {
        "q": "When did Vladimir Nabokov reside in Saint Petersburg?",
        "type": "simple_time",
        "gt": "1899 - 1917",
        "in_kg": True,
    },
    {
        "q": "When did Vladimir Nabokov visit the Moon?",
        "type": "simple_time",
        "gt": "Unknown",
        "in_kg": False,
    },

    # --- 3. Before / After ---
    {
        "q": "Where did Vladimir Nabokov live before 1930?",
        "type": "before_after",
        "gt": "Berlin / Saint Petersburg",
        "in_kg": True,
    },
    {
        "q": "Where did Vladimir Nabokov live after 1960?",
        "type": "before_after",
        "gt": "Montreux",
        "in_kg": True,
    },
    {
        "q": "Which novel did Vladimir Nabokov publish after 2020?",
        "type": "before_after",
        "gt": "Unknown",
        "in_kg": False,
    },

    # --- 4. First / Last ---
    {
        "q": "What was the first city where Vladimir Nabokov resided?",
        "type": "first_last",
        "gt": "Saint Petersburg",
        "in_kg": True,
    },
    {
        "q": "What was the last city where Vladimir Nabokov resided?",
        "type": "first_last",
        "gt": "Montreux",
        "in_kg": True,
    },
    {
        "q": "What was the last novel published by Vladimir Nabokov?",
        "type": "first_last",
        "gt": "Unknown",
        "in_kg": False,
    },

    # --- 5. Time Join ---
    {
        "q": "Who was the head of government of the USA when Vladimir Nabokov lived in Wellesley?",
        "type": "time_join",
        "gt": "Franklin D. Roosevelt",
        "in_kg": True,
    },
    {
        "q": "Who was the head of government of the USA when Nabokov was nominated for Nobel Prize in Literature?",
        "type": "time_join",
        "gt": "Lyndon B. Johnson / Kennedy",
        "in_kg": True,
    },
    {
        "q": "Who was the head of government of the USA when Vladimir Nabokov won the Grammy Award?",
        "type": "time_join",
        "gt": "Unknown",
        "in_kg": False,
    },
]


class BenchmarkRunner:
    """Evaluates QAEngine.ask() against the standard benchmark question set."""

    def __init__(self, engine: "QAEngine") -> None:
        self.engine = engine

    def run(
        self,
        questions: list = BENCHMARK_QUESTIONS,
        run_baseline: bool = False,
    ) -> pd.DataFrame:
        """
        Run all benchmark questions and return a DataFrame with results.
        Columns: Question, Type, In KG, Ground Truth, Answer, Correct, Category,
                 Time (s)[, Baseline Answer, Baseline Correct]
        """
        rows = []
        total = len(questions)
        for i, b in enumerate(questions, 1):
            print(f"\n{'#' * 70}\n--- Q{i}/{total}: {b['q']} ---")

            # Pipeline answer
            t0 = time.perf_counter()
            try:
                answer = self.engine.ask(b["q"], top_k=10)
            except Exception as e:
                print(f"  [ERROR] {e}")
                answer = "Error"
            elapsed = time.perf_counter() - t0

            correct = self.check_answer(answer, b["gt"], b["in_kg"])
            category = self._categorize(correct, b["in_kg"])

            row = {
                "Question":     b["q"],
                "Type":         b["type"],
                "In KG":        b["in_kg"],
                "Ground Truth": b["gt"],
                "Answer":       answer,
                "Correct":      correct,
                "Category":     category,
                "Time (s)":     round(elapsed, 2),
            }

            # Optional baseline
            if run_baseline and hasattr(self.engine, 'ask_base'):
                try:
                    base_answer = self.engine.ask_base(b["q"], top_k=10)
                except Exception as e:
                    print(f"  [BASELINE ERROR] {e}")
                    base_answer = "Error"
                base_correct = self.check_answer(base_answer, b["gt"], b["in_kg"])
                row["Baseline Answer"] = base_answer
                row["Baseline Correct"] = base_correct

            rows.append(row)

        return pd.DataFrame(rows)

    @staticmethod
    def check_answer(ans: str, gt: str, in_kg: bool) -> bool:
        """
        Check if an answer is correct.
        - out-of-KG: correct if 'unknown' or 'null' appears in the answer
        - in-KG:     correct if any ground-truth alternative is a substring of the answer
        """
        ans_lower = ans.lower()
        if not in_kg:
            return "unknown" in ans_lower or "null" in ans_lower
        if ans in ("Error", "Unknown", "NULL"):
            return False
        for t in gt.split(" / "):
            if t.strip().lower() in ans_lower:
                return True
        return False

    @staticmethod
    def _categorize(correct: bool, in_kg: bool) -> str:
        if in_kg:
            return "TP" if correct else "FP"
        return "TN" if correct else "FN"

    def summarize(self, df: pd.DataFrame) -> dict:
        """
        Print and return a summary of benchmark results.

        Returns a dict with keys:
            total, correct, accuracy, by_type, category_counts,
            avg_time_by_type[, baseline_accuracy]
        """
        total = len(df)
        correct = df["Correct"].sum()
        accuracy = correct / total if total > 0 else 0.0

        by_type = (
            df.groupby("Type")["Correct"]
            .agg(["sum", "count"])
            .rename(columns={"sum": "Correct", "count": "Total"})
        )
        by_type["Accuracy"] = by_type["Correct"] / by_type["Total"]

        # Avg time per type
        if "Time (s)" in df.columns:
            by_type["Avg Time (s)"] = df.groupby("Type")["Time (s)"].mean().round(2)

        category_counts = df["Category"].value_counts().to_dict()

        print("\n" + "=" * 50)
        print(f"BENCHMARK RESULTS: {correct}/{total} ({accuracy:.1%})")
        print("=" * 50)
        print("\nBy question type:")
        print(by_type.to_string())
        print("\nCategory breakdown:", category_counts)

        result = {
            "total":           total,
            "correct":         int(correct),
            "accuracy":        accuracy,
            "by_type":         by_type,
            "category_counts": category_counts,
        }

        if "Baseline Answer" in df.columns:
            base_correct = df["Baseline Correct"].sum()
            base_acc = base_correct / total if total > 0 else 0.0
            print(f"\nBaseline: {base_correct}/{total} ({base_acc:.1%})")
            print(f"Pipeline improvement: {accuracy - base_acc:+.1%}")
            result["baseline_accuracy"] = base_acc

        print("=" * 50)
        return result
