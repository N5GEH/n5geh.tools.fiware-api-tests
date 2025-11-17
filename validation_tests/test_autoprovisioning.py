import json
import time
import unittest
import requests
from filip.models.ngsi_v2 import ContextEntity

from paho.mqtt.client import Client, CallbackAPIVersion
from filip.clients.ngsi_v2 import ContextBrokerClient, IoTAClient
from filip.models import FiwareHeader
from filip.models.ngsi_v2.iot import ServiceGroup, DeviceAttribute, Device
from filip.utils.cleanup import clear_all

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

        self.mqttc = Client(callback_api_version=CallbackAPIVersion.VERSION2)
        self.mqttc.username_pw_set(username=settings.MQTT_USERNAME,
                                   password=settings.MQTT_PASSWORD)
        if settings.MQTT_TLS:
            self.mqttc.tls_set()
        self.mqttc.connect(host=settings.MQTT_BROKER_URL.host,
                           port=settings.MQTT_BROKER_URL.port)

        # TODO: clean up

        # clear_all(fiware_header=self.fiware_header,
        #           cb_url=settings.CB_URL,
        #           iota_url=settings.IOTA_JSON_URL,
        #           ql_url=settings.QL_URL,)

        # TODO: Create service group



    def test_autoprovision(self):

        # TODO: Send data for a non existing device
        # TODO: Check if device is created
        # TODO: Check if entity is created
        # TODO: Check if entity holds the right data
        pass

    def test_cross_group_operation_with_autoprov(self):
        # create 3 service groups, each with a device?
        # group 1
        attr1 = DeviceAttribute(
            name="attribute1",
            type="Number",
            object_id="a1"
        )
        device1_id = "Device:001"
        sg1 = ServiceGroup(
            resource="/iot/json",
            apikey="fiware-api-1",
            autoprovision=True,
            explicitAttrs=False,
            entity_type="Type1",
            attributes=[attr1]
        )

        # group 2
        attr2 = DeviceAttribute(
            name="attribute2",
            type="Number",
            object_id="a2"
        )
        device2_id = "Device:002"
        sg2 = ServiceGroup(
            resource="/iot/json",
            apikey="fiware-api-2",
            autoprovision=True,
            explicitAttrs=False,
            entity_type="Type2",
            attributes=[attr2]
        )
        # create device 2
        self.iotc.post_device(
            device=Device(**{
            "device_id": device2_id,
            "entity_name": "Entity:002",
            "entity_type": "Type2",
            "transport": "MQTT",
            "attributes": [attr2]
        }))

        # group 3
        attr3 = DeviceAttribute(
            name="attribute3",
            type="Number",
            object_id="a3"
        )
        device3_id = "Device:003"
        sg3 = ServiceGroup(
            resource="/iot/json",
            apikey="fiware-api-3",
            entity_type="Type3",
            autoprovision=True,
            explicitAttrs=False,
            attributes=[attr3]
        )

        # create service groups in IoT Agent
        self.iotc.post_groups([sg1, sg2, sg3])

        # update device 1 with group 2 credentials. and 2 -> 3, 3 -> 1
        for device, attr, sg in zip([device1_id, device2_id, device3_id], [attr1, attr2, attr3], [sg2, sg3, sg1]):
        # for device, attr, sg in zip([device1_id, device2_id, device3_id], [attr1, attr2, attr3], [sg1, sg2, sg3]):
            iot_topic = f"/json/{sg.apikey}/{device}/attrs"
            self.mqttc.publish(
                topic=iot_topic,
                payload=json.dumps({
                    attr.object_id: 10
                })
            )

        # verify the results
        time.sleep(2)
        devices = self.iotc.get_device_list()
        entities = self.cb_client.get_entity_list()
        for entity in entities:
            if entity.id == "Entity:002":  # attribute update will work with not matching service group if device exists
                self.assertIn('"value":10.0', entity.model_dump_json())
            else:  # Attribute update will not work with not matching service group
                self.assertNotIn('"value":10.0', entity.model_dump_json())

        # update new device 1 with correct group credentials  -> works
        device1_id_new = "Device:001:NEW"
        iot_topic = f"/json/{sg1.apikey}/{device1_id_new}/attrs"
        self.mqttc.publish(
            topic=iot_topic,
            payload=json.dumps({
                attr1.object_id: 15
            })
        )
        # verify the results
        time.sleep(2)
        entity_1_new = self.cb_client.get_entity_list(id_pattern=device1_id_new)[0]
        self.assertIn('"value":15', entity_1_new.model_dump_json())

    def test_cross_group_operation_without_autoprov(self):
        """
        Results:
        - Device update with "wrong" API key, will not affect the settings in the service group. The settings of the
            used service group will be applied.
        - If autoprovision is disabled (false), initial message will not create a new entity/device
        - If explicitAttrs is disabled (false), attributes not defined in the service group or device will not be
            created. But if the entity/device already exists, updates to those attributes will still work.
        """
        # test with without autoprovision
        attr4 = DeviceAttribute(
                    name="attribute4",
                    type="Number",
                    object_id="a4"
                )
        sg4 = ServiceGroup(
            resource="/iot/json",
            apikey="fiware-api-4",
            entity_type="Type4",
            autoprovision=True,
            explicitAttrs=False,
            attributes=[attr4]
        )
        self.iotc.post_groups([sg4])

        attr5 = DeviceAttribute(
                    name="attribute5",
                    type="Number",
                    object_id="a5"
                )
        sg5 = ServiceGroup(
            resource="/iot/json",
            apikey="fiware-api-5",
            entity_type="Type5",
            autoprovision=False,
            explicitAttrs=False,
            attributes=[attr5]
        )
        self.iotc.post_groups([sg5])

        # update device with wrong group credentials
        device_4_id = "Device:004"
        iot_topic = f"/json/{sg5.apikey}/{device_4_id}/attrs"
        self.mqttc.publish(
            topic=iot_topic,
            payload=json.dumps({
                attr4.object_id: 20
            })
        )
        # verify the results
        time.sleep(2)
        entity_4 = self.cb_client.get_entity_list(id_pattern=device_4_id)
        self.assertEqual(len(entity_4), 0)
        # self.assertIn('"value":20.0', entity_4[0].model_dump_json())

        device_5_id = "Device:005"
        iot_topic = f"/json/{sg4.apikey}/{device_5_id}/attrs"
        self.mqttc.publish(
            topic=iot_topic,
            payload=json.dumps({
                attr5.object_id: 25
            })
        )
        # verify the results
        time.sleep(2)
        entities_5 = self.cb_client.get_entity_list(id_pattern=device_5_id)
        self.assertEqual(len(entities_5), 1)
        self.assertNotIn('"value":25.0', entities_5[0].model_dump_json())

        # test with provisioned entity
        device_6_id = "Device:006"
        attr6 = DeviceAttribute(
                    name="attribute6",
                    type="Number"
                )
        entity_6 = ContextEntity(
            id=device_6_id,
            type="Type6",
            attribute6={"type": "Number", "value": 0}
        )
        self.cb_client.post_entity(entity_6)
        device_6 = Device(
            device_id=device_6_id,
            entity_name=device_6_id,
            entity_type="Type6",
            transport="MQTT",
            explicitAttrs=False
        )
        self.iotc.post_device(device=device_6)
        iot_topic = f"/json/{sg4.apikey}/{device_6_id}/attrs"
        self.mqttc.publish(
            topic=iot_topic,
            payload=json.dumps({
                attr6.name: 30
            })
        )
        # verify the results
        time.sleep(2)
        entity_6_updated = self.cb_client.get_entity(entity_id=device_6_id)
        self.assertIn('"value":30', entity_6_updated.model_dump_json())

    def test_different_transport(self):
        # HTTP-Transport service group and device
        attr_http = DeviceAttribute(
            name="attribute_http",
            type="Number",
            object_id="h1"
        )
        sg_http = ServiceGroup(
            resource="/iot/json",
            apikey="fiware-api-http",
            autoprovision=True,
            explicitAttrs=True,
            entity_type="TypeHTTP",
            attributes=[attr_http]
        )
        device_http_id = "Device:HTTP:001"
        device_http = Device(
            device_id=device_http_id,
            entity_name="Entity:HTTP:001",
            entity_type="TypeHTTP",
            transport="HTTP",
            explicitAttrs=True,
            attributes=[attr_http]
        )

        # MQTT-Transport service group and device
        attr_mqtt = DeviceAttribute(
            name="attribute_mqtt",
            type="Number",
            object_id="m1"
        )
        sg_mqtt = ServiceGroup(
            resource="/iot/json",
            apikey="fiware-api-mqtt",
            autoprovision=True,
            explicitAttrs=True,
            entity_type="TypeMQTT",
            attributes=[attr_mqtt]
        )
        device_mqtt_id = "Device:MQTT:001"
        device_mqtt = Device(
            device_id=device_mqtt_id,
            entity_name="Entity:MQTT:001",
            entity_type="TypeMQTT",
            transport="MQTT",
            explicitAttrs=True,
            attributes=[attr_mqtt]
        )

        # post service groups and devices
        self.iotc.post_groups([sg_http, sg_mqtt])
        self.iotc.post_device(device=device_http)
        self.iotc.post_device(device=device_mqtt)

        # Update MQTT device via MQTT
        iot_topic_mqtt = f"/json/{sg_mqtt.apikey}/{device_mqtt_id}/attrs"
        self.mqttc.publish(
            topic=iot_topic_mqtt,
            payload=json.dumps({attr_mqtt.object_id: 42})
        )
        time.sleep(2)
        entity_mqtt = self.cb_client.get_entity(entity_id="Entity:MQTT:001")
        self.assertIn('"value":42', entity_mqtt.model_dump_json())

        # HTTP-Device update via MQTT - should NOT work
        iot_topic_http = f"/json/{sg_http.apikey}/{device_http_id}/attrs"
        self.mqttc.publish(
            topic=iot_topic_http,
            payload=json.dumps({attr_http.object_id: 99})
        )
        time.sleep(2)
        entity_http = self.cb_client.get_entity(entity_id="Entity:HTTP:001")
        # The communication should be blocked. But seems like IoT Agent allow cross-transport updates
        self.assertIn('"value":99', entity_http.model_dump_json())

        # HTTP-Device update via HTTP
        url = f"{settings.IOTA_JSON_HTTP_URL}/iot/json"
        query_params = {
            "i": device_http_id,
            "k": sg_http.apikey
        }
        payload = {
            attr_http.object_id: 77
        }
        headers = {"Content-Type": "application/json"}
        requests.post(url, data=json.dumps(payload), headers=headers, params=query_params)
        time.sleep(2)
        entity_http = self.cb_client.get_entity(entity_id="Entity:HTTP:001")
        self.assertIn('"value":77', entity_http.model_dump_json())

        # Update MQTT device via HTTP - should NOT work
        requests.post(url, data=json.dumps({attr_mqtt.object_id: 88}),
                      headers={"Content-Type": "application/json"},
                      params={
                            "i": device_mqtt_id,
                            "k": sg_mqtt.apikey
                        })
        time.sleep(2)
        entity_mqtt = self.cb_client.get_entity(entity_id="Entity:MQTT:001")
        # The communication should be blocked. But seems like IoT Agent allow cross-transport updates
        self.assertIn('"value":88', entity_mqtt.model_dump_json())

    def tearDown(self) -> None:
        self.fiware_header = FiwareHeader(service=settings.FIWARE_SERVICE)
        clear_all(cb_client=self.cb_client,
                  iota_client=self.iotc)
        self.iotc.close()
        self.cb_client.close()


if __name__ == "__main__":
    unittest.main()
