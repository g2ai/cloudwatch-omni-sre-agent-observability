# Teardown

Removes everything this build creates, in order. Items created outside Terraform come first, because they depend on resources Terraform will delete.

Cost while left running is close to zero (Lambda, SNS and alarms idle at about $0.20 per month), but the Omni space, X-Ray indexing at 100% and OTel enrichment should not be left on by accident.

## 1. Stop the online evaluation and delete the evaluator (CLI and Omni UI)

The online evaluation locks the custom evaluator, so disable it first.

1. Omni web UI → Evaluate → Online evaluations → `sre_agent_quality` → disable, then delete.
2. Delete the code-based evaluator:

```powershell
aws bedrock-agentcore-control delete-evaluator --evaluator-id <EVALUATOR_ID> --profile <PROFILE>
aws bedrock-agentcore-control list-evaluators --profile <PROFILE>
```

3. Delete the online evaluation results log group:

```powershell
aws logs delete-log-group --log-group-name /aws/bedrock-agentcore/evaluations/results/<ONLINE_EVAL_CONFIG_ID> --profile <PROFILE>
```

## 2. Destroy the Terraform workload

The plan reads the agent package, so build it first. The alert email is required while the workload exists.

```powershell
.\scripts\build_sre_agent.ps1
$env:TF_VAR_alert_email = "<your-email>"
terraform -chdir=deploy\terraform plan -destroy -var="enable_workload=true" -out="destroy.tfplan"
terraform -chdir=deploy\terraform apply "destroy.tfplan"
```

This removes the three Lambda functions, their roles, log groups and function URLs, the SNS topic and subscription, both CloudWatch alarms, and the inline invoke policies added to the two Omni space roles. The space roles themselves are not touched.

Verify:

```powershell
aws lambda list-functions --profile <PROFILE> --query "Functions[?contains(['telemetry-api','sre-agent','freshness-evaluator'], FunctionName)].FunctionName"
```

The result must be empty.

## 3. Revert account-level settings changed for the lab

| Setting | Lab value | Revert |
|---|---|---|
| X-Ray indexing rule `Default` | 100% | Back to 1% (CloudWatch console → Settings → X-Ray traces → Indexing) |
| OTel enrichment for AWS vended metrics | On | Turn off if nothing else uses it |
| Log group `aws/spans` | Retention not set | Set retention or delete |
| Transaction Search | Active | Keep if other workloads use it |

## 4. Delete the CloudWatch Omni space and domain

CloudWatch console → Omni → delete the space, then the domain. This also removes the space roles created by setup. Check IAM afterwards for leftover roles with the space suffix.

## 5. Local cleanup

- Delete `deploy/terraform/terraform.tfstate*` after a successful destroy (it contains the alert email).
- Delete `deploy/terraform/build/`.
- Delete the spike virtual environment if you created one.