# Phase 8 Cloud-Test automation

## Prerequisites

- Azure CLI login (`az login`)
- Subscription access to:
  - `27db5ec6-d206-4028-b5e1-6004dca5eeef`
  - resource group `2dt-final-team4`
- Local Python environment with project dependencies

## End-to-end

```bash
scripts/cloud/phase8/run_all.sh
```

## Step-by-step

```bash
scripts/cloud/phase8/provision_resources.sh
scripts/cloud/phase8/build_push_images.sh
scripts/cloud/phase8/run_db_migrations.sh
scripts/cloud/phase8/deploy_apps.sh
scripts/cloud/phase8/run_smoke.sh
scripts/cloud/phase8/destroy_recreate_check.sh
```

## Runtime env file

- Default output: `.env/phase8_cloud_test.env`
- Override path: `PHASE8_ENV_FILE=/path/to/file`

## Notes

- Consumer deploy profile is fixed to `min=1`, `max=1`.
- If RG delete lock blocks app deletion during recreate check, the script falls back to scale cycle (`1 -> 0 -> 1`) and revalidates pipeline health.
