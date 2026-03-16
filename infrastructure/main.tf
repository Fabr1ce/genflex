# GenFlex Creative Storyteller - Google Cloud Infrastructure
# Terraform configuration for hackathon deployment

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs for Agent Engine, Storage, Redis, and Text-to-Speech
resource "google_project_service" "vertex_ai" {
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "memorystore" {
  service            = "redis.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "texttospeech" {
  service            = "texttospeech.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_storage" {
  service = "storage.googleapis.com"
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "genflex_repo" {
  repository_id = "genflex-storyteller-repo"
  location      = var.region
  format        = "DOCKER"
  description   = "Docker repository for GenFlex Storyteller"
  labels = {
    "env" = "dev"
  }
}


# Memorystore (Redis) for session management
resource "google_redis_instance" "genflex_cache" {
  name           = "genflex-cache"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region

  depends_on = [google_project_service.memorystore]
}

# Cloud Run service for the FastAPI application (COMMENTED OUT FOR AGENT ENGINE DEPLOYMENT)
resource "google_cloud_run_service" "genflex_storyteller" {
  name     = "genflex-storyteller"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.genflex_repo.repository_id}/genflex-storyteller:latest"

        ports {
          container_port = 8080
        }

        env {
          name  = "LOGS_BUCKET_NAME"
          value = google_storage_bucket.genflex_bucket.name
        }

        env {
          name  = "GEMINI_MODEL"
          value = "gemini-2.5-flash"
        }

        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }

        env {
          name  = "GOOGLE_CLOUD_LOCATION"
          value = var.region
        }

        env {
          name  = "REDIS_HOST"
          value = google_redis_instance.genflex_cache.host
        }

        env {
          name  = "REDIS_PORT"
          value = google_redis_instance.genflex_cache.port
        }

        resources {
          limits = {
            cpu    = "1000m"
            memory = "1Gi"
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_project_service.cloud_run, google_artifact_registry_repository.genflex_repo]
}

# GCS bucket for generated media (images, audio, video)
resource "google_storage_bucket" "genflex_bucket" {
  name                        = "genflex-bucket-${var.project_id}" # Make bucket name unique
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  lifecycle_rule {
    condition { age = 30 }
    action    { type = "Delete" }
  }
  depends_on = [google_project_service.cloud_storage]
}

# IAM service account for the application
resource "google_service_account" "genflex_sa" {
  account_id   = "genflex-storyteller-sa"
  display_name = "GenFlex Storyteller Service Account"
}

# Grant Vertex AI permissions
resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.genflex_sa.email}"
}

# Grant Cloud TTS permissions
resource "google_project_iam_member" "tts_user" {
  project = var.project_id
  role    = "roles/serviceusage.serviceUsageConsumer"
  member  = "serviceAccount:${google_service_account.genflex_sa.email}"
}

# Grant service account write access to the media bucket
resource "google_storage_bucket_iam_member" "genflex_sa_bucket_writer" {
  bucket = google_storage_bucket.genflex_bucket.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.genflex_sa.email}"
}

# Allow public access to Cloud Run (COMMENTED OUT)
resource "google_cloud_run_service_iam_member" "public_access" {
  service  = google_cloud_run_service.genflex_storyteller.name
  location = google_cloud_run_service.genflex_storyteller.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Variables
variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud Region"
  type        = string
  default     = "us-central1"
}

# Outputs
output "bucket_name" {
  description = "GCS bucket for generated media"
  value       = google_storage_bucket.genflex_bucket.name
}

output "cloud_run_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_service.genflex_storyteller.status[0].url
}

output "redis_host" {
  description = "Redis instance host"
  value       = google_redis_instance.genflex_cache.host
}

output "redis_port" {
  description = "Redis instance port"
  value       = google_redis_instance.genflex_cache.port
}