from pawnlib.config import pawn
from rich.prompt import Prompt, Confirm
from pawnlib.output import check_file_overwrite, print_syntax
import requests
import re
import yaml
import subprocess


class DockerComposeBuilder:
    """
    A class to build and manage Docker Compose files interactively.

    :param compose_file: Name of the Docker Compose file to be created or modified (default: "docker-compose.yml").

    Example:

        .. code-block:: python

            dcb = DockerComposeBuilder()

            dcb.create_docker_compose()
            # Starts an interactive session to create a Docker Compose file.

            dcb.save_docker_compose()
            # Saves the created Docker Compose data to a file.

            data = dcb.get_docker_compose_data()
            # Returns the Docker Compose data as a dictionary.

            dcb.remove_service()
            # Removes a service from the Docker Compose configuration.

    """
    def __init__(self, compose_file="docker-compose.yml"):
        self.compose_file = compose_file
        self.services = {}
        self.version = "3.8"
        self.first_loop = True
        self.port_asked = False
        self.env_asked = False
        self.vol_asked = False

    def create_docker_compose(self):
        pawn.console.print("[bold blue]Docker Compose File Creation Wizard[/bold blue]")
        self.version = Prompt.ask("Enter the Docker Compose version", default="3.8")

        while True:
            service_name = self.get_valid_input("\nEnter the service name", default="default")

            image = self.get_valid_input("Enter the image name", default="jinwoo/pawnlib")
            if not self.validate_docker_image(image):
                pawn.console.print(f"[bold red]Docker image '{image}' does not exist locally or in Docker Hub! Please enter a valid image.[/bold red]")
                continue
            service = {"image": image}

            if self.confirm_with_min_once("Would you like to map ports?", self.port_asked):
                service["ports"] = self.get_ports()
                self.port_asked = True

            if self.confirm_with_min_once("Would you like to add environment variables?", self.env_asked):
                service["environment"] = self.get_environment_variables()
                self.env_asked = True

            if self.confirm_with_min_once("Would you like to mount volumes?", self.vol_asked):
                service["volumes"] = self.get_volumes()
                self.vol_asked = True

            self.services[service_name] = service

            if self.confirm_with_default("Would you like to remove a service?", default=False):
                self.remove_service()

            if not self.confirm_with_default("Would you like to define another service?", default=False):
                break

    def confirm_with_min_once(self, message, already_asked):
        """Set the default value to ‘yes’ at least once, and then set it to ‘no’ afterwards."""
        if self.first_loop or not already_asked:
            return Confirm.ask(message, default=True)
        return Confirm.ask(message, default=False)

    def confirm_with_default(self, message, default=True):
        """Default confirm question logic"""
        return Confirm.ask(message, default=default)

    def get_valid_input(self, message, default=None):
        """Get valid non-empty input from the user, validate the input."""
        while True:
            user_input = Prompt.ask(message, default=default)
            if user_input and user_input.strip():
                return user_input.strip()
            pawn.console.print(f"[bold red]Input cannot be empty. Please enter a valid value.[/bold red]")

    def get_ports(self):
        """Get port mappings from the user."""
        ports = []
        while True:
            port = self.get_valid_input("Enter port mapping", default="80:80")
            if self.is_valid_port_mapping(port):
                ports.append(port)
            else:
                pawn.console.print(f"[bold red]Invalid port format. Please use the format 8080:80.[/bold red]")
            if not self.confirm_with_default("Would you like to add another port mapping?", default=False):
                break
        return ports

    def is_valid_port_mapping(self, port):
        """Validate port mapping format (e.g., 8080:80)"""
        return bool(re.match(r"^\d+:\d+$", port))

    def get_environment_variables(self):
        """Get environment variables from the user."""
        environment = {}
        while True:
            key = self.get_valid_input("Enter the environment variable key", default="TEST_KEY")
            value = self.get_valid_input("Enter the environment variable value", default="TEST_VALUE")
            environment[key] = value
            if not self.confirm_with_default("Would you like to add another environment variable?", default=False):
                break
        return environment

    def get_volumes(self, default_volume="./data:/data"):
        """Get volume mappings from the user and validate the format."""
        volumes = []
        while True:
            volume = self.get_valid_input("Enter the volume mount", default=default_volume)
            if self.is_valid_volume_mapping(volume):
                volumes.append(volume)
            else:
                pawn.console.print(f"[bold red]Invalid volume format. Please use the format ./data:/app/data.[/bold red]")
            if not self.confirm_with_default("Would you like to add another volume mount?", default=False):
                break
        return volumes

    def is_valid_volume_mapping(self, volume):
        """Validate volume mapping format (e.g., ./data:/app/data)"""
        return bool(re.match(r"^[^:]+:[^:]+$", volume))

    def validate_docker_image(self, image):
        """Validate if the Docker image exists locally or in Docker Hub"""
        if self.is_image_in_local(image):
            pawn.console.print(f"[bold green]Docker image '{image}' found locally.[/bold green]")
            return True
        else:
            return self.is_image_in_docker_hub(image)

    def is_image_in_local(self, image):
        """Check if the Docker image exists locally using docker images command"""
        try:
            result = subprocess.run(
                ["docker", "images", "-q", image],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return bool(result.stdout.strip())
        except Exception as e:
            pawn.console.print(f"[bold red]Error checking local Docker images: {e}[/bold red]")
            return False

    def is_image_in_docker_hub(self, image):
        """Validate if the Docker image exists in Docker Hub"""
        try:
            repo, tag = image.split(":") if ":" in image else (image, "latest")
            url = f"https://hub.docker.com/v2/repositories/{repo}/tags/{tag}"
            response = requests.get(url, verify=pawn.get('PAWN_SSL_CHECK'))
            if response.status_code == 200:
                pawn.console.print(f"[bold green]Docker image '{image}' found in Docker Hub.[/bold green]\n[grey74]({url})[/grey74]")
            return response.status_code == 200
        except Exception as e:
            pawn.console.print(f"[bold red]Error checking Docker Hub: {e}[/bold red]")
            return False

    def add_service(self, service_name="", service={}):

        self.services[service_name] = service

    def get_docker_compose_data(self):
        """Return the YAML data for Docker Compose."""
        return {
            "version": self.version,
            "services": self.services
        }

    def remove_service(self):
        """Remove a service from the services list."""
        if not self.services:
            pawn.console.print("[bold red]No services to remove![/bold red]")
            return

        service_to_remove = Prompt.ask(f"Enter the service name to remove from: {', '.join(self.services.keys())}")
        if service_to_remove in self.services:
            del self.services[service_to_remove]
            pawn.console.print(f"[bold green]{service_to_remove} has been removed![/bold green]")
        else:
            pawn.console.print(f"[bold red]{service_to_remove} does not exist![/bold red]")

    def save_docker_compose(self):
        """Save the Docker Compose data to a file, with confirmation."""
        docker_compose = self.get_docker_compose_data()

        # ['default', 'emacs', 'friendly', 'colorful', 'autumn', 'murphy', 'manni',
        # 'material', 'monokai', 'perldoc', 'pastie', 'borland', 'trac', 'native',
        # 'fruity', 'bw', 'vim', 'vs', 'tango', 'rrt', 'xcode', 'igor', 'paraiso-light',
        # 'paraiso-dark', 'lovelace', 'algol', 'algol_nu', 'arduino', 'rainbow_dash',
        # 'abap', 'solarized-dark', 'solarized-light', 'sas', 'stata', 'stata-light',
        # 'stata-dark', 'inkpot', 'zenburn']
        print_syntax(yaml.dump(docker_compose, default_flow_style=False, sort_keys=False), "yaml",  rich=True)

        if Confirm.ask("Would you like to save this configuration?", default=True):
            if check_file_overwrite(self.compose_file):
                try:
                    with open(self.compose_file, "w") as f:
                        yaml.dump(docker_compose, f, default_flow_style=False, sort_keys=False)
                    pawn.console.print("[bold green]docker-compose.yml file has been created![/bold green]")
                except IOError as e:
                    pawn.console.print(f"[bold red]Error writing file: {e}[/bold red]")
        else:
            pawn.console.print("[bold yellow]Save operation cancelled.[/bold yellow]")
