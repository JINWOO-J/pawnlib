import os
from hatchling.metadata.plugin.interface import MetadataHookInterface

class CustomNameHook(MetadataHookInterface):
    def update(self, metadata):
        # Set the project name dynamically
        metadata["name"] = os.getenv("NAME", "pawnlib")


