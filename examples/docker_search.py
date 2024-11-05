import requests

def search_docker_images(query):
    url = f"https://hub.docker.com/v2/search/repositories/?query={query}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses

        data = response.json()
        results = data.get('results', [])

        if not results:
            print(f"No results found for '{query}'")
            return

        for result in results[:100]:  # 상위 5개 결과만 표시
            print(f"Image: {result.get('repo_name', 'N/A')}")
            print(f"Description: {result.get('short_description', 'N/A')}")
            print(f"Stars: {result.get('star_count', 'N/A')}")
            print(f"Official: {'Yes' if result.get('is_official') else 'No'}")
            print("---")

    except requests.RequestException as e:
        print(f"Error occurred while searching Docker Hub: {e}")
    except KeyError as e:
        print(f"Unexpected response structure: {e}")
        print("Response content:", response.text)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# 사용 예시
query = input("Enter search term: ")
search_docker_images(query)
