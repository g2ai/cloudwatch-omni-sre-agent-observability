# Alert email comes from TF_VAR_alert_email so it never lands in the repo.
variable "alert_email" {
  description = "Email for alarm notifications. Set TF_VAR_alert_email; do not commit it."
  type        = string
  default     = ""
}

variable "online_eval_config_id" {
  description = "AgentCore online evaluation config ID (created in the Omni UI)."
  type        = string
  default     = "sre_agent_quality-qac2opE5ov"
}

locals {
  alerts_on = var.enable_workload && var.alert_email != "" ? 1 : 0
}

resource "aws_sns_topic" "alerts" {
  count = local.alerts_on
  name  = "build04-agent-quality-alerts"
}

resource "aws_sns_topic_subscription" "alert_email" {
  count     = local.alerts_on
  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Fires when any sampled trace in 5 minutes used stale data and did not say so.
# Minimum, not Average: one wrong answer must not hide among good ones.
resource "aws_cloudwatch_metric_alarm" "stale_answers" {
  count               = local.alerts_on
  alarm_name          = "sre-agent-stale-answers"
  alarm_description   = "sre-agent answered with stale data presented as current (freshness_evaluator < 1)."
  namespace           = "Bedrock-AgentCore/Evaluations"
  metric_name         = "freshness_evaluator"
  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    "service.name"           = "sre-agent"
    onlineEvaluationConfigId = var.online_eval_config_id
  }

  alarm_actions = [aws_sns_topic.alerts[0].arn]
  ok_actions    = [aws_sns_topic.alerts[0].arn]
}

output "alerts_topic_arn" {
  description = "SNS topic for agent quality alarms."
  value       = one(aws_sns_topic.alerts[*].arn)
}
