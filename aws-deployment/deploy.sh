#!/bin/bash

# AWS Deployment Script for StartupAutoApplier
# This script deploys the application to AWS ECS with auto-scaling

set -e

# Configuration
AWS_REGION="us-east-1"
ECR_REPOSITORY="startup-auto-applier"
ECS_CLUSTER="startup-auto-applier-cluster"
ECS_SERVICE="startup-auto-applier-service"
TASK_DEFINITION="startup-auto-applier"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying StartupAutoApplier to AWS...${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${YELLOW}📋 AWS Account ID: $AWS_ACCOUNT_ID${NC}"

# Create ECR repository if it doesn't exist
echo -e "${YELLOW}📦 Creating ECR repository...${NC}"
aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION 2>/dev/null || echo "Repository already exists"

# Get ECR login token
echo -e "${YELLOW}🔐 Logging into ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and tag Docker image
echo -e "${YELLOW}🏗️  Building Docker image...${NC}"
docker build -f aws-deployment/Dockerfile.production -t $ECR_REPOSITORY .

# Tag for ECR
docker tag $ECR_REPOSITORY:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

# Push to ECR
echo -e "${YELLOW}⬆️  Pushing image to ECR...${NC}"
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

# Update task definition
echo -e "${YELLOW}📝 Updating ECS task definition...${NC}"
aws ecs register-task-definition \
    --cli-input-json file://aws-deployment/ecs-task-definition.json \
    --region $AWS_REGION

# Update ECS service
echo -e "${YELLOW}🔄 Updating ECS service...${NC}"
aws ecs update-service \
    --cluster $ECS_CLUSTER \
    --service $ECS_SERVICE \
    --task-definition $TASK_DEFINITION \
    --region $AWS_REGION

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${YELLOW}📊 Monitor your deployment in the AWS ECS console:${NC}"
echo -e "https://$AWS_REGION.console.aws.amazon.com/ecs/v2/clusters/$ECS_CLUSTER/services/$ECS_SERVICE" 