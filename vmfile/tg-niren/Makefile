# dpl ?= ../.env/deploy.env
# include $(dpl)
# export $(shell sed 's/=.*//' $(dpl))

COMPOSE_FILE ?= docker-compose.yml

VERSION = "1.0.2"

# MAKE = make --no-print-directory
# EXEC = @../.utils/bash/main exec

# HELP
.PHONY: help

help: ## This help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ''

.DEFAULT_GOAL := help

# Build and run the container
  	# @docker-compose -p $project_name -f $compose_file up --build -d
up: version ## Boot up container
	# Boot up nginx
	@docker-compose -f "$(COMPOSE_FILE)" up --build

# reload: ## Reload nginx to apply config
# 	$(EXEC) nginx -s reload

version: ## output to version
	@echo $(VERSION)
