from locust import HttpUser, task, between
import random

class AsyncLocustTask(HttpUser):
    wait_time = between(0.01, 0.05)

    @task
    def get_thumbnail_small(self):
        idx = random.randint(0, 3)
        self.client.get(f'/images/img{idx}.jpg/small', name='Get small thumbnail')

    @task
    def get_thumbnail_medium(self):
        idx = random.randint(0, 3)
        self.client.get(f'/images/img{idx}.jpg/medium', name='Get medium thumbnail')