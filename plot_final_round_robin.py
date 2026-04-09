#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


plt.rcParams.update({
    "font.size": 16,
    "axes.titlesize": 20,
    "axes.labelsize": 18,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "legend.fontsize": 16,
})


def expected_score(r_a: float, r_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((r_b - r_a) / 400.0))


def update_elo(r_a: float, r_b: float, score_a: float, k_factor: float = 32.0):
    exp_a = expected_score(r_a, r_b)
    exp_b = expected_score(r_b, r_a)
    new_a = r_a + k_factor * (score_a - exp_a)
    new_b = r_b + k_factor * ((1.0 - score_a) - exp_b)
    return new_a, new_b


def compute_elo_from_results(df: pd.DataFrame, k_factor: float = 32.0) -> dict:
    ratings = {}

    for _, row in df.iterrows():
        if int(row.get("error", 0)) != 0:
            continue

        a = row["agent_a"]
        b = row["agent_b"]

        ratings.setdefault(a, 1500.0)
        ratings.setdefault(b, 1500.0)

        winner = row["winner_from_log"]
        if pd.isna(winner) or winner == "":
            winner = row["winner"]

        if winner == a:
            score_a = 1.0
        elif winner == b:
            score_a = 0.0
        else:
            score_a = 0.5

        ratings[a], ratings[b] = update_elo(ratings[a], ratings[b], score_a, k_factor)

    return ratings


def build_agent_level_table(df: pd.DataFrame):
    rows = []

    for _, row in df.iterrows():
        if int(row.get("error", 0)) != 0:
            continue

        winner = row["winner_from_log"]
        if pd.isna(winner) or winner == "":
            winner = row["winner"]

        is_draw = row.get("is_draw_from_log", False)
        if pd.isna(is_draw):
            is_draw = False

        rows.append(
            {
                "agent": row["agent_a"],
                "opponent": row["agent_b"],
                "seed": row["seed"],
                "swap_positions": row["swap_positions"],
                "won": 1 if winner == row["agent_a"] else 0,
                "draw": 1 if bool(is_draw) else 0,
                "survival_turns": row["survival_turns_a"],
                "final_length": row["final_length_a"],
                "max_length": row["max_length_a"],
                "food_eaten": row["food_eaten_a"],
                "hazard_turns": row["hazard_turns_a"],
                "hazard_entries": row["hazard_entries_a"],
                "avg_health": row["avg_health_a"],
                "min_health": row["min_health_a"],
                "avg_latency": row["avg_latency_a"],
            }
        )

        rows.append(
            {
                "agent": row["agent_b"],
                "opponent": row["agent_a"],
                "seed": row["seed"],
                "swap_positions": row["swap_positions"],
                "won": 1 if winner == row["agent_b"] else 0,
                "draw": 1 if bool(is_draw) else 0,
                "survival_turns": row["survival_turns_b"],
                "final_length": row["final_length_b"],
                "max_length": row["max_length_b"],
                "food_eaten": row["food_eaten_b"],
                "hazard_turns": row["hazard_turns_b"],
                "hazard_entries": row["hazard_entries_b"],
                "avg_health": row["avg_health_b"],
                "min_health": row["min_health_b"],
                "avg_latency": row["avg_latency_b"],
            }
        )

    long_df = pd.DataFrame(rows)

    summary = (
        long_df.groupby("agent", as_index=False)
        .agg(
            games=("agent", "size"),
            wins=("won", "sum"),
            draws=("draw", "sum"),
            win_rate=("won", "mean"),
            avg_survival_turns=("survival_turns", "mean"),
            avg_final_length=("final_length", "mean"),
            avg_max_length=("max_length", "mean"),
            avg_food_eaten=("food_eaten", "mean"),
            avg_hazard_turns=("hazard_turns", "mean"),
            avg_hazard_entries=("hazard_entries", "mean"),
            avg_health=("avg_health", "mean"),
            avg_min_health=("min_health", "mean"),
            avg_latency=("avg_latency", "mean"),
        )
    )

    return summary, long_df


def add_value_labels(ax, bars, fmt="{:.2f}", rotation=0):
    for bar in bars:
        h = bar.get_height()
        ax.annotate(
            fmt.format(h),
            xy=(bar.get_x() + bar.get_width() / 2, h),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            va="bottom",
            rotation=rotation,
            fontsize=14,
        )


def plot_summary(summary_df: pd.DataFrame, out_path: Path, title: str):
    agents = summary_df["agent"].tolist()
    xpos = list(range(len(agents)))

    fig, axes = plt.subplots(2, 2, figsize=(16, 11))

    # 1. Win rate
    ax = axes[0, 0]
    bars = ax.bar(agents, summary_df["win_rate"] * 100)
    ax.set_title("Win rate")
    ax.set_ylabel("Win rate (%)")
    ax.set_ylim(0, 100)
    add_value_labels(ax, bars, fmt="{:.1f}")
    ax.tick_params(axis="x", rotation=20)

    # 2. ELO
    ax = axes[0, 1]
    bars = ax.bar(agents, summary_df["elo"])
    ax.set_title("ELO")
    ax.set_ylabel("ELO rating")
    add_value_labels(ax, bars, fmt="{:.1f}")
    ax.tick_params(axis="x", rotation=20)

    # 3. Survival and final length
    ax = axes[1, 0]
    width = 0.35
    bars1 = ax.bar(
        [i - width / 2 for i in xpos],
        summary_df["avg_survival_turns"],
        width=width,
        label="Avg survival turns",
    )
    bars2 = ax.bar(
        [i + width / 2 for i in xpos],
        summary_df["avg_final_length"],
        width=width,
        label="Avg final length",
    )
    ax.set_xticks(xpos)
    ax.set_xticklabels(agents, rotation=20)
    ax.set_title("Survival and final length")
    ax.legend()
    add_value_labels(ax, bars1, fmt="{:.1f}")
    add_value_labels(ax, bars2, fmt="{:.1f}")

    # 4. Food and hazard exposure
    ax = axes[1, 1]
    bars1 = ax.bar(
        [i - width / 2 for i in xpos],
        summary_df["avg_food_eaten"],
        width=width,
        label="Avg food eaten",
    )
    bars2 = ax.bar(
        [i + width / 2 for i in xpos],
        summary_df["avg_hazard_turns"],
        width=width,
        label="Avg hazard turns",
    )
    ax.set_xticks(xpos)
    ax.set_xticklabels(agents, rotation=20)
    ax.set_title("Food and hazard exposure")
    ax.legend()
    add_value_labels(ax, bars1, fmt="{:.2f}")
    add_value_labels(ax, bars2, fmt="{:.2f}")

    plt.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=str, help="Path to results.csv")
    parser.add_argument(
        "--title",
        type=str,
        default="Battlesnake experiment summary",
        help="Figure title",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Could not find file: {csv_path}")

    df = pd.read_csv(csv_path)

    summary_df, long_df = build_agent_level_table(df)
    elo = compute_elo_from_results(df)

    summary_df["elo"] = summary_df["agent"].map(elo)
    summary_df = summary_df.sort_values("elo", ascending=False).reset_index(drop=True)

    out_dir = csv_path.parent
    summary_csv = out_dir / "summary_by_agent.csv"
    fig_path = out_dir / "summary_figure.png"

    summary_df.to_csv(summary_csv, index=False)
    plot_summary(summary_df, fig_path, args.title)

    print(f"Saved summary table to: {summary_csv}")
    print(f"Saved figure to: {fig_path}")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()