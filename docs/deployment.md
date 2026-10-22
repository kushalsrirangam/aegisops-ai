# Deployment direction

The supplied Compose stack is the only runnable deployment. A production AWS design would use private ECS/Fargate tasks for API and UI, RDS PostgreSQL with pgvector, a load balancer with TLS, role-based IAM, Secrets Manager, CloudWatch logs, database backups, migration jobs, and authenticated user access. Use separate execution and read-only investigation roles. Restrict egress, apply rate limits and request timeouts, add durable LangGraph checkpoints, and review infrastructure plans before apply. No Terraform module or AWS deployment automation is currently provided.
