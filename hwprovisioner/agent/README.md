# agent

It is the responsibility of the agent to inform the Allocate service of the resources the agent is connected to, and to report on the health status of the resources the agent is connected to. This populates the inventory on Allocate.

*Scenario: "As a systems engineer, I want to add a new nvidia server to the Allocate inventory"*

## api

```json
# The agent has no exposed API. Instead it is passed configuration for the resources it should be connected to and reports their status up to the Allocate service
```
