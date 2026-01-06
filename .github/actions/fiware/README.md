# Configurable FIWARE Setup Action

This GitHub Action allows you to start a complete FIWARE stack using Docker Compose, with configurable versions for all core services. You can set the desired versions for Orion, MongoDB, IoT Agent JSON, IoT Agent UL, QuantumLeap, CrateDB, and Orion-LD via workflow inputs.

**Features:**
- Start and manage FIWARE services in CI/CD pipelines
- Health checks for all core services
- Easy version configuration via workflow inputs
- Debug output on failure

**Usage Example:**
Refer to the example in your workflow file:
```yaml
- name: Setup FIWARE Services
  uses: RWTH-EBC/fiware-api-tests/.github/actions/fiware@main
  with:
    orion-version: '3.12.0'
    mongo-db-version: '5.0.24'
    iot-agent-json-version: '1.26.0'
    iot-agent-ul-version: '1.22.0'
    quantumleap-version: '1.0.0'
    crate-version: '4.8.4'
    orion-ld-version: '1.5.1'
    healthcheck-urls: 'http://localhost:1026/version http://localhost:8668/version'
    timeout-seconds: 120
```

See `action.yml` and `docker-compose.yml` for details on configuration and available options.
