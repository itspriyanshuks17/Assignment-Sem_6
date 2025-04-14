# Cloud Assignment-2: AWS Console Procedure

## ✅ Overview
This guide explains how to perform the full cloud setup using the AWS Console for:
- S3 → SNS → SQS → Lambda
- CloudWatch alarms
- QuickSight dashboard for file upload logs
- Optional Macie integration

## 1. Create S3 Bucket
- Go to **S3 > Create bucket**
- Name: `bucket-ctis`
- Region: `us-east-1`
- Block public access: ✅
- Create bucket

## 2. Create SNS Topic
- Go to **SNS > Topics > Create topic**
- Type: Standard
- Name: `file-upload-topic`
- Copy the Topic ARN for later

## 3. Create SQS Queue
- Go to **SQS > Create queue**
- Name: `file-upload-queue`
- Standard queue
- Save the ARN

## 4. Subscribe SQS to SNS
- SNS > Subscriptions > Create subscription
- Topic ARN: `file-upload-topic`
- Protocol: `Amazon SQS`
- Endpoint: SQS ARN

## 5. Update SQS Queue Policy
```json
{
  "Effect": "Allow",
  "Principal": {"Service": "sns.amazonaws.com"},
  "Action": "SQS:SendMessage",
  "Resource": "arn:aws:sqs:us-east-1:ACCOUNT_ID:file-upload-queue",
  "Condition": {
    "ArnEquals": {
      "aws:SourceArn": "arn:aws:sns:us-east-1:ACCOUNT_ID:file-upload-topic"
    }
  }
}
```

## 6. Add S3 Event Notification
- S3 > `bucket-ctis` > Properties > Event notifications
- Add notification:
  - Event: `PUT` (object created)
  - Destination: SNS → `file-upload-topic`

## 7. Create Lambda Function
- Go to **Lambda > Create Function**
- Name: `ProcessS3Upload`
- Runtime: Python 3.10
- Create role with basic Lambda permissions

### Sample Code
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

## 8. Add SQS Trigger to Lambda
- Lambda > Triggers > Add SQS trigger
- Choose `file-upload-queue`
- ✅ Enable trigger

## 9. Add S3 Permissions to Lambda Role
- IAM > Roles > Your Lambda Role > Add inline policy
- Permissions: `s3:PutObject` to `processed-logs-ctis/*`

## 10. Create CloudWatch Alarm
- CloudWatch > Alarms > Create alarm
- Metric: Lambda errors (from `ProcessS3Upload`)
- Threshold: `>= 1 error`
- Notifications: SNS/email

## 11. Setup QuickSight Dashboard
- Enable QuickSight
- Upload processed logs to S3
- Use AWS Glue + Athena to catalog and query
- Visualize:
  - File uploads (bar/line chart)
  - Sensitive alerts (pie chart)

## 12. (Optional) Macie Integration
- Enable Amazon Macie
- Scan `bucket-ctis`
- Export results to S3
- Visualize Macie data in QuickSight
