terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
  required_version = ">= 1.5.7"
}

provider "aws" {
  region = var.aws_region
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  name    = "credit-scoring-vpc"
  cidr    = "10.0.0.0/16"
  azs     = ["${var.aws_region}a", "${var.aws_region}b"]
  public_subnets  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnets = ["10.0.3.0/24", "10.0.4.0/24"]
  enable_nat_gateway = true
  single_nat_gateway = true
}

module "ecr" {
  source = "terraform-aws-modules/ecr/aws"
  repository_name = "credit-scoring-onchain"
  repository_force_delete = true
}


# ECS Cluster
module "ecs_cluster" {
  source       = "terraform-aws-modules/ecs/aws//modules/cluster"
  name         = "credit-scoring-cluster"
}

# ECS Fargate Service
module "ecs_service" {
  source                = "terraform-aws-modules/ecs/aws//modules/service"
  name                  = "fastapi-gradio"
  cluster_arn           = module.ecs_cluster.arn
  task_exec_iam_role_arn = null
  cpu                   = 1024
  memory                = 2048
  desired_count         = 1
  launch_type           = "FARGATE"
  subnet_ids            = module.vpc.private_subnets
  security_group_ids    = [module.vpc.default_security_group_id]
  assign_public_ip      = false
  container_definitions = {
    app = {
      image     = "${module.ecr.repository_url}:latest"
      essential = true
      portMappings = [
        { containerPort = 8000, protocol = "tcp" },
        { containerPort = 7860, protocol = "tcp" }
      ]
      environment = [
        { name = "ENV", value = "production" }
      ]
    }
  }
  load_balancer = {
    fastapi = {
      target_group_arn = module.alb.target_groups["fastapi"].arn
      container_name   = "app"
      container_port   = 8000
    },
    gradio = {
      target_group_arn = module.alb.target_groups["gradio"].arn
      container_name   = "app"
      container_port   = 7860
    }
  }
}

module "alb" {
  source = "terraform-aws-modules/alb/aws"
  name   = "credit-scoring-alb"
  vpc_id = module.vpc.vpc_id
  subnets = module.vpc.public_subnets
  security_groups = [module.vpc.default_security_group_id]
  target_groups = {
    fastapi = {
      name_prefix      = "fastapi"
      backend_protocol = "HTTP"
      backend_port     = 8000
      target_type      = "ip"
      health_check = {
        enabled             = true
        interval            = 30
        path                = "/"
        port                = "8000"
        protocol            = "HTTP"
        matcher             = "200-399"
        timeout             = 5
        healthy_threshold   = 2
        unhealthy_threshold = 2
      }
    }
    gradio = {
      name_prefix      = "gradio"
      backend_protocol = "HTTP"
      backend_port     = 7860
      target_type      = "ip"
      health_check = {
        enabled             = true
        interval            = 30
        path                = "/"
        port                = "7860"
        protocol            = "HTTP"
        matcher             = "200-399"
        timeout             = 5
        healthy_threshold   = 2
        unhealthy_threshold = 2
      }
    }
  }
  listeners = {
    http = {
      port     = 80
      protocol = "HTTP"
      default_action = {
        type               = "forward"
        target_group_index = 0
      }
    }
  }
}
