# Optional AWS deployment foundation

Terraform deployment is intentionally not automated. This project ships a local Compose runtime and a small `modules/observer_policy` module that emits scoped IAM JSON without creating a resource. Production ECS/Fargate modules, VPC, RDS, secret management, and deployment pipelines remain future work. Do not run `terraform apply` against an AWS account without a reviewed deployment plan.
