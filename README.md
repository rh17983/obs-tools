# OBS Tools

Build & Push

```bash
docker build -t docker.io/hedgefock/obs-tools-worker:latest ./worker
docker push docker.io/hedgefock/obs-tools-worker:latest
```

Deploy

```bash
kubectl apply -f ns.yaml 
kubectl apply -f rbac.yaml
kubectl apply -f pvc.yaml
kubectl apply -f cron-validate.yaml
kubectl apply -f obs-tools-links-configmap.yaml
kubectl apply -f web-configmap.yaml
kubectl apply -f web-deploy.yaml
kubectl apply -f web-svc.yaml
```

Test

```bash
kubectl -n obs-tools get pods,cronjobs,svc,pvc
kubectl -n obs-tools logs job/obs-tools-validate -f
kubectl -n obs-tools port-forward svc/obs-tools-web 8080:80
http://localhost:8080
```
