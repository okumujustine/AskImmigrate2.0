# Makefile for AskImmigrate 2.0
IMAGE_TAG    ?= 2.0.1
IMAGE_REG    := dunky2012

ASKIMMIGRATE_IMG := $(IMAGE_REG)/askimmigrate:$(IMAGE_TAG)

.PHONY: build push run stop clean logs shell help

build:
	@echo "→ Building AskImmigrate image"
	cp requirements.txt backend/
	docker buildx build --no-cache \
		-t $(ASKIMMIGRATE_IMG) \
		./backend
	rm backend/requirements.txt

push:
	@echo "→ Pushing AskImmigrate image to DockerHub"
	docker push $(ASKIMMIGRATE_IMG)

run:
	@echo "→ Starting AskImmigrate services"
	cp requirements.txt backend/
	docker compose -f docker-compose.yml up -d
	rm backend/requirements.txt

stop:
	@echo "→ Stopping AskImmigrate services"
	docker compose -f docker-compose.yml down

clean:
	@echo "→ Cleaning up containers and images"
	docker compose -f docker-compose.yml down --rmi all --volumes --remove-orphans

logs:
	@echo "→ Showing service logs"
	docker compose -f docker-compose.yml logs -f

shell:
	@echo "→ Opening shell in container"
	docker compose -f docker-compose.yml exec askimmigrate /bin/bash

help:
	@echo "Available commands:"
	@echo "  build      - Build Docker image"
	@echo "  push       - Push image to DockerHub"
	@echo "  run        - Start services with docker-compose"
	@echo "  stop       - Stop services"
	@echo "  clean      - Clean up containers and images"
	@echo "  logs       - Show service logs"
	@echo "  shell      - Open shell in running container"