# -*- coding: utf-8 -*-
"""
Created on Tue Nov 21 11:12:02 2023

@author: Markus
"""

# ## Import packages
from filip.clients.ngsi_v2.cb import ContextBrokerClient
from filip.clients.ngsi_v2.client import HttpClientConfig
from filip.clients.ngsi_v2.iota import IoTAClient
from filip.clients.ngsi_v2.quantumleap import QuantumLeapClient
from filip.models.base import DataType, FiwareHeader
from filip.models.ngsi_v2.base import Status
from filip.models.ngsi_v2.context import ContextEntity, ContextAttribute, \
    NamedContextAttribute, NamedCommand
from filip.models.ngsi_v2.iot import Device, ServiceGroup, TransportProtocol, \
    StaticDeviceAttribute, DeviceAttribute, LazyDeviceAttribute, DeviceCommand
from filip.models.ngsi_v2.subscriptions import Subscription, Message

import certifi
import json
import logging
import paho.mqtt.client as mqtt
import random
import requests
import ssl
import time
from urllib.parse import urlparse
from uuid import uuid4

#%%

# ## Parameters
#
# Host addresses - the ports do not necessarily need to be provided, for MQTT
# however, the port is required
# Host address of Context Broker
CB_URL = "http://localhost:1026"
# Host address of IoT-Agent
IOTA_URL = "http://localhost:4041"
# Host address of QuantumLeap
QL_URL = "http://localhost:8668"
# Host address of MQTT broker
MQTT_BROKER_URL = "mqtt://localhost:1883"
#
# FIWARE-Service
SERVICE = 'openiot'
# FIWARE-Servicepath
SERVICE_PATH = '/'
# 
# MQTT credentials if required
MQTT_USER = "mqtt_user"
MQTT_PW = "mqtt_password"

#%% # Define a class for Fiware testing
class Fiware_filip_test():

    def __init__(self, service='openiot', service_path='/',
                 cb_url='http://localhost:1026',
                 iota_url='http://localhost:4041',
                 ql_url='http://localhost:8668',
                 mqtt_url='mqtt://localhost:1883',
                 mqtt_credentials={'MQTT_USER':'mqtt_user',
                                   'MQTT_PW':'mqtt_password'}):
        # # 1 FiwareHeader
        #
        # First a create a fiware header that you want to work with
        # For more details on the headers check the official documentation:
        # https://fiware-orion.readthedocs.io/en/master/user/multitenancy/index.html
        #
        # In short a fiware header specifies a location in Fiware where the
        # created entities will be saved and requests are executed.
        # It can be thought of as a separated subdirectory where you work in.
        self.fiware_header = FiwareHeader(service=service,
                                     service_path=service_path)
        self.service_group  = None
        self.device         = None

        # initialize / create clients
        self.cb_url      = cb_url
        self.cb_client   = ContextBrokerClient(url=cb_url,   
                                               fiware_header=self.fiware_header)
        self.iota_url    = iota_url
        self.iota_client = IoTAClient(url=iota_url,          
                                      fiware_header=self.fiware_header)
        self.ql_url      = ql_url
        self.ql_client   = QuantumLeapClient(url=ql_url,     
                                             fiware_header=self.fiware_header)
        self.mqtt_url    = urlparse(mqtt_url)
        self.mqtt_client = mqtt.Client(client_id=str(uuid4()), # random client ID
                                              clean_session=None,
                                              userdata=None,
                                              protocol=mqtt.MQTTv5,
                                              transport="tcp",
                                              reconnect_on_failure=True)
        self.mqtt_client.username_pw_set(username=mqtt_credentials['MQTT_USER'], 
                                         password=mqtt_credentials['MQTT_PW'])
        # enable TLS for MQTT communication
        # self.mqtt_client.tls_set(ca_certs=certifi.where(), tls_version=ssl.PROTOCOL_TLSv1_2)
        # self.mqtt_client.tls_set(cert_reqs=ssl.CERT_NONE)
        # self.mqtt_client.tls_insecure_set(False)

        self.max_retries = 5

    # Various testing functions for getting version information, and performing 
    # CRUD (create, read, update, delete) operations
    # Functions for getting version information
    def test_get_OCB_version(self):
        """Prints and returns the version information of the Context Broker."""
        print(f"\n")
        print(f"OCB Version: {json.dumps(self.cb_client.get_version(), indent=2)}\n")
        self.cb_version = self.cb_client.get_version()
        return self.cb_version

    def test_get_IOTA_version(self):
        """Prints and returns the version information of the IoT-Agent."""
        print(f"\n")
        print(f"Iot-Agent Version: {self.iota_client.get_version()}\n")
        self.iota_version = self.iota_client.get_version()
        return self.iota_version

    def test_get_QL_version(self):
        """Prints and returns the version information of QuantumLeap."""
        print(f"\n")
        print(f"QuantumLeap Version: {self.ql_client.get_version()}\n")
        self.ql_version = self.ql_client.get_version()
        return self.ql_version

    # Functions for testing CRUD operations
    def test_get_versions(self):
        """Prints and returns the version information of OCB, IoT-Agent, and QuantumLeap."""
        self.test_get_OCB_version()
        self.test_get_IOTA_version()
        self.test_get_QL_version()
        return self.cb_version, self.iota_version, self.ql_version

    def test_get_service_list(self, surpress_print=False):
        self.iota_service_list = self.iota_client.get_group_list()
        if not surpress_print:
            print(f"\n")
            print(f"IoTA Service list: {self.iota_client.get_group_list()}\n")
        return self.iota_service_list

    def test_get_entity_list(self, surpress_print=False):
        self.cb_entity_list = self.cb_client.get_entity_list()
        if not surpress_print:
            print(f"\n")
            print(f"OCB Entity list: {self.cb_client.get_entity_list()}\n")
        return self.cb_entity_list

    def test_get_device_list(self, surpress_print=False):
        self.iota_device_list = self.iota_client.get_device_list()
        if not surpress_print:
            print(f"\n")
            print(f"IoTA Device list: {self.iota_client.get_device_list()}\n")
        return self.iota_device_list

    def test_get_registration_list(self):
        self.cb_registration_list = self.cb_client.get_registration_list()
        print(f"\n")
        print(f"OCB Registration list: {self.cb_client.get_registration_list()}\n")
        return self.cb_registration_list

    def test_get_subscription_list(self, surpress_print=False):
        self.cb_subscription_list = self.cb_client.get_subscription_list()
        if not surpress_print:
            print(f"\n")
            print(f"OCB Subscription list: {self.cb_client.get_subscription_list()}\n")
        return self.cb_subscription_list

    def test_post_service(self, service, force=True):
        # Check if the entity already exists
        self.test_get_service_list(surpress_print=True)
        service_already_existent = (service.resource, 
                                    service.apikey) in [
                                    (i.resource, i.apikey) 
                                    for i in iota_service_list]
        # Post the service according to settings
        # Cases: 1. already existing + force: delete old service and create new
        # 2. already existing + not force: return 'already existing
        # 3. not already existing: post service'
        # Case 1:
        if service_already_existent and force:
            # Delete old services
            print('\n Service already exists. Continue by deleting the service first.\n')
            self.test_delete_service(service)
            # give it a little bit of time for processing
            time.sleep(1)
            for i in range(self.max_retries):
                try:
                    self.iota_client.post_groups(service_groups=[service])
                    break
                except:
                    continue
            self.test_get_service_list()
        # Case 3:
        elif not service_already_existent:
            # give it a little bit of time for processing
            time.sleep(1)
            for i in range(self.max_retries):
                try:
                    self.iota_client.post_groups(service_groups=[service])
                    break
                except:
                    continue
            self.test_get_service_list()
        elif service_already_existent and not force:
            return print('\n Service already exists. Returned without renewed POST request.\n')
        else:
            print('\n Unconsidered case in posting service.\n')
        # Check if posting the service has been successful
        time.sleep(1)
        service_already_existent = (service.resource, 
                                    service.apikey) in [
                                    (i.resource, i.apikey) 
                                    for i in self.iota_service_list]
        # print(service_already_existent)
        if service_already_existent:
            return print('\n POST service request terminated successfully.\n')
        else:
            return print('\n Could not POST service.\n')

    def test_post_entity(self, entity, force=True):
        # Check if the entity already exists
        self.test_get_entity_list(surpress_print=True)
        entity_already_existent = self.does_entity_exist(entity_id=entity.id, 
                                                entity_type=entity.type)
        # Post the entity according to settings
        # Cases: 1. already existing + force: delete old entity and create new
        # 2. already existing + not force: return 'already existing
        # 3. not already existing: post entity'
        # Case 1:
        if entity_already_existent and force:
            # Delete old entities
            print('\n Entity already exists. Continue by deleting the entity first.\n')
            self.test_delete_entity(entity)
            # give it a little bit of time for processing
            time.sleep(1)
            for i in range(self.max_retries):
                try:
                    self.cb_client.post_entity(entity=entity)
                    break
                except:
                    continue
            self.test_get_entity_list()
        # Case 3:
        elif not entity_already_existent:
            # give it a little bit of time for processing
            time.sleep(1)
            for i in range(self.max_retries):
                try:
                    self.cb_client.post_entity(entity=entity)
                    break
                except:
                    continue
            self.test_get_entity_list()
        # Case 2:
        elif entity_already_existent and not force:
            return print('\n Entity already exists. Returned without renewed POST request.\n')
        else:
            print('\n Unconsidered case in posting entity.\n')
        # Check if posting the entity has been successful
        time.sleep(1)
        entity_already_existent = self.does_entity_exist(entity_id=entity.id, 
                                                entity_type=entity.type)
        if entity_already_existent:
            return print('\n POST entity request terminated successfully.\n')
        else:
            return print('\n Could not POST entity.\n')

    def test_post_device(self, device, force=True):
        # Check if the device already exists
        self.test_get_device_list(surpress_print=True)
        device_already_existent = self.does_device_exist(device_id=device.device_id)
        # Post the device according to settings
        # Cases: 1. already existing + force: delete old device and create new
        # 2. already existing + not force: return 'already existing'
        # 3. not already existing: post device
        # Case 1:
        if device_already_existent and force:
            # Delete old devices
            print('\n Device already exists. Continue by deleting the device first.\n')
            self.test_delete_device(device)
            # give it a little bit of time for processing
            time.sleep(1)
            for i in range(self.max_retries):
                try:
                    self.iota_client.post_device(device=device)
                    break
                except:
                    continue
            self.test_get_device_list()
        # Case 3:
        elif not device_already_existent:
            # give it a little bit of time for processing
            time.sleep(1)
            for i in range(self.max_retries):
                try:
                    self.iota_client.post_device(device=device)
                    break
                except:
                    continue
            self.test_get_device_list()
        # Case 2:
        elif device_already_existent and not force:
            return print('\n Device already exists. Returned without renewed POST request.\n')
        else:
            print('\n Unconsidered case in posting device.\n')
        # Check if posting the device has been successful
        time.sleep(1)
        device_already_existent = self.does_device_exist(device_id=device.device_id)
        if device_already_existent:
            return print('\n POST device request terminated successfully.\n')
        else:
            return print('\n Could not POST device.\n')

    def test_post_subscription(self, subscription, force=True):
        # Check if the subscription already exists
        self.test_get_subscription_list(surpress_print=True)
        # TODO: not the cleanest way as there might be multiple subscriptions
        # with different ids für the same entity?
        subscription_already_existent = subscription.id in [
                        i.id for i in cb_subscription_list]
        # Post the subscription according to settings
        # Cases: 1. already existing + force: delete old subscription and create new
        # 2. already existing + not force: return 'already existing'
        # 3. not already existing: post subscription
        # Case 1:
        if subscription_already_existent and force:
            # Delete old subscriptions
            print('\n Subscription already exists. Continue by deleting the subscription first.\n')
            self.test_delete_subscription(subscription)
            # give it a little bit of time for processing
            time.sleep(1)
            for i in range(self.max_retries):
                try:
                    sub_id = self.cb_client.post_subscription(subscription=subscription,
                                                     throttling=0)
                    break
                except:
                    continue
            self.test_get_subscription_list()
        # Case 3:
        elif not subscription_already_existent:
            # give it a little bit of time for processing
            time.sleep(1)
            for i in range(self.max_retries):
                try:
                    sub_id = self.cb_client.post_subscription(subscription=subscription)
                    break
                except:
                    continue
            self.test_get_subscription_list()
        # Case 2:
        elif subscription_already_existent and not force:
            return None, print('\n Subscription already exists. Returned without renewed POST request.\n')
        else:
            print('\n Unconsidered case in posting subscription.\n')
        # Check if posting the subscription has been successful
        time.sleep(1)
        subscription_already_existent = sub_id in [
                        i.id for i in self.cb_subscription_list]
        if subscription_already_existent:
            return sub_id, print('\n POST subscription request terminated successfully.\n')
        else:
            return sub_id, print('\n Could not POST subscription.\n')

    def test_patch_subscription(self, subscription):
        # give it a little bit of time for processing
        time.sleep(1)
        for i in range(self.max_retries):
            try:
                self.cb_client.update_subscription(subscription=subscription)
                break
            except:
                continue
        self.test_get_subscription_list()

    def test_patch_entity(self, entity):
        # give it a little bit of time for processing
        time.sleep(1)
        for i in range(self.max_retries):
            try:
                self.cb_client.patch_entity(entity=entity)
                break
            except:
                continue
        self.test_get_entity_list()

    def test_put_device(self, device):
        # FIXME: Error in FiLiP library: PATCH does not exist in the IoTA API for
        # updating devices
        # give it a little bit of time for processing
        time.sleep(1)
        for i in range(self.max_retries):
            try:
                self.iota_client.update_device(device=device)
                break
            except:
                continue
        self.test_get_device_list()

    def test_delete_service(self, service):
        # give it a little bit of time for processing
        time.sleep(1)
        for i in range(self.max_retries):
            try:
                self.iota_client.delete_group(resource=service.resource,
                                               apikey=service.apikey)
                break
            except:
                continue
        self.test_get_service_list()

    def test_delete_entity(self, entity):
        # give it a little bit of time for processing
        time.sleep(1)
        for i in range(self.max_retries):
            try:
                self.cb_client.delete_entity(entity_id=entity.id, 
                                             entity_type=entity.type)
                break
            except:
                continue
        self.test_get_entity_list()

    def test_delete_all_entities(self):
        self.cb_client.delete_entities(self.cb_client.get_entity_list())

    def test_delete_device(self, device):
        # give it a little bit of time for processing
        time.sleep(1)
        for i in range(self.max_retries):
            try:
                self.iota_client.delete_device(device_id=device.device_id)
                break
            except:
                continue
        self.test_get_device_list()

    def test_delete_subscription(self, subscription):
        # get Subscription ID
        self.test_get_subscription_list(surpress_print=True)
        # index = [idx for idx, element in enumerate(cb_subscription_list) if 
        #          subscription.id == element.subject.entities[0].id]
        # give it a little bit of time for processing
        time.sleep(1)
        # if index:
        #     for i in index:
        #         sub_id = self.cb_subscription_list[i].id
        #         # print('\n Sub ID: '+sub_id+'\n')
        for i in range(self.max_retries):
            try:
                self.cb_client.delete_subscription(subscription_id=subscription.id)
                break
            except:
                continue
        self.test_get_subscription_list()

    def get_service_group(self):
        return self.service_group

    def set_service_group(self, service_group):
        self.service_group = service_group

    def get_device(self):
        return self.device

    def set_device(self, device):
        self.device = device

    # MQTT functions for connecting, disconnecting, and handling messages
    def mqtt_connect(self):
        """Connects to the MQTT broker."""
        # Set up callbacks
        self.mqtt_client.on_connect     = self.on_connect
        self.mqtt_client.on_subscribe   = self.on_subscribe
        self.mqtt_client.on_message     = self.on_message
        self.mqtt_client.on_disconnect  = self.on_disconnect

        # Connect to the MQTT broker
        self.mqtt_client.connect(host=self.mqtt_url.hostname,
                                port=self.mqtt_url.port,
                                keepalive=60,
                                bind_address="",
                                bind_port=0,
                                clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY,
                                properties=None)

    def mqtt_disconnect(self):
        """Disconnects from the MQTT broker."""
        self.mqtt_client.disconnect()

    def mqtt_start_loop(self):
        """Starts the MQTT client loop."""
        self.mqtt_client.loop_start()

    def mqtt_stop_loop(self):
        """Stops the MQTT client loop."""
        self.mqtt_client.loop_stop()

    # Callback functions for MQTT events
    def on_connect(self, client, userdata, flags, reasonCode, properties=None):
        """Callback function when connected to the MQTT broker."""
        if reasonCode != 0:
            logger.error(f"Connection failed with error code: '{reasonCode}'")
            raise ConnectionError
        else:
            logger.info("Successfully, connected with result code "+str(
                reasonCode))
        client.subscribe(f"/{self.device.apikey}/{self.device.device_id}/cmd")

    def on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        """Callback function when subscribed to an MQTT topic."""
        logger.info("Successfully subscribed to with QoS: %s", granted_qos)

    def on_message(self, client, userdata, msg):
        """Callback function when a message is received from the MQTT broker."""
        logger.info(msg.topic + " " + str(msg.payload))
        data = json.loads(msg.payload)
        res = {k: v for k, v in data.items()}
        print(msg.payload)
        client.publish(topic=f"/json/{self.service_group.apikey}"
                             f"/{self.device.device_id}/cmdexe",
                       payload=json.dumps(res))

    def on_disconnect(self, client, userdata, reasonCode, properties):
        """Callback function when disconnected from the MQTT broker."""
        logger.info("MQTT client disconnected" + str(reasonCode))

    # auxiliary functions
    def does_entity_exist(self,
                           entity_id: str,
                           entity_type: str) -> bool:
        """
        Test if an entity with given id and type is present in the CB
        Args:
            entity_id: Entity id
            entity_type: Entity type
        Returns:
            bool; True if entity exists

        Raises:
            RequestException, if any error occurres (e.g: No Connection),
            except that the entity is not found
        """
        try:
            self.cb_client.get_entity(entity_id=entity_id, entity_type=entity_type)
        except requests.RequestException as err:
            if not err.response.status_code == 404:
                raise
            return False
        return True

    def does_device_exist(self, device_id: str) -> bool:
        """
        Test if a device with the given id exists in Fiware
        Args:
            device_id (str)
        Returns:
            bool
        """
        try:
            self.iota_client.get_device(device_id=device_id)
            return True
        except requests.RequestException as err:
            if not err.response.status_code == 404:
                raise
            return False

#%%
if __name__ == '__main__':
    # Set up logging configuration
    logging.basicConfig(
        level='INFO',
        format='%(asctime)s %(name)s %(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)

    # Initialize Fiware_filip_test class with specified parameters
    test = Fiware_filip_test(service=SERVICE,
                             service_path=SERVICE_PATH,
                             cb_url=CB_URL,
                             iota_url=IOTA_URL,
                             ql_url=QL_URL,
                             mqtt_url=MQTT_BROKER_URL,
                             mqtt_credentials={'MQTT_USER':MQTT_USER,
                                               'MQTT_PW':MQTT_PW})

#%% GET endpoints
    # GET Versions
    cb_version, iota_version, ql_version = test.test_get_versions()

    # GET Registration list
    cb_registration_list = test.test_get_registration_list()

    # GET Service list
    iota_service_list = test.test_get_service_list()

    # GET Entity list
    cb_entity_list = test.test_get_entity_list()

    # GET Device list
    iota_device_list = test.test_get_device_list()

    # GET Subscription list
    cb_subscription_list = test.test_get_subscription_list()

#%% POST endpoints

    # POST Services
    # FIXME: Sometimes the call to evaluate if the service has already been
    # created won't work and thus the ouput returns 'Could not POST service'
    # Create test service group
    service_group1 = ServiceGroup(entity_type='Thing',
                                  resource='/iot/json',
                                  # apikey=str(uuid4()))
                                  apikey='testservice')
    test.test_post_service(service=service_group1, force=True)
    test.set_service_group(service_group=service_group1)

    # POST Entities
    # Create test entities
    # using a dict
    room1 = {"id": "Room1",
              "type": "Room",
              "temperature": {"value": 21.5,
                              "type": "Float"},
              "humidity": {"value": 47.3,
                          "type": "Float"}
              }
    room1_entity = ContextEntity(**room1)
    # using constructor and interfaces
    room2_entity = ContextEntity(id="Room2", type="Room")
    temp_attr = NamedContextAttribute(name="temperature", value=22.1,
                                      type=DataType.FLOAT)
    humidity_attr = NamedContextAttribute(name="humidity", value=28.6,
                                          type="Float")
    room2_entity.add_attributes([temp_attr, humidity_attr])
    test.test_post_entity(entity=room1_entity, force=True)
    test.test_post_entity(entity=room2_entity, force=True)
    cb_entity_list = test.cb_entity_list

    # POST Devices
    # using dict
    example_device = {"device_id": "sensor008",
                      "service": SERVICE,
                      "service_path": SERVICE_PATH,
                      "entity_name": "sensor1",
                      "entity_type": "Sensor",
                      "timezone": 'Europe/Berlin',
                      "timestamp": True,
                      "apikey": "1234",
                      "protocol": "IoTA-UL",
                      "transport": "MQTT",
                      "lazy": [],
                      "commands": [],
                      "attributes": [],
                      "static_attributes": [],
                      "internal_attributes": [],
                      "explicitAttrs": False,
                      "ngsiVersion": "v2"}
    device1 = Device(**example_device)
    # directly
    device2 = Device(device_id="sensor009",
                      service=SERVICE,
                      service_path=SERVICE_PATH,
                      entity_name="sensor2",
                      entity_type="Sensor",
                      transport=TransportProtocol.HTTP,
                      endpoint="http://localhost:1234")
    # building device model
    attribute1 = DeviceAttribute(name='time',
                            object_id='t',
                            type="Number")
    attribute2 = DeviceAttribute(name='power',
                            object_id='p',
                            type="Number")
    attribute3 = DeviceAttribute(name='temperature',
                            object_id='T',
                            type="Number",
                            metadata={"unit":
                                        {"type": "Unit",
                                         "value": {
                                             "name": "degree Celsius"
                                             }
                                         }
                            })
    cmd = DeviceCommand(name="heater_on",
                        type=DataType.BOOLEAN)
    device3 = Device(device_id="device:003",
                    entity_name="Heater:001",
                    entity_type="Heater",
                    apikey="heater",
                    attributes=[attribute1,attribute2,attribute3],
                    commands=[cmd],
                    transport='MQTT',
                    protocol='IoTA-JSON')
    test.test_post_device(device=device1, force=True)
    test.test_post_device(device=device2, force=True)
    test.test_post_device(device=device3, force=True)
    iota_device_list = test.iota_device_list
    test.set_device(device=device3)

    # POST Subscriptions
    # Generate Subscription object
    subscription = {
        "id": "656f336ce0fa548de70a106f", #"example_subscription_ID",
        "description": "Subscription to receive MQTT-Notifications about "
                       "device:003",
        "subject": {
            "entities": [
                {
                    "id": device3.entity_name,
                    "type": device3.entity_type
                }
            ],
            "condition" : {
                "attrs" : [
                    "time",
                    "power",
                    "temperature"
                    ]
            }
        },
        "notification": {
            # "mqtt": {
            #     "url": MQTT_BROKER_URL,
            #     "topic": "/",
            #     "user": MQTT_USER,
            #     "passwd": MQTT_PW
            # },
            "http": {
                "url": QL_URL+'/v2/notify'
                },
            "attrs" : [
                "time",
                "power",
                "temperature"
                ],
            "metadata": [
                "dateCreated",
                "dateModified"
                ]
        },
        "throttling": 0
    }
    subscription = Subscription(**subscription)
    subscription_id = test.test_post_subscription(subscription=subscription, force=True)[0]
    subscription = test.cb_client.get_subscription(subscription_id=subscription_id)
    cb_subscription_list = test.cb_subscription_list

#%% MQTT connection
    test.mqtt_connect()
    test.mqtt_start_loop()

    # Publish MQTT data for device attributes
    for i in range(10):
        for attr in device3.attributes:
            payload = json.dumps({attr.object_id: random.uniform(19.0,26.0)})
            logger.info("Send data to platform:" + payload)
            test.mqtt_client.publish(
                topic=f"/json/{test.service_group.apikey}/{test.device.device_id}/attrs",
                payload=payload)
        time.sleep(1)

    # Post command
    for i in range(10):
        if i % 2 == 1:
            value = True
        else:
            value = False
        context_command = NamedCommand(name=cmd.name,
                                        value=value)
        test.cb_client.post_command(entity_id=device3.entity_name,
                                entity_type=device3.entity_type,
                                command=context_command)
        time.sleep(1)

#%% PATCH / PUT endpoints

    # PATCH Subscriptions
    # Deactivate Subscription
    subscription.status = Status.INACTIVE
    test.test_patch_subscription(subscription=subscription)
    cb_subscription_list = test.cb_subscription_list
    # Reactivate Subscription
    subscription.status = Status.ACTIVE
    test.test_patch_subscription(subscription=subscription)
    cb_subscription_list = test.cb_subscription_list

    # PATCH Entities
    # updating directly
    # test.cb_client.update_attribute_value(entity_id=room1_entity.id,
    #                                           attr_name="temperature",
    #                                           value=20.8)
    # updating the model
    room2_entity.add_attributes({'Space': ContextAttribute(type='Number',
                                                      value=82.5)})
    temp_attr = room2_entity.get_attribute("temperature")
    temp_attr.value = 22.4
    room2_entity.update_attribute([temp_attr])
    test.test_patch_entity(room2_entity)
    ocb_entity_list = test.cb_entity_list

    # PUT Devices
    # FIXME: Currently not working due to an error in the FiLiP library
    # device2.add_attribute(StaticDeviceAttribute(name="address",
    #                                             type=DataType.TEXT,
    #                                             value="Lichtenhof 3"))
    # device2.add_attribute(DeviceAttribute(name="temperature",
    #                                       object_id="t"))
    # device2.add_attribute(LazyDeviceAttribute(name="humidity"))
    # device2.add_attribute(DeviceCommand(name="on"))
    # test.test_put_device(device=device2)
    # iota_device_list = test.iota_device_list

    # Read historic data via QL
    cb_entity_list = test.test_get_entity_list()
    debug_variable = cb_entity_list
    debug_variable2 = test.ql_client.get_entities()
    try:
        data = test.ql_client.get_entity_by_id(device3.entity_name).to_pandas()
        print(data)
    except:
        print('\n Cannot retrieve historic data.\n')

#%% DELETE endpoints

    # DELETE Entities
    test.test_delete_entity(entity=room1_entity)
    test.test_delete_entity(entity=room2_entity)
    cb_entity_list = test.cb_entity_list

    # # DELETE ALL ENTITIES - USE WITH CAUTION!!!
    #     test.test_delete_all_entities()

    # DELETE Devices
    test.test_delete_device(device=device1)
    test.test_delete_device(device=device2)
    test.test_delete_device(device=device3)
    iota_device_list = test.iota_device_list

    # DELETE Subscriptions
    test.test_delete_subscription(subscription=subscription)
    cb_subscription_list = test.cb_subscription_list

    # DELETE Services
    test.test_delete_service(service_group1)
    iota_service_list = test.iota_service_list

    # TODO: Implement remaining functionality tests:
    # PUT Service,
    # Delete entity in QL
    # # Subscription: Notify QL via Orion
    # for i in range(5, 10):
    #     cb_client.update_attribute_value(entity_id=hall_entity.id,
    #                                      entity_type=hall_entity.type,
    #                                      attr_name="temperature",
    #                                      value=i)
    # # delete entity in QL
    # ql_client.delete_entity(entity_id=hall_entity.id,
    #                         entity_type=hall_entity.type)

    # # Clean up (Optional)
    #
    test.mqtt_stop_loop()
    test.mqtt_disconnect()
    # Close client
    test.iota_client.close()
    test.cb_client.close()
    test.ql_client.close()