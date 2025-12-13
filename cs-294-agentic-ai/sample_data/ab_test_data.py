"""
A/B Test Analysis Code

This script implements the A/B test for checkout button color experiment.
"""

import pandas as pd
import numpy as np
from scipy import stats


def load_data(file_path):
    """Load A/B test data from CSV file."""
    df = pd.read_csv(file_path)
    return df


def calculate_metrics(df, group_col='group', metric_col='conversion'):
    """
    Calculate key metrics for each group.

    Args:
        df: DataFrame with A/B test data
        group_col: Column name for group assignment
        metric_col: Column name for success metric

    Returns:
        dict: Metrics for each group
    """
    metrics = {}

    for group in df[group_col].unique():
        group_data = df[df[group_col] == group]

        metrics[group] = {
            'n': len(group_data),
            'mean': group_data[metric_col].mean(),
            'std': group_data[metric_col].std(),
            'sum': group_data[metric_col].sum()
        }

    return metrics


def run_ttest(df, group_col='group', metric_col='conversion'):
    """
    Run t-test to compare groups.

    Args:
        df: DataFrame with A/B test data
        group_col: Column name for group assignment
        metric_col: Column name for success metric

    Returns:
        tuple: (t_statistic, p_value)
    """
    control = df[df[group_col] == 'control'][metric_col]
    treatment = df[df[group_col] == 'treatment'][metric_col]

    t_stat, p_value = stats.ttest_ind(control, treatment)

    return t_stat, p_value


def main():
    """Main analysis function."""
    # Load data
    df = load_data('ab_test_data.csv')

    print("A/B Test Analysis")
    print("=" * 50)
    print(f"Total samples: {len(df)}")
    print(f"\nData shape: {df.shape}")
    print(f"\nColumns: {df.columns.tolist()}")

    # Calculate metrics
    metrics = calculate_metrics(df)

    print("\nGroup Metrics:")
    for group, stats in metrics.items():
        print(f"  {group}: n={stats['n']}, mean={stats['mean']:.3f}")

    # Run statistical test
    t_stat, p_value = run_ttest(df)

    print(f"\nT-test Results:")
    print(f"  t-statistic: {t_stat:.3f}")
    print(f"  p-value: {p_value:.4f}")
    print(f"  Significant at α=0.05: {p_value < 0.05}")


if __name__ == "__main__":
    main()
