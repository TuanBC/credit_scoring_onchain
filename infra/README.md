# AWS Infrastructure for credit_scoring_onchain

## Overview

This Terraform configuration deploys the FastAPI + Gradio Docker app to AWS using ECS Fargate, ECR, ALB, and VPC best practices.

## Usage

1. Install [Terraform](https://www.terraform.io/downloads.html) and configure your AWS credentials.
2. Update `variables.tf` if you want to change the region.
3. Run:

   ```sh
   terraform init
   terraform apply
   ```

4. Build and push your Docker image to the ECR repo shown in the output.
5. Update the ECS service to use the new image (see CI/CD below).

## CI/CD

- Use GitHub Actions to build, tag, and push your Docker image to ECR, then update ECS service.
- See example workflow below.

## Example GitHub Actions Workflow

```yaml
name: Deploy to AWS ECS
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      - name: Build, tag, and push image
        run: |
          docker build -t ${{ steps.login-ecr.outputs.registry }}/credit-scoring-onchain:latest .
          docker push ${{ steps.login-ecr.outputs.registry }}/credit-scoring-onchain:latest
      - name: Update ECS service
        run: |
          aws ecs update-service --cluster credit-scoring-cluster --service fastapi-gradio --force-new-deployment
```

## Outputs

- `ecr_repository_url`: Docker image repo
- `ecs_cluster_name`: ECS cluster name
- `alb_dns_name`: Public endpoint for your app
