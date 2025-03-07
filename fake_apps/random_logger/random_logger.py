import time
import random

while True:
    print(f"Random number: {random.randint(1,100)}",flush=True)
    time.sleep(2)

#docker build -t random-logger .
#docker save random_logger -o random_logger.tar
#docker load -i random_logger.tard
