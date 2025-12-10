# Observability Stack with Grafana

Production-ready telemetry pipeline using OpenTelemetry, Prometheus, Loki, Tempo, and Grafana for metrics, logs, and traces.

## Stack

- **App**: Sample instrumented service (Python/FastAPI)
- **Collection**: OpenTelemetry Collector
- **Storage**: Prometheus (metrics), Loki (logs), Tempo (traces)
- **Visualization**: Grafana with pre-configured dashboards
- **Alerting**: Grafana Alerting → Slack

## Quick Start

```bash
# Start the stack
docker-compose up -d

# Access services
# Grafana: http://localhost:3000 (admin/admin)
# Sample App: http://localhost:8000
# Prometheus: http://localhost:9090

# View app logs
curl http://localhost:8000/logs

# Trigger some traffic
for i in {1..100}; do curl http://localhost:8000/api/users; done
```

## Structure

```
├── app/                    # Sample instrumented application
├── otel-collector/         # OpenTelemetry Collector config
├── prometheus/             # Prometheus config & alert rules
├── grafana/               # Dashboards & datasources
├── docker-compose.yml     # Full stack orchestration
└── requirements.txt       # Python dependencies
```

## Key Alerts Configured

- **HighErrorRate**: >5% errors for 10min
- **HighLatencyP95**: p95 >300ms for 15min
- **ServiceDown**: Probe failure >2min
- **HighLogErrors**: >5 ERROR logs/sec

## Kubernetes Deployment

```bash
# Apply manifests
kubectl apply -f k8s/

# Port-forward Grafana
kubectl port-forward svc/grafana 3000:3000 -n observability
```

## Customization

Edit `prometheus/alerts.yml` for alert rules and `grafana/provisioning/dashboards/app-dashboard.json` for dashboards.
