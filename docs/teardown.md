# Teardown

Remove everything this build creates, in this order. Steps marked **verify before use** have not been run yet; check the AWS docs or `--help` first.

Region: `ap-south-1`. CLI profile: `build04` (admin) and `build04-ro` (read-only checks).

## 1. Stop paid activity first

1. In CloudWatch Omni, disable every online evaluation configuration (Online evaluations).
2. If the DevOps Agent integration is connected: Settings > Integrations > Amazon DevOps Agent > remove. Then delete the DevOps Agent agent space in the DevOps Agent console.

## 2. Remove the workload

```powershell
Set-Location deploy\terraform
terraform destroy
```

## 3. Remove Omni content

1. Delete custom evaluators, datasets and saved experiments in Omni.
2. Delete Omni alerts and dashboards created for this build.

## 4. Revert account and Region settings changed for the lab

X-Ray span indexing back to the 1% default:

```powershell
aws xray update-indexing-rule --name Default --rule "Probabilistic={DesiredSamplingPercentage=1}" --profile build04
```

OTel enrichment for AWS vended metrics (**verify before use**):

```powershell
aws cloudwatch stop-otel-enrichment --profile build04
aws observabilityadmin stop-telemetry-enrichment --profile build04
```

Transaction Search: keep it if other workloads use it. To stop sending spans to CloudWatch Logs, change the trace segment destination (**verify before use**).

## 5. Delete the Omni space and domain

1. CloudWatch console > Settings > Omni > Space > Actions > delete the space.
2. Then delete the account domain.
3. Check that the roles created by setup are gone (`CloudWatchOmniSpaceAccessRole-*`, `AgentCoreEvaluationRole-*`), and the Dataset integration with its execution role. Delete any that remain (**verify before use**).

## 6. Logs and local files

1. Log group `aws/spans`: set retention or delete it.
2. Delete local `.env`, `.omni/`, `.env.omni` and any test venv.

## 7. Check

```powershell
aws resourcegroupstaggingapi get-resources --tag-filters Key=build,Values=build-04 --profile build04-ro --query "ResourceTagMappingList[].ResourceARN"
aws xray get-indexing-rules --profile build04-ro
```

The first command should return an empty list. The second should show `DesiredSamplingPercentage` 1.0.
