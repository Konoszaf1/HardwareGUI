Feature: Simulation Mode
  As a developer without lab hardware
  I want to run the application in simulation mode
  So that I can test GUI workflows without real instruments

  Scenario: Simulation service ping always succeeds
    Given a simulated VU service
    When I ping the instrument
    Then the ping result should be OK

  Scenario: Simulation connect always succeeds
    Given a simulated VU service
    When I connect
    Then the service should report connected
