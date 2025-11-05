# OBS Tools

## Repo Structure

```text
root/
├─ clusters/
│  └─ obs-tools/                # Flux applies everything here to the cluster
│     ├─ flux-sources.yaml      # With this, any change you make under clusters/obs-tools/ will be reconciled by Flux (egress-only; Flux pulls from GitHub).
│     ├─ kustomization.yaml     # Flux Kustomization entrypoint
│     ├─ ns.yaml                # namescpace
│     ├─ rbac.yaml              # rbac
│     ├─ pvc.yaml               # persistent coolume clame
│     ├─ cfg-pipeline.yaml      # pipeline config (URLs, schedules, MODE)
│     ├─ web-configmap.yaml     # obs_tools.html
│     ├─ web-deploy.yaml        # nginx serving obs_tools.html + links-out.yaml
│     ├─ web-svc.yaml
│     ├─ cron-fetch-scrape.yaml # calls worker in MODE=GIT_HTML or MODE=API
│     └─ cron-validate.yaml     # runs check_links_async.py periodically
└─ worker/
   ├─ Dockerfile
   ├─ check_links_async.py      # links validation script
   ├─ scrape_links.py           # HTML -> links.yaml
   ├─ fetch_from_source.sh      # MODE=GIT_HTML | API dispatcher
   └─ api_fetch_links.py        # API -> links.yaml (future use)
```
