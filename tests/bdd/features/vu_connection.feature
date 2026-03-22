Feature: Voltage Unit Connection
  As a lab technician
  I want to connect to a Voltage Unit via the GUI
  So that I can perform calibration and testing

  Scenario: Successful ping verifies instrument
    Given a VU service with scope IP "192.168.68.154"
    When the ping task completes successfully
    Then the instrument should be verified

  Scenario: Failed ping marks instrument as unverified
    Given a VU service with scope IP "10.0.0.99"
    When the ping task fails
    Then the instrument should not be verified

  Scenario: Connect without scope IP returns None
    Given a VU service with no scope IP
    When I request connect_and_read
    Then no task should be returned

  Scenario: Successful connection emits connectedChanged
    Given a VU service with scope IP "192.168.68.154"
    When the connect task completes successfully
    Then the service should report connected

  Scenario: Disconnect after connection
    Given a connected VU service
    When I disconnect
    Then the service should report disconnected
