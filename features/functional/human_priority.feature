Feature: Human Priority Guarantee

  As a Human User (Brandon Fox)
  I want my interactive requests to ALWAYS succeed
  So that I am never blocked by background AI tasks consuming my personal quota

  Background:
    Given the system is initialized
    And a valid API key is present

  Scenario: Human request succeeds when quota 90% consumed
    Given the quota is 90% consumed by background tasks
    When I submit an interactive request with prompt "What is the meta?"
    Then the request should succeed immediately
    And the response should be valid

  Scenario: Background tasks pause for human request
    Given background tasks are queued
    When a human request arrives
    Then background tasks should pause until the human request completes
    And the human request should be processed first

  Scenario: Clear error when quota exhausted
    Given the quota is fully exhausted
    When I submit a human request
    Then I should receive a QuotaExhaustedError
    And the error should contain a reset time
