import docker
import time

# initialize docker client
client = docker.from_env()

# function to start postgresql container
def create_container():
    try:
        print("Database container is starting.")
        container = client.containers.run(
            "postgres",
            name="mock-postgres",
            environment={
                "POSTGRES_USER": "user",
                "POSTGRES_PASSWORD": "pass",
                "POSTGRES_DB": "mockDB"
            },
            ports={"5432/tcp": 5432},
            detach=True
        )
        # wait for container initialization
        time.sleep(5)
        print("Database container is running. :)")
        return container

    except docker.errors.NotFound:
        print(f"Container {container.name} not found.")
        return

    except Exception as e:
        print(f"Error: {e}")
        return
    
def add_mock_data(container):
    try:
        data_insert = """
            psql -U user -d mockDB -c "
                CREATE TABLE IF NOT EXISTS mock_cities_data (
                    id SERIAL PRIMARY KEY,
                    city VARCHAR(50),
                    country VARCHAR(50)
                );
                INSERT INTO mock_cities_data (city, country) VALUES
                    ('Trento', 'Italy'),
                    ('Helsinki', 'Finland'),
                    ('Riga', 'Latvia'),
                    ('Milan', 'Italy'),
                    ('Kuopio', 'Finland');
            "
        """

        # run command inside container to insert mock data
        print("Inserting mock data inside the container.")
        result_insert = container.exec_run(data_insert, tty=False)
        print(result_insert.output.decode())

        # wait for data insertion
        time.sleep(5)

    except Exception as e:
        print(f"An error occurred: {e}")

# function to verify correctness of table
def print_mock_table(container):
    try:
        select_query = """
            psql -U user -d mockDB -c "
                SELECT * FROM mock_cities_data;
            "
        """
        result_print = container.exec_run(select_query, tty=False)
        print(result_print.output.decode())
    except Exception as e:
        print(f"An error occurred: {e}")
        return

# function to stop container
def stop_container(container):
    try:
        print("Stopping database container.")

        if container.status == "created":
            container.stop()
            
        # wait for container to stop
        time.sleep(5)
        container.remove()
        
        print("Container stopped.")
    except Exception as e:
        print(f"Error: {e}")


# main function
if __name__ == "__main__":
    
    container = create_container()
    
    if container:
        add_mock_data(container)
        print_mock_table(container)
        
        time.sleep(10) # timer before stopping container (for testing only)

    # stop and remove container after some time
    #if container:
    #    stop_container(container)