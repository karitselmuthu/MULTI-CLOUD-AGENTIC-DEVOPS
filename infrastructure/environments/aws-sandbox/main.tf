# The provider refuses to plan or apply against a different AWS account.
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs#allowed_account_ids
provider "aws" {
  region              = var.aws_region
  allowed_account_ids = [var.aws_account_id]
}

module "sandbox" {
  source = "../../modules/aws"

  name              = var.name
  vpc_cidr          = var.vpc_cidr
  subnet_cidr       = var.subnet_cidr
  availability_zone = var.availability_zone
  tags = {
    owner       = var.owner
    cost_center = var.cost_center
    environment = "sandbox"
  }
}
