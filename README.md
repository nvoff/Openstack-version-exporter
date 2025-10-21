# Components Version Exporter / Экспортер версий компонентов

Lightweight Kubernetes exporter that collects version information from OpenStack-related pods and exposes it as Prometheus metrics.

Легковесный Kubernetes-экспортер, который собирает информацию о версиях из подов, связанных с OpenStack, и экспортирует её в формате метрик Prometheus.

This repository contains a small Python-based exporter packaged into a Docker image and Kubernetes manifests to run it in-cluster.

В этом репозитории находится небольшой Python-экспортер, упакованный в Docker-образ, а также манифесты Kubernetes для запуска внутри кластера.

## Repository layout / Структура репозитория

- `exporter-docker-image/` - Docker image source and Python code / исходники образа и Python-код
  - `Dockerfile` - image build instructions / инструкция сборки образа
  - `requirements.txt` - runtime Python dependencies / runtime-зависимости
  - `requirements-dev.txt` - development / test dependencies / dev-зависимости
  - `src/` - Python source code / исходники
    - `mainversh.py` - main exporter script / основной скрипт экспортера
- `exporter-k8s/` - Kubernetes manifests / манифесты для Kubernetes
  - `deployment.yaml` - Deployment manifest / Deployment
  - `service.yaml` - Service manifest for exposing metrics / Service
  - `role.yaml` - ServiceAccount and RBAC rules required for in-cluster access / ServiceAccount и RBAC
  - `kustomization.yaml` - Kustomize entrypoint / точка входа для kustomize

## What it does / Что делает

The exporter locates pods in the `os` namespace matching a set of component name prefixes (configured in `mainversh.py`), executes version commands inside those pods (using the Kubernetes exec API), parses semantic versions from the output, and exposes them as Prometheus metrics on port `8000`.

Экспортер находит поды в неймспейсе `os`, имена которых начинаются с определённых префиксов (настраивается в `mainversh.py`), выполняет команды внутри этих подов (через Kubernetes exec API), парсит семантические версии из вывода и экспортирует их как метрики Prometheus на порту `8000`.

Metric produced / Производимая метрика:

- `pod_version_info{pod_name="...", component="...", version="..."}` with value `1` when a component version was collected, or `0` when unknown/missing.

- `pod_version_info{pod_name="...", component="...", version="..."}` со значением `1` когда версия компонента получена, или `0` когда неизвестна/не найдена.

The exporter runs as a non-root user inside the container and is intended to be deployed inside the Kubernetes cluster it queries.

Экспортер запускается в контейнере не от root-пользователя и предназначен для разворачивания внутри кластера Kubernetes, к которому он обращается.

## Build Docker image / Сборка Docker-образа

From the repository root, build the image (replace `your-registry` with your image name):

Из корня репозитория соберите образ (замените `your-registry` на имя вашего образа):

```bash
cd exporter-docker-image
docker build -t your-registry/components-version-exporter:latest .
```

Push the image to your registry if you plan to use it in a cluster:

Запушьте образ в регистр, если планируете запуск в кластере:

```bash
docker push your-registry/components-version-exporter:latest
```

Note: The `Dockerfile` uses a non-root user (UID 1000) and adds the application to `/app`. The container command runs `python /app/src/mainversh.py`.

Примечание: `Dockerfile` использует не-root пользователя (UID 1000) и помещает приложение в `/app`. Команда контейнера запускает `python /app/src/mainversh.py`.

## Deploy to Kubernetes / Разворачивание в Kubernetes

Edit `exporter-k8s/deployment.yaml` and replace the `image: your-registry` placeholder with your built image reference (for example `your-registry/components-version-exporter:latest`).

Отредактируйте `exporter-k8s/deployment.yaml` и замените `image: your-registry` на ссылку на ваш собранный образ (например `your-registry/components-version-exporter:latest`).

Then apply manifests with kubectl (ensure you have access to the cluster and the `os` namespace exists):

Затем примените манифесты (убедитесь, что у вас есть доступ к кластеру и неймспейс `os` создан):

```bash
kubectl apply -k exporter-k8s/
```

What the manifests do / Что делают манифесты:

- `role.yaml` creates a `ServiceAccount` named `version-exporter`, a `Role` that allows listing/getting/watching pods and creating exec sessions, and a `RoleBinding` to bind that role to the ServiceAccount.
- `role.yaml` создаёт `ServiceAccount` с именем `version-exporter`, `Role`, который позволяет получать/листать/наблюдать поды и создавать exec-сессии, и `RoleBinding`, который связывает роль с ServiceAccount.
- `deployment.yaml` creates a Deployment that mounts an emptyDir at `/tmp`, runs the exporter as UID 1000 with a read-only root filesystem, and exposes container port 8000.
- `deployment.yaml` создаёт Deployment, монтирует `emptyDir` в `/tmp`, запускает экспортер под UID 1000 с `readOnlyRootFilesystem: true` и открывает порт 8000.
- `service.yaml` exposes the pod on port 8000 within the cluster.
- `service.yaml` создаёт Service, который открывает порт 8000 внутри кластера.

## Configuration / Конфигурация

The exporter is configured inside `src/mainversh.py`:

Экспортер конфигурируется в `src/mainversh.py`:

- `NAMESPACE` - namespace to look for component pods (default `os`).
- `NAMESPACE` - неймспейс для поиска подов компонентов (по умолчанию `os`).
- `POD_COMMANDS` - dictionary mapping pod name prefixes (used to find pods) to commands executed inside the found pod to extract a version string.
- `POD_COMMANDS` - словарь, сопоставляющий префиксы имён подов (используются для поиска) с командами, выполняемыми внутри пода для получения строки версии.

Adjust these values or extend `POD_COMMANDS` for additional components as needed.

Изменяйте эти значения или расширяйте `POD_COMMANDS` для добавления новых компонентов.

## Development and testing / Разработка и тестирование

- Install dev dependencies locally (optional):
- Установка dev-зависимостей локально (опционально):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r exporter-docker-image/requirements-dev.txt
```

- Run the exporter locally against a kubeconfig (the script currently only attempts in-cluster config). To run outside the cluster you can modify `mainversh.py` to call `config.load_kube_config()` when needed.
- Запуск локально против kubeconfig: по умолчанию скрипт пытается только in-cluster конфигурацию. Для запуска вне кластера добавьте `config.load_kube_config()` в `mainversh.py`.

- Unit tests are not included by default; consider adding pytest tests for parsing logic (`parse_version`) and for functions that can be executed without a cluster.
- Юнит-тесты не включены по умолчанию; рекомендуется добавить pytest-тесты для логики парсинга (`parse_version`) и для функций, которые можно запускать без кластера.

## Security notes / Замечания по безопасности

- The exporter uses the `exec` API to run commands inside other pods. Limit which ServiceAccount/Role can use this exporter and follow the principle of least privilege.
- Экспортер использует API `exec` для запуска команд внутри других подов. Ограничьте ServiceAccount/Role, которые получают такие полномочия, и следуйте принципу наименьших привилегий.
- The Deployment sets `readOnlyRootFilesystem: true` and runs as a non-root user. Keep container images minimal and scan them for vulnerabilities.
- Deployment использует `readOnlyRootFilesystem: true` и non-root пользователя. Держите образы минимальными и сканируйте их на уязвимости.

## Troubleshooting / Устранение проблем

- If metrics are blank or `unknown`, check logs of the exporter pod:
- Если метрики пусты или `unknown`, посмотрите логи экспортера:

```bash
kubectl -n os logs -l app=components-version-exporter
```

- Ensure the ServiceAccount has the RBAC permissions granted by `role.yaml` and that the target pods are in the `os` namespace and have names matching configured prefixes.
- Убедитесь, что ServiceAccount имеет RBAC-права из `role.yaml`, а целевые поды находятся в неймспейсе `os` и их имена соответствуют префиксам в конфигурации.

## Example changes you might make / Примеры изменений

- Add `config.load_kube_config()` fallback for local development.
- Добавить fallback `config.load_kube_config()` для локальной разработки.
- Add command timeouts and more robust output parsing for versions with different formats.
- Добавить таймауты команд и более надёжный парсинг вывода версий с разными форматами.
- Expose additional labels such as container name or image tag.
- Экспортировать дополнительные лейблы, например имя контейнера или тег образа.

