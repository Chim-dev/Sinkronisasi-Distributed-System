from locust import HttpUser, between, task


class DistributedSyncUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(2)
    def queue_publish_consume(self):
        self.client.post("/queue/orders/publish", json={"order_id": "locust", "amount": 100})
        response = self.client.post("/queue/orders/consume", json={})
        data = response.json()
        message = data.get("message")
        if message:
            self.client.post(f"/queue/ack/{message['id']}", json={})

    @task(1)
    def cache_put_get(self):
        self.client.post("/cache/product-1", json={"stock": 10})
        self.client.get("/cache/product-1")

    @task(1)
    def lock_attempt(self):
        self.client.post("/locks/acquire", json={"resource": "inventory", "owner": "locust", "mode": "exclusive"})
        self.client.post("/locks/release", json={"resource": "inventory", "owner": "locust"})
