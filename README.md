# cmr_token_creator

Retrieves CMR token from Earthdata Login and stores the token in AWS SSM 
Parameter Store.

This can be run every 59 days in order to renew credentials during an 
execution of Confluence.

## aws infrastructure

The renew program includes the following AWS services:

- Lambda function to execute code deployed via zip file.
- IAM role and policy for Lambda function execution.
- EventBridge schedule to run Lambda function every 59 days.
- IAM role and policy for EventBridge schedule execution.
- Permissions that allow EventBridge to invoke the Lambda function.

## deployment

There is a script to deploy the Lambda function AWS infrastructure called `deploy.sh`.

REQUIRES:

- AWS CLI (<https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html>)
- Terraform (<https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli>)

Command line arguments:

 [1] app_name: Name of application to create a zipped deployment package for
 [2] s3_state_bucket: Name of the S3 bucket to store Terraform state in (no need for s3:// prefix)
 [3] profile: Name of profile used to authenticate AWS CLI commands

Example usage: `./delpoy-lambda.sh "my-app-name" "s3-state-bucket-name" "confluence-named-profile"`
