# PowerShell script to automate Docker build, push, and ECS update using terraform_outputs.json

# Load and parse the Terraform outputs JSON
$tfOutputs = Get-Content -Raw -Encoding UTF8 -Path "terraform_outputs.json" | ConvertFrom-Json

$ecrUrl = $tfOutputs.ecr_repository_url.value
$ecsCluster = $tfOutputs.ecs_cluster_name.value
$taskDefArn = $tfOutputs.task_definition_arn.value

# Build Docker image
Write-Host "Building Docker image..."
docker build -t credit-scoring-onchain ..

# Tag Docker image for ECR
Write-Host "Tagging Docker image for ECR..."
docker tag credit-scoring-onchain:latest $ecrUrl:latest

# Login to ECR
Write-Host "Logging in to ECR..."
aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin $ecrUrl.Split('/')[0]

# Push Docker image to ECR
Write-Host "Pushing Docker image to ECR..."
docker push $ecrUrl:latest

# Update ECS service (assumes service name is 'credit-scoring-service')
Write-Host "Updating ECS service..."
aws ecs update-service --cluster $ecsCluster --service credit-scoring-service --task-definition $taskDefArn

Write-Host "Deployment complete!"