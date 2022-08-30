import os
from typing import Union

from pydantic import BaseSettings


class Base(BaseSettings):
    SECRET_KEY: str = "random_string"
    PORT: int = 5050
    USERNAME: str = "ANAND"
    settings = Base()
