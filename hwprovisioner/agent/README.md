# agent

It is the responsibility of the agent to inform the Allocate service of the resources the agent is connected to. This populates the inventory on Allocate.

*Scenario: "As a systems engineer, I want to join my nvidia server to the Allocate inventory"*

## api

```json
# The agent has no exposed API. Instead it is passed configuration for the resources it is connected to and sends this configuration to the Allocate service. It maintains a connection with the Allocate service which dictates wether the resource it is responsible for should appear "online" or not```
