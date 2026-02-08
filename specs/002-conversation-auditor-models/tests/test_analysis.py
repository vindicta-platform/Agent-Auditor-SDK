import pytest
from agent_auditor.analysis import (
    ArchetypeClassifier,
    ConversationAnalyzer,
    ConversationTurn,
    TaskArchetype,
)


@pytest.fixture
def classifier():
    return ArchetypeClassifier()


@pytest.fixture
def analyzer():
    from agent_auditor.analysis import RewardConfig

    # Favor quality significantly (0.8) to force switch to Pro for complex tasks
    config = RewardConfig(w_quality=0.8, w_efficiency=0.1, w_context=0.1)
    return ConversationAnalyzer(reward_config=config)


def test_scenario_classify_code_gen(classifier):
    """
    Scenario: Classify a code generation prompt
    """
    prompt = "Write a Python function to sort a list"
    archetype, confidence = classifier.classify(prompt)
    assert archetype == TaskArchetype.CODE_GEN


def test_scenario_score_models_for_reasoning(analyzer):
    """
    Scenario: Score models for a reasoning task
    """
    # GIVEN turn classified as REASONING
    archetype = TaskArchetype.REASONING

    # WHEN scoring models
    pro_score = analyzer.evaluator.calculate_quality_reward("gemini-2.5-pro", archetype)
    flash_score = analyzer.evaluator.calculate_quality_reward("gemini-2.0-flash", archetype)

    # THEN pro should have higher quality score for reasoning
    assert pro_score > flash_score


def test_scenario_detect_optimal_switch(analyzer):
    """
    Scenario: Detect optimal switching point
    """
    turns = [
        ConversationTurn(role="user", content="Hi"),
        ConversationTurn(role="assistant", content="Hello", model="gemini-2.0-flash"),
        ConversationTurn(role="user", content="Analyze this complex logical paradox..."),
        ConversationTurn(role="assistant", content="The paradox is...", model="gemini-2.0-flash"),
    ]

    report = analyzer.analyze("test-conv", turns)

    # turn 2 (index 2 in turns list) is the reasoning inflection point
    # It should recommend switching to a stronger model like Pro
    switch_points = [r.turn_index for r in report.switching_schedule]
    assert 2 in switch_points
    assert report.switching_schedule[0].recommended_model in ["gemini-2.5-pro", "claude-4-opus"]


def test_scenario_penalize_switch(analyzer):
    """
    Scenario: Penalize mid-conversation model switch
    """
    # GIVEN a proposed switch with hypothetical 20% loss
    from_m = "gemini-2.5-flash"
    to_m = "claude-4-opus"
    loss_ratio = analyzer.cost_model.calculate_loss_ratio(from_m, to_m)

    # Expect cross-provider penalty (0.05 tier + 0.15 provider = 0.20)
    assert 0.15 <= loss_ratio <= 0.25

    penalty = analyzer.evaluator.calculate_context_reward(from_m, to_m, loss_ratio)
    assert penalty < 1.0


def test_scenario_generate_report(analyzer):
    """
    Scenario: Generate analysis report for multi-archetype conversation
    """
    turns = [
        ConversationTurn(role="user", content="Hello"),
        ConversationTurn(role="assistant", content="Hi", model="gemini-2.0-flash"),
        ConversationTurn(role="user", content="Write a compiler in C++"),
        ConversationTurn(role="assistant", content="Source code...", model="gemini-2.0-flash"),
    ]
    report = analyzer.analyze("mult-arch", turns)

    assert len(report.inflection_points) == 2
    assert report.potential_improvement >= 0
    assert report.cost_savings_estimate >= 0
