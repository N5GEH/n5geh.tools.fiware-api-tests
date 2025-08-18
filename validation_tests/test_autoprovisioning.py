import time
import unittest
import json
import os.path
from functools import wraps
from typing import Callable
from paho.mqtt.client import Client
from filip.clients.ngsi_v2 import ContextBrokerClient, IoTAClient
from filip.models import FiwareHeader
from filip.models.ngsi_v2.context import ContextEntity, NamedContextAttribute
from filip.models.ngsi_v2.iot import Device, ServiceGroup, DeviceAttribute
from filip.utils.cleanup import clear_all, clean_test
from requests import HTTPError
from copy import deepcopy

from settings import settings

path_input = "inputs/test_autoprovisioning"

standard_entity = {
    "id": "Entity:001",
    "type": "Entity",
    "attribute1": {
        "type": "Number",
        "value": 1
    },
    "attribute2": {
        "type": "Number",
        "value": 2
    },
    "attribute3": {
        "type": "Number",
        "value": 3
    },
    "attribute4": {
        "type": "Number",
        "value": 4
    }
}

standard_device = {
    "device_id": "Device:001",
    "entity_name": standard_entity["id"],
    "entity_type": standard_entity["type"],
    "transport": "MQTT",
    "explicitAttrs": True,
    "attributes": [
        {
            "name": "attribute1",
            "type": "Number",
            "object_id": "a1"
        },
        {
            "name": "attribute2",
            "type": "Number",
            "object_id": "a2"
        },
        {
            "name": "attribute3",
            "type": "Number",
            "object_id": "a3"
        },
        {
            "name": "attribute4",
            "type": "Number",
            "object_id": "a4"
        }
    ]
}

standard_service_group = {
    "resource": "/iot/json",
    "apikey": "fiware-api-test",
    "explicitAttrs": True,
    "autoprovision": False
}


class TestAutoprovisioning(unittest.TestCase):

    def setUp(self) -> None:
        self.fiware_header = FiwareHeader(
            service=settings.FIWARE_SERVICE,
            service_path=settings.FIWARE_SERVICEPATH,
        )

        self.cb_client = ContextBrokerClient(url=settings.CB_URL,
                                             fiware_header=self.fiware_header)
        self.iotc = IoTAClient(url=settings.IOTA_JSON_URL,
                               fiware_header=self.fiware_header)

        self.mqttc = Client()
        self.mqttc.username_pw_set(username=settings.MQTT_USERNAME,
                                   password=settings.MQTT_PASSWORD)
        if settings.MQTT_TLS:
            self.mqttc.tls_set()
        self.mqttc.connect(host=settings.MQTT_BROKER_URL.host,
                           port=settings.MQTT_BROKER_URL.port)

        # TODO: clean up
        # TODO: Create service group

    def test_autoprovision(self):

        # TODO: Send data for a non existing device
        # TODO: Check if device is created
        # TODO: Check if entity is created
        # TODO: Check if entity holds the right data
        pass

    def tearDown(self) -> None:
        self.fiware_header = FiwareHeader(
            service=settings.FIWARE_SERVICE,
            service_path=settings.FIWARE_SERVICEPATH,
        )
        self.iotc.close()
        self.cb_client.close()


if __name__ == "__main__":
    unittest.main()
