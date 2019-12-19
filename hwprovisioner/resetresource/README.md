# "reset resource" service

It is the responsibility of the "Reset Resource" service to reset resources that have been provisioned using the Allocate API to a known safe state. The problem to solve here is ensuring that each device is in a clean state, ready for it's next load of tests.

*Scenario: "As a developer, when I no longer have use of a resource, the hw provisioner should ensure that resource has been reset to a known safe configuration so that it's reliable in the next use"*

## api

```json
# The reset resource service has no exposed API. Instead, it gets job from a queue in Redis and communicates directly with the resource
```

