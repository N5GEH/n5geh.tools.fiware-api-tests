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

from settings import settings

path_input = "inputs/test_data_model"

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
        }
    ]
}

standard_service_group = {
    "resource": "/iot/json",
    "apikey": "fiware-api-test",
    "explicitAttrs": True,
    "autoprovision": False
}


def standard_test(*,
                  fiware_service: str,
                  fiware_servicepath: str,
                  cb_url: str = None,
                  iota_url: str = None,
                  ql_url: str = None,
                  ) -> Callable:
    # clean up
    fiware_header = FiwareHeader(service=fiware_service,
                                 service_path=fiware_servicepath)
    clear_all(fiware_header=fiware_header,
              cb_url=cb_url,
              iota_url=iota_url,
              ql_url=ql_url)

    # initial entity
    entity = ContextEntity(**standard_entity)
    with ContextBrokerClient(url=cb_url, fiware_header=fiware_header) as cbc:
        cbc.post_entity(entity=entity)

    # initial service group
    service_group = ServiceGroup(**standard_service_group)
    with IoTAClient(url=iota_url, fiware_header=fiware_header) as iotac:
        iotac.post_group(service_group=service_group)

    # initial device
    device = Device(**standard_device)
    with IoTAClient(url=iota_url, fiware_header=fiware_header) as iotac:
        iotac.post_device(device=device)

    # wrapper
    def decorator(func):
        #  Wrapper function for the decorated function
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


class TestDataModel(unittest.TestCase):

    def setUp(self) -> None:
        self.fiware_header = FiwareHeader(
            service=settings.FIWARE_SERVICE,
            service_path=settings.FIWARE_SERVICEPATH,
        )

        # clear_all(fiware_header=self.fiware_header,
        #           cb_url=settings.CB_URL,
        #           iota_url=settings.IOTA_JSON_URL
        #           )

        # Initial client
        self.cb_client = ContextBrokerClient(url=settings.CB_URL,
                                             fiware_header=self.fiware_header)
        self.iotc = IoTAClient(url=settings.IOTA_JSON_URL,
                               fiware_header=self.fiware_header)

        self.mqttc = Client()
        self.mqttc.connect(host=settings.MQTT_BROKER_URL.host,
                           port=settings.MQTT_BROKER_URL.port)

        # device list
        self.devices_list = [
            {
                "ID": "eui-a81758fffe045eea",
                "sensor_type": "Elsys ERS CO2"
            },
            {
                "ID": "eui-a81758fffe045ef3",
                "sensor_type": "Elsys ERS CO2"
            },
            {
                "ID": "eui-a81758fffe045eee",
                "sensor_type": "Elsys ERS CO2"
            },
            {
                "ID": "eui-a81758fffe045f59",
                "sensor_type": "Elsys ERS CO2"
            },
            {
                "ID": "eui-10ce45fffe007e89",
                "sensor_type": "AME"
            },
            {
                "ID": "eui-10ce45fffe007e70",
                "sensor_type": "AME"
            },
            {
                "ID": "eui-10ce45fffe007e6e",
                "sensor_type": "AME"
            },
            {
                "ID": "eui-10ce45fffe007e6c",
                "sensor_type": "AME"
            },
            {
                "ID": "eui-0018b2400001a3fb",
                "sensor_type": "Adeunis modbus"
            }
        ]

    def test_data_model_provision(self):
        # 1. load devices from excel table
        pass

        # 2. provisioning
        for device_item in self.devices_list:
            _uid = device_item["ID"]
            device_type = device_item["sensor_type"]
            # create entity
            with open(os.path.join(path_input, "entity_templates",
                                   device_type + ".json")) as f:
                entity_template: dict = json.load(f)
                entity_template['id'] = f"{entity_template['type']}:{_uid}"
                entity = ContextEntity(**entity_template)
                with self.cb_client:
                    self.cb_client.post_entity(entity)
                    entity_fiware = self.cb_client.get_entity(entity_id=entity.id)
                    self.assertEqual(entity_fiware.id, entity_template.get('id'))

            # create device
            with open(os.path.join(path_input, "device_templates",
                                   device_type + ".json")) as f:
                device_template: dict = json.load(f)
                device_template['device_id'] = _uid
                device_template['entity_name'] = f"{entity_template['type']}:{_uid}"
                device = Device(**device_template)
                # test the connection
                with self.iotc:
                    self.iotc.post_device(device=device)
                    device_fiware = self.iotc.get_device(device_id=device.device_id)
                    self.assertEqual(device_fiware.device_id,
                                     device_template.get('device_id'))

        # 3. validate provisioning
        for device in self.iotc.get_device_list():
            entity = self.cb_client.get_entity(entity_id=device.entity_name)
            for attr in device.attributes:
                entity_attr = entity.get_attribute(attr.name)
                self.assertEqual(entity_attr.type, attr.type)

    @standard_test(
        fiware_service=settings.FIWARE_SERVICE,
        fiware_servicepath=settings.FIWARE_SERVICEPATH,
        cb_url=settings.CB_URL,
        iota_url=settings.IOTA_JSON_URL)
    def test_append_attribute(self):
        """
        New attributes are appended
        """
        # append attributes in CB
        new_attribute_name = "attribute3"
        self.cb_client.update_or_append_entity_attributes(
            entity_id=standard_entity["id"],
            entity_type=standard_entity["type"],
            attrs=[
                NamedContextAttribute(**{
                    "name": "attribute3",
                    "type": "Number",
                    "value": 3})],
            append_strict=True)
        # test sending, and fetching, should fail
        topic = f"/json/{standard_service_group['apikey']}/{standard_device['device_id']}/attrs"
        new_value = 33
        self.mqttc.publish(topic=topic, payload=json.dumps({"attribute3": new_value}))
        time.sleep(0.5)
        self.assertNotEqual(new_value,
                            self.cb_client.get_attribute_value(
                                entity_id=standard_entity["id"],
                                entity_type=standard_entity["type"],
                                attr_name=new_attribute_name
                            ))
        # append attributes in IoTAgent
        device = self.iotc.get_device(device_id=standard_device["device_id"])
        device.add_attribute(attribute=DeviceAttribute(
            name=new_attribute_name,
            type="Number",
            object_id=new_attribute_name
        ))
        # standard_device["attributes"].append({
        #     "name": new_attribute_name,
        #     "type": "Number",
        #     "object_id": new_attribute_name
        # })
        self.iotc.update_device(device=device)
        time.sleep(0.5)

        # test sending again, should work
        self.mqttc.publish(topic=topic, payload=json.dumps({"attribute3": new_value}))
        time.sleep(0.5)
        self.assertEqual(new_value,
                         self.cb_client.get_attribute_value(
                             entity_id=standard_entity["id"],
                             entity_type=standard_entity["type"],
                             attr_name=new_attribute_name
                         ))

    def test_delete_attribute(self):
        """
        Attributes are deleted
        :return:
        """
        # delete attributes in IoTAgent
        # test sending, should fail
        # test fetching, attribute should be found
        # delete attributes in CB
        # test fetching, attribute should not be found
        pass

    def test_rename_attribute(self):
        """
        Attributes are renamed
        :return:
        """
        # rename attributes in IoTAgent
        # test sending, and fetching with new name, should fail
        # append new attribute in CB
        # test sending and fetching again, should work
        pass

    def test_anonymous_update(self):
        """
        Anonymous attributes getting updated
        :return:
        """
        # test sending anonymous attributes, and fetching, should fail
        # append new attribute in CB
        # test sending and fetching again, should work
        pass

    def tearDown(self) -> None:
        self.fiware_header = FiwareHeader(
            service=settings.FIWARE_SERVICE,
            service_path=settings.FIWARE_SERVICEPATH,
        )
        clear_all(fiware_header=self.fiware_header,
                  cb_url=settings.CB_URL,
                  iota_url=settings.IOTA_JSON_URL
                  )
        self.iotc.close()
        self.cb_client.close()


if __name__ == "__main__":
    unittest.main()
