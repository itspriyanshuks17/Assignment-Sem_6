# Cloud Assignment-2: Terraform Procedure

## ✅ Overview
This guide covers automating the setup using Terraform:
- S3, SNS, SQS, Lambda
- Permissions and policies
- CloudWatch alarms
- Log storage for QuickSight

## 1. providers.tf
```hcl
provider "aws" {
  region = "us-east-1"
}
```

## 2. variables.tf
```hcl
variable "bucket_name" { default = "bucket-ctis" }
variable "log_bucket_name" { default = "processed-logs-ctis" }
variable "sns_topic_name" { default = "file-upload-topic" }
variable "sqs_queue_name" { default = "file-upload-queue" }
```

## 3. main.tf

### S3 Buckets
```hcl
resource "aws_s3_bucket" "file_upload_bucket" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket" "log_bucket" {
  bucket = var.log_bucket_name
}
```

### SNS Topic + Policy
```hcl
resource "aws_sns_topic" "file_upload_topic" {
  name = var.sns_topic_name
}

resource "aws_sns_topic_policy" "allow_s3_publish" {
  arn = aws_sns_topic.file_upload_topic.arn
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "s3.amazonaws.com" },
      Action = "sns:Publish",
      Resource = aws_sns_topic.file_upload_topic.arn,
      Condition = {
        ArnLike = { "aws:SourceArn" = aws_s3_bucket.file_upload_bucket.arn }
      }
    }]
  })
}
```

### SQS Queue + Policy + Subscription
```hcl
resource "aws_sqs_queue" "file_upload_queue" {
  name = var.sqs_queue_name
}

resource "aws_sns_topic_subscription" "sqs_sub" {
  topic_arn = aws_sns_topic.file_upload_topic.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.file_upload_queue.arn
}

resource "aws_sqs_queue_policy" "allow_sns" {
  queue_url = aws_sqs_queue.file_upload_queue.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "sns.amazonaws.com" },
      Action = "SQS:SendMessage",
      Resource = aws_sqs_queue.file_upload_queue.arn,
      Condition = {
        ArnEquals = {
          "aws:SourceArn" = aws_sns_topic.file_upload_topic.arn
        }
      }
    }]
  })
}
```

### Lambda + Role + Policy + SQS Trigger
```hcl
resource "aws_iam_role" "lambda_exec_role" {
  name = "lambda_exec_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "lambda.amazonaws.com" },
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_policy" "lambda_sqs_s3_policy" {
  name = "lambda_sqs_s3_access"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"],
        Effect = "Allow",
        Resource = aws_sqs_queue.file_upload_queue.arn
      },
      {
        Action = ["s3:PutObject"],
        Effect = "Allow",
        Resource = "${aws_s3_bucket.log_bucket.arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_sqs_s3_policy.arn
}

resource "aws_lambda_function" "process_file" {
  function_name = "ProcessS3Upload"
  runtime       = "python3.10"
  handler       = "lambda_function.lambda_handler"
  filename      = "lambda.zip"
  role          = aws_iam_role.lambda_exec_role.arn
}

resource "aws_lambda_event_source_mapping" "lambda_trigger" {
  event_source_arn = aws_sqs_queue.file_upload_queue.arn
  function_name    = aws_lambda_function.process_file.arn
  batch_size       = 10
  enabled          = true
}
```

### S3 Notification
```hcl
resource "aws_s3_bucket_notification" "s3_to_sns" {
  bucket = aws_s3_bucket.file_upload_bucket.id
  topic {
    topic_arn = aws_sns_topic.file_upload_topic.arn
    events    = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_sns_topic_policy.allow_s3_publish]
}
```

## 4. CloudWatch Alarm
```hcl
resource "aws_cloudwatch_metric_alarm" "lambda_error_alarm" {
  alarm_name          = "LambdaErrorAlarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  dimensions = {
    FunctionName = aws_lambda_function.process_file.function_name
  }
}
```

## 5. Lambda Function Code
```python
import json
import boto3
from datetime import datetime
import uuid

s3 = boto3.client('s3')
LOG_BUCKET = 'processed-logs-ctis'

def lambda_handler(event, context):
    for record in event['Records']:
        message = json.loads(record['body'])
        s3_info = message['Records'][0]['s3']
        filename = s3_info['object']['key']

        result = {
            "filename": filename,
            "upload_time": datetime.utcnow().isoformat(),
            "status": "success",
            "sensitive_data_found": False
        }

        log_key = f"logs/{uuid.uuid4()}.json"
        s3.put_object(
            Bucket=LOG_BUCKET,
            Key=log_key,
            Body=json.dumps(result),
            ContentType='application/json'
        )
```