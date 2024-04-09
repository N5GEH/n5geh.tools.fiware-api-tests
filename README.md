# Fiware API Tests

This project includes various test scenarios of the FIWARE infrastructure. Depending on the use case, the FIWARE API is used to ensure that all basic components, such as the Orion Context Broker or the IoT Agent, function reliably. 

Tests confirm that your API is working as expected, that integrations between services are functioning reliably, and that any changes haven't broken existing functionality. In this project, Postman requests are used for direct testing of the API. For more complex scenarios, libraries like FiLiP are used.

## Postman

The Tests tab of a Postman request allows for any post-processing after a request is sent and includes the ability to write tests for assessing response data. The Test tab sandbox has the Chai.js library built in, so you can use Chai's behavior-driven development (BDD) syntax to create readable test assertions.

### Write a Collection of Tests

You can add tests to individual requests, collections, and folders in a collection. Postman includes code snippets you add and then change to suit your test logic.

To add tests to a request, open the request and enter your code in the Tests tab. Tests will execute after the request runs. The output is in the response's Test Results tab.

![Alt text](images/request-test-tab-v10-19.jpg)

You can add test scripts to a collection, a folder, or a single request within a collection. A test script associated with a collection will run after every request in the collection.

When you run a collection the collection runner displays the test results, including the response time in milliseconds and details about whether a specific request in the collection passed or failed its tests.

### Include Test Collection in GitLab CI

In the next step you can automate your testing by integrating collection runs within your CI/CD configuration. It is very practical to store important parameters of a test collection, such as the OCB URL or the FIWARE Service, in variables before setting up the pipeline. The image below shows an example of Postman variables in the test case *Entity Update*. Note that the hostname of the OCB corresponds to the name of the service in the *.gitlab-ci.yml* file (here *docker*).

![alt text](images/postman_variables.png)

Once a collection is completed, we need to export it in JSON format and store the file in the Git repository. To run a Postman collection in the pipeline, we create the necessary FIWARE instances (see *docker-compose.yml*) and run the exported JSON file from the command-line collection runner newman (see *.gitlab-ci.yml* for the pipeline).