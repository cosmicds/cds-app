terraform {
  backend "local" {
    path = "../../.terraform-state/demo/terraform.tfstate"
  }
}
