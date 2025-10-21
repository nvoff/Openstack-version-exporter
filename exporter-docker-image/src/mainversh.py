import re
import time
import logging
from kubernetes import client, config
from kubernetes.stream import stream
from prometheus_client import Gauge, start_http_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NAMESPACE = "os"
POD_COMMANDS = {
    "cinder-api": {"command": "cinder-api --version"},
    "cinder-scheduler": {"command": "cinder-scheduler --version"},
    "cinder-volume": {"command": "cinder-volume --version"},
    "client": {"command": "openstack --version"},
    "glance": {"command": "glance-api --version"},
    "haproxy": {"command": "haproxy -v"},
    "heat-api": {"command": "heat-api --version"},
    "heat-cfn": {"command": "heat-api-cfn --version"},
    "heat-engine": {"command": "heat-engine --version"},
    "horizon": {"command": "pip show horizon"},
    "keystone": {"command": "keystone-manage --version"},
    "memcached": {"command": "memcached --version"},
    "neutron-metadata": {"command": "neutron-metadata-agent --version"},
    "neutron-server": {"command": "neutron-server --version"},
    "nova-api": {"command": "nova-api --version"},
    "nova-compute": {"command": "nova-compute --version"},
    "nova-conductor": {"command": "nova-conductor --version"},
    "nova-novncproxy": {"command": "nova-novncproxy --version"},
    "nova-scheduler": {"command": "nova-scheduler --version"},
    "placement": {"command": "placement-manage --version"},
    "rabbitmq-server": {"command": "rabbitmqctl version"},
    "skyline": {"command": "pip show skyline-apiserver"},
}

version_info = Gauge(
    'pod_version_info',
    'Version information of Kubernetes pods',
    ['pod_name', 'component', 'version']
)

def get_pod_name(v1, namespace, pod_prefix):
    pods = v1.list_namespaced_pod(namespace=namespace)
    pattern = re.compile(f"^{pod_prefix}.*")
    for pod in pods.items:
        if pattern.match(pod.metadata.name):
            return pod.metadata.name
    return None

def get_first_container_name(v1, namespace, pod_name):
    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        containers = pod.spec.containers
        return containers[0].name if containers else None
    except Exception as e:
        logger.error(f"Ошибка получения контейнера из пода {pod_name}: {e}")
        return None

def exec_command(v1, namespace, pod_name, command, container):
    try:
        exec_command = ["sh", "-c", command]
        resp = stream(v1.connect_get_namespaced_pod_exec, pod_name, namespace,
                      container=container, command=exec_command,
                      stderr=True, stdin=False, stdout=True, tty=False)
        return resp
    except Exception as e:
        logger.error(f"Ошибка выполнения команды в поде {pod_name}: {e}")
        return None

def parse_version(output):
    if not output:
        return "unknown"
    match = re.search(r'\d+\.\d+\.\d+', output)
    return match.group(0) if match else "unknown"

def collect_versions():
    try:
        v1 = client.CoreV1Api()

        version_info._metrics.clear()

        for component, cmd_cfg in POD_COMMANDS.items():
            pod_name = get_pod_name(v1, NAMESPACE, component)

            if not pod_name:
                logger.warning(f"Под не найден: {component}")
                version_info.labels(pod_name="unknown", component=component, version="unknown").set(0)
                continue

            container = get_first_container_name(v1, NAMESPACE, pod_name)
            if not container:
                logger.warning(f"Контейнер не найден в поде {pod_name}")
                version_info.labels(pod_name=pod_name, component=component, version="unknown").set(0)
                continue

            output = exec_command(v1, NAMESPACE, pod_name, cmd_cfg["command"], container)
            version = parse_version(output)
            logger.info(f"{component} версия компонента: {version}")
            version_info.labels(pod_name=pod_name, component=component, version=version).set(1)

    except Exception as e:
        logger.error(f"Ошибка сбора версий: {e}")

def main():
    try:
        config.load_incluster_config()
        logger.info("Kubernetes API client initialized using RBAC")
    except config.ConfigException as e:
        logger.error(f"Ошибка инициализации Kubernetes клиента: {e}")
        return

    start_http_server(8000)
    logger.info("Prometheus metrics server started on port 8000")

    while True:
        collect_versions()
        time.sleep(43200)

if __name__ == "__main__":
    main()
