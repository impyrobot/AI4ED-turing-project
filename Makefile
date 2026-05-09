build-production:
	docker compose -f docker-compose.production.yml build

start-production:
	docker compose -f docker-compose.production.yml up -d

stop-production:
	docker compose -f docker-compose.production.yml down
