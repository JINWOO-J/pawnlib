import os
import toml
from hatchling.metadata.plugin.interface import MetadataHookInterface

class CustomDepsHook(MetadataHookInterface):
    def update(self, metadata):
        # pyproject.toml 파일 읽기
        pyproject_data = toml.load("pyproject.toml")

        # 기본 종속성 추가
        base_dependencies = pyproject_data["project"].get("dependencies", [])
        metadata["dependencies"] = base_dependencies

        # 선택적 종속성 가져오기
        optional_dependencies = pyproject_data["project"].get("optional-dependencies", {})

        # 환경 변수에 따른 선택적 종속성 추가
        dependency_mode = os.environ.get("DEPENDENCY_MODE", "").lower()

        optional_dependencies.get(dependency_mode, [])
        metadata["dependencies"] += optional_dependencies.get("full", [])

        print(f"CustomDepsHook invoked. DEPENDENCY_MODE={dependency_mode}")
        print(f"optional_dependencies={optional_dependencies}")
        print(f"dependencies={metadata['dependencies']}")
