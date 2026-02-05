Feature: Predictive Quota Budgeting

  As the Arbiter Scheduler
  I want to predict how much quota headroom remains each hour
  So that I can safely allocate leftover capacity to background AI tasks

  Background:
    Given the system is initialized

  Scenario: Calculate safe budget from history
    Given historical usage data exists for the past 7 days
    When the scheduler evaluates capacity
    Then it should calculate a safe budget with positive confidence

  Scenario: Background throttles when budget consumed
    Given the predicted budget is 50 requests per hour
    And 30 requests are consumed by background tasks
    When background usage increases to 45 requests
    Then background processing should throttle
