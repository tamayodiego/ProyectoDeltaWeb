# infra/

Infraestructura del proyecto. Por ahora está vacía; se llena en estas fases del roadmap:

| Carpeta (futura) | Contenido | Fase |
|---|---|---|
| `ansible/` | Provisionamiento y seguridad del VPS | 5 |
| `k8s/` | Manifiestos base del clúster k3s (namespaces, cert-manager, CloudNativePG) | 5 |
| `helm/` | Chart de la aplicación y `values-dev.yaml` / `values-prod.yaml` | 6 |
| `monitoring/` | Prometheus y Grafana | 7 |

El `docker-compose.yml` para desarrollo local vive en la raíz del repo.
