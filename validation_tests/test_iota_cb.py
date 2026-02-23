import pytest
import json
import time
import requests
from filip.models.ngsi_v2.context import ContextEntity
from paho.mqtt.client import Client, CallbackAPIVersion
from filip.clients.ngsi_v2 import ContextBrokerClient, IoTAClient
from filip.models import FiwareHeader
from filip.models.ngsi_v2.iot import ServiceGroup, DeviceAttribute, Device
from filip.utils.cleanup import clear_all
from settings import settings


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


@pytest.fixture(autouse=True)
def setup_clients():
    fiware_header = FiwareHeader(
        service=settings.FIWARE_SERVICE,
        service_path=settings.FIWARE_SERVICEPATH,
    )
    cb_client = ContextBrokerClient(url=settings.CB_URL, fiware_header=fiware_header)
    iotc = IoTAClient(url=settings.IOTA_JSON_URL, fiware_header=fiware_header)
    mqttc = Client(callback_api_version=CallbackAPIVersion.VERSION2)
    mqttc.username_pw_set(username=settings.MQTT_USERNAME, password=settings.MQTT_PASSWORD)
    if settings.MQTT_TLS:
        mqttc.tls_set()
    mqttc.connect(host=settings.MQTT_BROKER_URL.host, port=settings.MQTT_BROKER_URL.port)
    yield fiware_header, cb_client, iotc, mqttc
    clear_all(cb_client=cb_client, iota_client=iotc)
    iotc.close()
    cb_client.close()

@pytest.mark.order(1)
def test_autoprovision(setup_clients):
    fiware_header, cb_client, iotc, mqttc = setup_clients
    device1_id = "device1"
    entity_type = "Type1"
    attr1 = DeviceAttribute(
        name="attribute1",
        type="Number",
        object_id="a1"
    )
    service_group = ServiceGroup(
        resource="/iot/json",
        apikey="fiware-api-test",
        entity_type=entity_type,
        explicitAttrs=False,
        autoprovision=True,
        attributes=[attr1],
    )
    iotc.post_groups([service_group])
    devices = iotc.get_device_list()
    assert len(devices) == 0
    iot_topic = f"/json/{service_group.apikey}/{device1_id}/attrs"
    mqttc.publish(
        topic=iot_topic,
        payload=json.dumps({attr1.object_id: 15})
    )
    time.sleep(2)
    devices = iotc.get_device_list()
    assert len(devices) == 1
    assert devices[0].device_id == device1_id
    entities = cb_client.get_entity_list()
    assert len(entities) == 1
    assert entities[0].id == f"{entity_type}:{device1_id}"
    assert entities[0].get_attribute(attr1.name).value == 15.0

@pytest.mark.order(2)
def test_cross_group_operation_with_autoprov(setup_clients):
    fiware_header, cb_client, iotc, mqttc = setup_clients
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
    iotc.post_device(
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
    # post service groups in IoT Agent
    iotc.post_groups([sg1, sg2, sg3])

    # update device 1 with group 2 credentials. and 2 -> 3, 3 -> 1
    for device, attr, sg in zip([device1_id, device2_id, device3_id], [attr1, attr2, attr3], [sg2, sg3, sg1]):
        iot_topic = f"/json/{sg.apikey}/{device}/attrs"
        mqttc.publish(
            topic=iot_topic,
            payload=json.dumps({attr.object_id: 10})
        )

    # verify the results
    time.sleep(2)
    devices = iotc.get_device_list()
    entities = cb_client.get_entity_list()
    for entity in entities:
        if entity.id == "Entity:002":
            assert '"value":10.0' in entity.model_dump_json()
        else:
            assert '"value":10.0' not in entity.model_dump_json()
    device1_id_new = "Device:001:NEW"
    iot_topic = f"/json/{sg1.apikey}/{device1_id_new}/attrs"
    mqttc.publish(
        topic=iot_topic,
        payload=json.dumps({attr1.object_id: 15})
    )
    time.sleep(2)
    entity_1_new = cb_client.get_entity_list(id_pattern=device1_id_new)[0]
    assert '"value":15' in entity_1_new.model_dump_json()

@pytest.mark.order(3)
def test_cross_group_operation_without_autoprov(setup_clients):
    """
    Results:
    - Device update with "wrong" API key, will not affect the settings in the service group. The settings of the
        used service group will be applied.
    - If autoprovision is disabled (false), initial message will not create a new entity/device
    - If explicitAttrs is disabled (false), attributes not defined in the service group or device will not be
        created. But if the entity/device already exists, updates to those attributes will still work.
    """
    fiware_header, cb_client, iotc, mqttc = setup_clients
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
    iotc.post_groups([sg4])
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
    iotc.post_groups([sg5])
    device_4_id = "Device:004"
    iot_topic = f"/json/{sg5.apikey}/{device_4_id}/attrs"
    mqttc.publish(
        topic=iot_topic,
        payload=json.dumps({attr4.object_id: 20})
    )
    time.sleep(2)
    entity_4 = cb_client.get_entity_list(id_pattern=device_4_id)
    assert len(entity_4) == 0
    device_5_id = "Device:005"
    iot_topic = f"/json/{sg4.apikey}/{device_5_id}/attrs"
    mqttc.publish(
        topic=iot_topic,
        payload=json.dumps({attr5.object_id: 25})
    )
    time.sleep(2)
    entities_5 = cb_client.get_entity_list(id_pattern=device_5_id)
    assert len(entities_5) == 1
    assert '"value":25.0' not in entities_5[0].model_dump_json()
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
    cb_client.post_entity(entity_6)
    device_6 = Device(
        device_id=device_6_id,
        entity_name=device_6_id,
        entity_type="Type6",
        transport="MQTT",
        explicitAttrs=False
    )
    iotc.post_device(device=device_6)
    iot_topic = f"/json/{sg4.apikey}/{device_6_id}/attrs"
    mqttc.publish(
        topic=iot_topic,
        payload=json.dumps({attr6.name: 30})
    )
    # verify the results
    time.sleep(2)
    entity_6_updated = cb_client.get_entity(entity_id=device_6_id)
    assert '"value":30' in entity_6_updated.model_dump_json()

@pytest.mark.order(4)
def test_different_transport(setup_clients):
    fiware_header, cb_client, iotc, mqttc = setup_clients
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
    # post service groups and device
    iotc.post_groups([sg_http, sg_mqtt])
    iotc.post_device(device=device_http)
    iotc.post_device(device=device_mqtt)
    # Update MQTT device via MQTT
    iot_topic_mqtt = f"/json/{sg_mqtt.apikey}/{device_mqtt_id}/attrs"
    mqttc.publish(
        topic=iot_topic_mqtt,
        payload=json.dumps({attr_mqtt.object_id: 42})
    )
    time.sleep(2)
    entity_mqtt = cb_client.get_entity(entity_id="Entity:MQTT:001")
    assert '"value":42' in entity_mqtt.model_dump_json()
    iot_topic_http = f"/json/{sg_http.apikey}/{device_http_id}/attrs"
    mqttc.publish(
        topic=iot_topic_http,
        payload=json.dumps({attr_http.object_id: 99})
    )
    time.sleep(2)
    entity_http = cb_client.get_entity(entity_id="Entity:HTTP:001")
    # The communication should be blocked. But seems like IoT Agent allow cross-transport updates
    assert '"value":99' in entity_http.model_dump_json()
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
    entity_http = cb_client.get_entity(entity_id="Entity:HTTP:001")
    assert '"value":77' in entity_http.model_dump_json()
    # Update MQTT device via HTTP - should NOT work
    requests.post(url, data=json.dumps({attr_mqtt.object_id: 88}), headers={"Content-Type": "application/json"}, params={"i": device_mqtt_id, "k": sg_mqtt.apikey})
    time.sleep(2)
    entity_mqtt = cb_client.get_entity(entity_id="Entity:MQTT:001")
    # The communication should be blocked. But seems like IoT Agent allow cross-transport updates
    assert '"value":88' in entity_mqtt.model_dump_json()
