.PHONY: install run test test-cov lint format clean docker-build docker-run help

SERVICE_NAME = umbra-security-service
PORT = 5006

install: ## Installer les dépendances
	pip install -U pip
	pip install -r requirements.txt

run: ## Lancer le service
	python -m src.main

dev: ## Lancer en mode développement
	FLASK_ENV=development FLASK_DEBUG=1 python -m src.main

test: ## Lancer les tests
	pytest tests/ -v

test-cov: ## Tests avec couverture
	pytest tests/ -v --cov=src --cov-report=term-missing

lint: ## Vérifier le code
	flake8 src/ tests/

format: ## Formater le code
	black src/ tests/

docker-build: ## Construire l'image Docker
	docker build -t $(SERVICE_NAME):latest .

docker-dev: ## Environnement de développement
	docker-compose up -d

docker-stop: ## Arrêter Docker
	docker-compose down

clean: ## Nettoyer
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	rm -rf .pytest_cache/ htmlcov/ .coverage

help: ## Afficher l'aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
