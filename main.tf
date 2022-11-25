terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

variable "region" {
  default = "us-east-1"
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}


locals {
  account_id          = data.aws_caller_identity.current.account_id
  ecr_repository_name = "housing-bot-ecr-repository"
  ecr_image_tag       = "latest"
  src_dir             = "src"
}


resource "aws_ecr_repository" "repo" {
  name = local.ecr_repository_name
}

# The null_resource resource implements the standard resource lifecycle but takes no further action.
# The triggers argument allows specifying an arbitrary set of values that, when changed, 
#   will cause the resource to be replaced.
resource "null_resource" "ecr_image" {
  triggers = {
    src_dir     = md5(join("", [for f in fileset("${path.module}/${local.src_dir}", "**") : filesha1("${path.module}/${local.src_dir}/${f}")]))
    docker_file = md5(file("${path.module}/Dockerfile"))
  }

  provisioner "local-exec" {
    command = <<EOF
           aws ecr get-login-password --region ${var.region} | docker login --username AWS --password-stdin ${local.account_id}.dkr.ecr.${var.region}.amazonaws.com
           cd ${path.module}
           docker build -t ${aws_ecr_repository.repo.repository_url}:${local.ecr_image_tag} .
           docker push ${aws_ecr_repository.repo.repository_url}:${local.ecr_image_tag}
       EOF
  }
}

data "aws_ecr_image" "lambda_image" {
  depends_on = [
    null_resource.ecr_image
  ]
  repository_name = local.ecr_repository_name
  image_tag       = local.ecr_image_tag
}
resource "aws_iam_role" "iam_for_lambda" {
  name = "iam_for_housing_bot_lambda"

  assume_role_policy = jsonencode(
    {
      "Version" : "2012-10-17",
      "Statement" : [
        {
          "Action" : "sts:AssumeRole",
          "Principal" : {
            "Service" : "lambda.amazonaws.com"
          },
          "Effect" : "Allow",
          "Sid" : ""
        }
      ]
  })

  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    aws_iam_policy.dynamo_db_for_lambda.arn,
    aws_iam_policy.sns_for_lambda.arn
  ]
}

resource "aws_iam_policy" "dynamo_db_for_lambda" {
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Action" : [
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query",
          "dynamodb:BatchGetItem",
        ],
        "Resource" : [
          "arn:aws:dynamodb:${var.region}:${local.account_id}:table/ScraperHistory"
        ],
        "Effect" : "Allow"
      }
    ]
  })
}

resource "aws_iam_policy" "sns_for_lambda" {
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Action" : [
          "sns:Publish"
        ],
        "Resource" : [
          "arn:aws:sns:${var.region}:${local.account_id}:MessengerHousingBot"
        ],
        "Effect" : "Allow"
      }
    ]
  })
}

resource "aws_sns_topic" "housing_bot_sns_topic" {
  name = "housing_bot_sns_topic"
}

resource "aws_sns_topic_subscription" "housing_bot_sns_topic_subscription" {
  topic_arn = aws_sns_topic.housing_bot_sns_topic.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.housing-bot.arn
}

resource "aws_lambda_function" "housing-bot" {
  depends_on = [
    null_resource.ecr_image
  ]
  function_name = "HousingBot"
  image_uri     = "${aws_ecr_repository.repo.repository_url}@${data.aws_ecr_image.lambda_image.id}"
  role          = aws_iam_role.iam_for_lambda.arn
  memory_size   = 256
  package_type  = "Image"

  environment {
    variables = {
      "NLTK_DATA"     = "/var/task/nltk_data",
      "SNS_TOPIC_ARN" = "arn:aws:sns:${var.region}:${local.account_id}:MessengerHousingBot"
    }
  }
}

resource "aws_lambda_function_url" "housing_bot_latest" {
  function_name      = aws_lambda_function.housing-bot.function_name
  authorization_type = "NONE"
}
