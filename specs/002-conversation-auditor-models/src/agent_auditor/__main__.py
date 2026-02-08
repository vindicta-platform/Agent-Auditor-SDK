import argparse
import json

from .analysis.analyzer import ConversationAnalyzer
from .analysis.models import ConversationTurn


def analyze_conversation(args):
    """CLI handler for conversation analysis."""
    analyzer = ConversationAnalyzer()

    # Load transcript
    with open(args.file) as f:
        data = json.load(f)

    turns = [ConversationTurn(**t) for t in data]
    report = analyzer.analyze(args.id or "cli-conv", turns)

    if args.format == "json":
        print(report.model_dump_json(indent=2))
    else:
        print(f"\n--- Analysis Report: {report.conversation_id} ---")
        print(f"Total Turns: {report.total_turns}")
        print(f"Potential Improvement: {report.potential_improvement:.1f}%")
        print(f"Optimal Total Reward: {report.optimal_reward:.2f}")
        print(f"Actual Total Reward: {report.actual_reward:.2f}")
        print("\nOptimal Switching Schedule:")
        for rec in report.switching_schedule:
            print(f"  Turn {rec.turn_index}: {rec.recommended_model} ({rec.reasoning})")
        print("-------------------------------------------\n")


def main():
    parser = argparse.ArgumentParser(prog="agent_auditor")
    subparsers = parser.add_subparsers(dest="command")

    # Existing commands (stubs for this execution)
    subparsers.add_parser("status")
    subparsers.add_parser("process")

    # New Analyze command
    analyze_parser = subparsers.add_parser("analyze")
    analyze_parser.add_argument(
        "--file", required=True, help="Path to conversation transcript JSON"
    )
    analyze_parser.add_argument("--id", help="Optional conversation ID")
    analyze_parser.add_argument("--format", choices=["text", "json"], default="text")

    args = parser.parse_args()

    if args.command == "analyze":
        analyze_conversation(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
