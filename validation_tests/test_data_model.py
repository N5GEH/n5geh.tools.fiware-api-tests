import pytest
import time
import json
import os
from paho.mqtt.client import Client, CallbackAPIVersion
from filip.clients.ngsi_v2 import ContextBrokerClient, IoTAClient
from filip.models import FiwareHeader
from filip.models.ngsi_v2.context import ContextEntity, NamedContextAttribute
from filip.models.ngsi_v2.iot import Device, ServiceGroup, DeviceAttribute
from filip.utils.cleanup import clear_all
from requests import HTTPError
from copy import deepcopy

from settings import settings

# get current working directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# set the path to the input directory
path_input = os.path.join(current_dir, 'inputs', 'test_data_model')

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


@pytest.fixture(scope='function')
def standard_setup():
    """
    Fixture to perform standard cleaning and setup before each test.
    """
    # Retrieve parameters
    fiware_service = settings.FIWARE_SERVICE
    fiware_servicepath = settings.FIWARE_SERVICEPATH
    cb_url = settings.CB_URL
    iota_url = settings.IOTA_JSON_URL
    ql_url = None  # Adjust as needed

    fiware_header = FiwareHeader(service=fiware_service,
                                 service_path=fiware_servicepath)
    clear_all(fiware_header=fiware_header,
              cb_url=cb_url,
              iota_url=iota_url,
              ql_url=ql_url)

    # Initial entity
    entity = ContextEntity(**standard_entity)
    with ContextBrokerClient(url=cb_url, fiware_header=fiware_header) as cbc:
        cbc.post_entity(entity=entity)

    # Initial service group
    service_group = ServiceGroup(**standard_service_group)
    try:
        with IoTAClient(url=iota_url, fiware_header=fiware_header) as iotac:
            iotac.post_group(service_group=service_group)
    except HTTPError:  # In case of Conflict error
        pass

    # Initial device
    device = Device(**standard_device)
    with IoTAClient(url=iota_url, fiware_header=fiware_header) as iotac:
        iotac.post_device(device=device)


@pytest.fixture(autouse=True)
def setup_clients(request):
    """
    Fixture to set up clients and other resources.
    """
    self = request.instance  # Access 'self' from the test class

    self.fiware_header = FiwareHeader(
        service=settings.FIWARE_SERVICE,
        service_path=settings.FIWARE_SERVICEPATH,
    )

    # Initial clients
    self.cb_client = ContextBrokerClient(url=settings.CB_URL,
                                         fiware_header=self.fiware_header)
    self.iotc = IoTAClient(url=settings.IOTA_JSON_URL,
                           fiware_header=self.fiware_header)

    self.mqttc = Client(callback_api_version=CallbackAPIVersion.VERSION2)
    self.mqttc.username_pw_set(username=settings.MQTT_USERNAME,
                               password=settings.MQTT_PASSWORD)
    if settings.MQTT_TLS:
        self.mqttc.tls_set()
    self.mqttc.connect(host=settings.MQTT_BROKER_URL.host,
                       port=settings.MQTT_BROKER_URL.port)

    # Device list
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

    yield  # Teardown code can go after this if needed

    # Teardown code
    clear_all(cb_client=self.cb_client,
              iota_client=self.iotc)
    self.iotc.close()
    self.cb_client.close()


@pytest.mark.usefixtures("setup_clients")
class TestDataModel:

    def test_data_model_provision(self, standard_setup):
        # 1. Load devices from an Excel table (implementation needed)
        pass

        # 2. Provisioning
        for device_item in self.devices_list:
            _uid = device_item["ID"]
            device_type = device_item["sensor_type"]
            # Create entity
            with open(os.path.join(path_input, "entity_templates",
                                   device_type + ".json")) as f:
                entity_template: dict = json.load(f)
                entity_template['id'] = f"{entity_template['type']}:{_uid}"
                entity = ContextEntity(**entity_template)
                with self.cb_client:
                    self.cb_client.post_entity(entity)
                    # time.sleep(0.5)
                    entity_fiware = self.cb_client.get_entity(entity_id=entity.id)
                    assert entity_fiware.id == entity_template.get('id')

            # Create device
            with open(os.path.join(path_input, "device_templates",
                                   device_type + ".json")) as f:
                device_template: dict = json.load(f)
                device_template['device_id'] = _uid
                device_template['entity_name'] = f"{entity_template['type']}:{_uid}"
                device = Device(**device_template)
                # Test the connection
                with self.iotc:
                    self.iotc.post_device(device=device)
                    device_fiware = self.iotc.get_device(device_id=device.device_id)
                    assert device_fiware.device_id == device_template.get('device_id')

        # 3. Validate provisioning
        for device in self.iotc.get_device_list():
            entity = self.cb_client.get_entity(entity_id=device.entity_name)
            for attr in device.attributes:
                entity_attr = entity.get_attribute(attr.name)
                assert entity_attr.type == attr.type

    @pytest.mark.order(1)
    def test_existing_attribute(self, standard_setup):
        """
        Existing attributes.
        """
        existing_attribute = "attribute1"
        topic = f"/json/{standard_service_group['apikey']}/{standard_device['device_id']}/attrs"
        new_value = 11
        self.mqttc.publish(topic=topic, payload=json.dumps({existing_attribute: new_value}))
        time.sleep(0.5)
        value = self.cb_client.get_attribute_value(
            entity_id=standard_entity["id"],
            entity_type=standard_entity["type"],
            attr_name=existing_attribute
        )
        assert value == new_value

    @pytest.mark.order(2)
    def test_append_attribute(self, standard_setup):
        """
        New attributes are appended.
        """
        # Append attributes in CB
        new_attribute_name = "attribute5"
        self.cb_client.update_or_append_entity_attributes(
            entity_id=standard_entity["id"],
            entity_type=standard_entity["type"],
            attrs=[
                NamedContextAttribute(**{
                    "name": new_attribute_name,
                    "type": "Number",
                    "value": 5})],
            append_strict=True)
        # Test sending and fetching; should fail initially
        topic = f"/json/{standard_service_group['apikey']}/{standard_device['device_id']}/attrs"
        new_value = 55
        self.mqttc.publish(topic=topic, payload=json.dumps({new_attribute_name: new_value}))
        time.sleep(0.5)
        value = self.cb_client.get_attribute_value(
            entity_id=standard_entity["id"],
            entity_type=standard_entity["type"],
            attr_name=new_attribute_name
        )
        assert value != new_value

        # Append attribute in IoTAgent
        device = self.iotc.get_device(device_id=standard_device["device_id"])
        device.add_attribute(attribute=DeviceAttribute(
            name=new_attribute_name,
            type="Number",
            object_id=new_attribute_name
        ))
        self.iotc.update_device(device=device)
        time.sleep(0.5)

        # Test sending again; should work now
        self.mqttc.publish(topic=topic, payload=json.dumps({new_attribute_name: new_value}))
        time.sleep(0.5)
        value = self.cb_client.get_attribute_value(
            entity_id=standard_entity["id"],
            entity_type=standard_entity["type"],
            attr_name=new_attribute_name
        )
        assert value == new_value

    @pytest.mark.order(3)
    def test_delete_attribute(self, standard_setup):
        """
        Attributes are deleted.
        """
        # Delete attribute in IoTAgent
        attribute_name_to_delete = "attribute3"
        device = self.iotc.get_device(device_id=standard_device["device_id"])
        device.delete_attribute(device.get_attribute(attribute_name_to_delete))
        self.iotc.update_device(device=device)
        time.sleep(0.5)

        # Test sending; should fail
        topic = f"/json/{standard_service_group['apikey']}/{standard_device['device_id']}/attrs"
        deleted_value = 42
        self.mqttc.publish(topic=topic,
                           payload=json.dumps({attribute_name_to_delete: deleted_value}))
        time.sleep(0.5)
        value = self.cb_client.get_attribute_value(
            entity_id=standard_entity["id"],
            entity_type=standard_entity["type"],
            attr_name=attribute_name_to_delete
        )
        assert value != deleted_value

        # Attribute should still exist in CB
        entity_attr = self.cb_client.get_attribute(
            entity_id=standard_entity["id"],
            entity_type=standard_entity["type"],
            attr_name=attribute_name_to_delete
        )
        assert entity_attr is not None

        # Delete attribute in CB
        self.cb_client.delete_entity_attribute(
            entity_id=standard_entity["id"],
            entity_type=standard_entity["type"],
            attr_name=attribute_name_to_delete
        )

        # Attribute should no longer exist
        attrs = self.cb_client.get_entity_attributes(
            entity_id=standard_entity["id"],
            entity_type=standard_entity["type"],
            attrs=[attribute_name_to_delete]
        )
        assert attrs == {}

    @pytest.mark.order(4)
    def test_rename_attribute(self, standard_setup):
        """
        Attributes are renamed.
        """
        # Rename attribute in CB
        old_attribute_name = "attribute4"
        new_attribute_name = "new_attribute"
        self.cb_client.update_or_append_entity_attributes(
            entity_id=standard_entity["id"],
            entity_type=standard_entity["type"],
            attrs=[
                NamedContextAttribute(**{
                    "name": new_attribute_name,
                    "type": "Number",
                    "value": 0})],
            append_strict=True)
        time.sleep(0.5)

        # Test sending and fetching with new name; should fail initially
        topic = f"/json/{standard_service_group['apikey']}/{standard_device['device_id']}/attrs"
        value_to_send = 44
        self.mqttc.publish(topic=topic,
                           payload=json.dumps({new_attribute_name: value_to_send}))
        time.sleep(0.5)
        value = self.cb_client.get_attribute_value(
            entity_id=standard_entity["id"],
            entity_type=standard_entity["type"],
            attr_name=new_attribute_name
        )
        assert value != value_to_send

        # Update attribute name in IoTAgent
        device = self.iotc.get_device(device_id=standard_device["device_id"])
        device_attribute = device.get_attribute(old_attribute_name)
        device_attribute.name = new_attribute_name
        device.update_attribute(device_attribute)
        self.iotc.update_device(device=device)
        time.sleep(0.5)

        # Test sending and fetching again; should work now
        self.mqttc.publish(topic=topic,
                           payload=json.dumps({new_attribute_name: value_to_send}))
        time.sleep(0.5)
        value = self.cb_client.get_attribute_value(
            entity_id=standard_entity["id"],
            entity_type=standard_entity["type"],
            attr_name=new_attribute_name
        )
        assert value == value_to_send

    @pytest.mark.order(5)
    def test_anonymous_update(self, standard_setup):
        """
        Anonymous attributes getting updated.
        """
        # Test sending anonymous attributes; should fail
        anonymous_device = deepcopy(standard_device)
        anonymous_device["device_id"] = "anonymous_device"
        anonymous_device["explicitAttrs"] = False
        self.iotc.post_device(device=Device(**anonymous_device))
        topic = f"/json/{standard_service_group['apikey']}/{anonymous_device['device_id']}/attrs"
        anonymous_attribute = "anonymous_attribute"
        anonymous_value = 77

        with pytest.raises(HTTPError):
            self.cb_client.get_attribute_value(
                entity_id=standard_entity["id"],
                entity_type=standard_entity["type"],
                attr_name=anonymous_attribute)

        # Append new attribute in CB
        self.cb_client.update_or_append_entity_attributes(
            entity_id=standard_entity["id"],
            entity_type=standard_entity["type"],
            attrs=[
                NamedContextAttribute(**{
                    "name": anonymous_attribute,
                    "type": "Number",
                    "value": 0})],
            append_strict=True)
        time.sleep(0.5)

        # Test sending and fetching again; should work now
        self.mqttc.publish(topic=topic,
                           payload=json.dumps({anonymous_attribute: anonymous_value}))
        time.sleep(0.5)
        value = self.cb_client.get_attribute_value(
            entity_id=standard_entity["id"],
            entity_type=standard_entity["type"],
            attr_name=anonymous_attribute
        )
        assert value == anonymous_value