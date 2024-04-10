# AWS Lambda function
resource "aws_lambda_function" "aws_lambda_cmr" {
  filename         = "cmr_token_creator.zip"
  function_name    = "${var.prefix}-cmr-token-creator"
  role             = aws_iam_role.aws_lambda_cmr_execution_role.arn
  handler          = "cmr_token_creator.lambda_handler"
  runtime          = "python3.9"
  source_code_hash = filebase64sha256("cmr_token_creator.zip")
  timeout          = 300
  tags = {
    "Name" = "${var.prefix}-cmr-token-creator"
  }
}

# AWS Lambda execution role & policy
resource "aws_iam_role" "aws_lambda_cmr_execution_role" {
  name = "${var.prefix}-lambda-cmr-execution-role"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
}

# Parameter Store policy
resource "aws_iam_role_policy_attachment" "aws_lambda_get_put_parameter_policy_attach" {
  role       = aws_iam_role.aws_lambda_cmr_execution_role.name
  policy_arn = data.aws_iam_policy.get_put_parameter.arn
}

# Execution policy
resource "aws_iam_role_policy_attachment" "aws_lambda_cmr_execution_role_policy_attach" {
  role       = aws_iam_role.aws_lambda_cmr_execution_role.name
  policy_arn = aws_iam_policy.aws_lambda_cmr_execution_policy.arn
}

resource "aws_iam_policy" "aws_lambda_cmr_execution_policy" {
  name        = "${var.prefix}-lambda-cmr-execution-policy"
  description = "Upload files to bucket and send messages to queue."
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Sid" : "AllowCreatePutLogs",
        "Effect" : "Allow",
        "Action" : [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource" : "arn:aws:logs:*:*:*"
      },
      {
        "Sid" : "EncryptDecryptKey",
        "Effect" : "Allow",
        "Action" : [
          "kms:DescribeKey",
          "kms:Encrypt",
          "kms:Decrypt"
        ],
        "Resource" : "${data.aws_kms_key.ssm_key.arn}"
      }
    ]
  })
}

# EventBridge schedule
resource "aws_scheduler_schedule" "aws_schedule_cmr" {
  name       = "${var.prefix}-cmr-token-creator"
  group_name = "default"
  flexible_time_window {
    mode = "OFF"
  }
  schedule_expression = "rate(59 days)"
  target {
    arn      = aws_lambda_function.aws_lambda_cmr.arn
    role_arn = aws_iam_role.aws_eventbridge_cmr_execution_role.arn
    input = jsonencode({
      prefix = "${var.prefix}"
    })
  }
  state = "ENABLED"
}

# EventBridge execution role and policy
resource "aws_iam_role" "aws_eventbridge_cmr_execution_role" {
  name = "${var.prefix}-eventbridge-cmr-execution-role"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "scheduler.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "aws_eventbridge_cmr_execution_role_policy_attach" {
  role       = aws_iam_role.aws_eventbridge_cmr_execution_role.name
  policy_arn = aws_iam_policy.aws_eventbridge_cmr_execution_policy.arn
}

resource "aws_iam_policy" "aws_eventbridge_cmr_execution_policy" {
  name        = "${var.prefix}-eventbridge-cmr-execution-policy"
  description = "Allow EventBridge to invoke a Lambda function."
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Sid" : "AllowInvokeLambda",
        "Effect" : "Allow",
        "Action" : [
          "lambda:InvokeFunction"
        ],
        "Resource" : "${aws_lambda_function.aws_lambda_cmr.arn}"
      }
    ]
  })
}