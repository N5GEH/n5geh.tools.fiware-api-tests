![E.ON EBC RWTH Aachen University](https://raw.githubusercontent.com/RWTH-EBC/FiLiP/master/docs/logos/EBC_Logo.png)

# FIWARE API Tests

- [Test Cases](#test-cases)
- [Run tests locally](#run-tests-locally)
- [Run in CI/CD pipeline](#run-in-cicd-pipeline)
  - [Configurable FIWARE setup action](#configurable-fiware-setup-action)
  - [The example testing pipeline](#the-example-testing-pipeline)
- [Acknowledgements](#acknowledgements)

This project includes various test scenarios of the FIWARE infrastructure. Depending on the use case, the FIWARE API is used to ensure that all basic components, such as the Orion Context Broker or the IoT Agent, function reliably. 

Tests confirm that your API is working as expected, that integrations between services are functioning reliably, and that any changes haven't broken existing functionality. In this project, the tests cases are implemented in Python using pytest (under the *validation_tests* directory). Some tests
are implemented based on the [FiLiP](https://github.com/RWTH-EBC/FiLiP) library.

## Test Cases
The following table provides an overview of the currently implemented/planned test cases:

| Script                                                                  | Test case name                                                        | Description                                                                                                                                                                                                                                             | Status      |
|-------------------------------------------------------------------------|-----------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|
| [test_data_model.py](./validation_tests/test_data_model.py)             | Data model provisioning                                               | This test case aims at validating the successful creation of entities and devices. This is the basis of nearly all applications. For a realistic scenario, consider the devices and datapoints to be available in an excel sheet.                       | Implemented |
| [test_ql_subscriptions.py](./validation_tests/test_ql_subscriptions.py) | Subscriptions on historic data                                        | This test case aims at validating the successful creation of a subscription on live data to be notified to QuantumLeap in order to store them as historic data in the timeseries database.                                                              | Implemented |
| [test_notification.py](./validation_tests/test_notification.py)         | Notification for forwarding control signal/data to external endpoints | This test case targets at various notification possibilities of Orion Context Broker to notify external endpoints, including custom notifications used for forwarding control signals.                                                                  | Implemented |
| [test_entity_update.py](./validation_tests/test_entity_update.py)       | Entity Update                                                         | This test case covers different ways to update entities: single/multiple values or attributes, add/delete attributes, update metadata etc.                                                                                                              | Implemented |
| [test_iota_cb.py](./validation_tests/test_iota_cb.py)                   | Interaction between IoT Agent and Orion Context Broker                | This is the collection of test cases that cover the fundamental interactions between IoT Agent and Orion context broker. Currently, there are three subcases: <br/>1. Autoprovision functionality; <br/>2. Device groups; <br/>3. `transport` parameter | Implemented |

## Run tests locally
The local testing environment is recommended for developing purpose or for testing with a specific FIWARE instance.

Set up a Python environment:
```bash
cd n5geh.tools.fiware-api-tests
pip install -r requirements.txt
```

To run the tests locally, you will also need to set the environment variables by creating a `.env` file under the `validation_tests` folder. An example `.env.EXAMPLE` file is provided. The necessary variables are:

- LOG_LEVEL
- CB_URL
- IOTA_JSON_URL
- IOTA_URL
- QL_URL  
- MQTT_BROKER_URL
- MQTT_BROKER_URL_INTERNAL
- MQTT_USERNAME (only if required)
- MQTT_PASSWORD (only if required)
- MQTT_TLS (only set to ``True`` if required)
- FIWARE_SERVICE

The test scripts can be executed with pytest command:
```bash
pytest validation_tests --disable-warnings -v
```

## Run in CI/CD pipeline
If you are interested in finding a specific set of FIWARE component versions that work well together, you can use the provided GitHub Actions and workflows to automatically run the tests in a reproducible CI/CD environment.
This setup ensures that your FIWARE stack is reproducibly tested and validated in CI/CD with minimal configuration effort.

### Configurable FIWARE setup action
For basic understanding of GitHub actions, please refer to the official documentation:https://docs.github.com/en/actions/get-started/understand-github-actions
This repository provides ready-to-use GitHub Action (see [`.github/actions/fiware`](.github/actions/fiware)) to select different versions of FIWARE core components and deploy them within a GitHub runner.

An example usage of this action is provided in this workflow:
[`.github/workflows/fiware_setup_test.yml`](.github/workflows/fiware_setup_test.yml).
It starts the FIWARE stack using Docker Compose with configurable service versions and checks the health of all core services.

In short, the specific versions can be overridden in the workflow file by setting the input variables, e.g.:
```yaml
        with:
          healthcheck-urls: 'http://localhost:1026/version http://localhost:8668/version http://localhost:1027/version http://localhost:4041/iot/about'
          timeout-seconds: 60
          orion-version: '3.12.0'
          mongo-db-version: '5.0.24'
          iot-agent-json-version: '1.26.0'
          quantumleap-version: '1.0.0'
          crate-version: '4.8.4'
          orion-ld-version: '1.5.1'
```

### The example testing pipeline

You can use the aforementioned action in any GitHub repository and even extend it with your own test cases or any other processing steps.
This repository provides an example workflow ([`.github/workflows/fiware_api_test.yml`](.github/workflows/fiware_api_test.yml)) to run the validation tests against a FIWARE stack with following versions:

- Orion: `3.12.0`
- MongoDB: `5.0.24`
- IoT Agent JSON: `1.26.0`
- QuantumLeap: `1.0.0`
- CrateDB: `4.8.4`
- Orion-LD: `1.5.1`

## Acknowledgements

This project is a joint development effort between [RWTH-EBC](https://github.com/RWTH-EBC) and [FZJ-ICE1](https://jugit.fz-juelich.de/iek-10/public/ict-platform).
We gratefully acknowledge the financial support of the Federal Ministry
for Economic Affairs and Climate Action (BMWK), promotional references 03EN1030B.

<p>
  <img src="images/BMWE_gefoerdert_en_CMYK.jpg" alt="BMWK funded" width="150"/>
</p>
